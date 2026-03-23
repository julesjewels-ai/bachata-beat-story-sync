"""Montage generation engine — FEAT-001 through FEAT-013, FEAT-019, FEAT-025."""

import bisect
import hashlib
import logging
import math
import os
import random
import re
import shutil
import tempfile
from pathlib import Path

import yaml

from src.core.ffmpeg_renderer import (
    apply_transitions,
    concatenate_segments,
    extract_segments,
    get_video_duration,
    overlay_audio,
)
from src.core.interfaces import ProgressObserver
from src.core.models import (
    AudioAnalysisResult,
    PacingConfig,
    SegmentDecision,
    SegmentPlan,
    VideoAnalysisResult,
)

logger = logging.getLogger(__name__)



# Default config file location (project root)
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "montage_config.yaml"


def load_pacing_config(
    config_path: str | None = None,
) -> PacingConfig:
    """
    Load pacing configuration from YAML file.

    Falls back to PacingConfig defaults if the file is missing or invalid.

    Args:
        config_path: Optional explicit path to YAML config file.

    Returns:
        A validated PacingConfig instance.
    """
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH

    if path.exists():
        try:
            with open(path) as f:
                raw = yaml.safe_load(f) or {}
            pacing_data = raw.get("pacing", {})

            # FEAT-027: apply genre preset if specified
            genre = pacing_data.get("genre")
            if genre:
                from src.core.genre_presets import apply_genre_preset  # noqa: WPS433

                pacing_data = apply_genre_preset(genre, pacing_data)

            config = PacingConfig(**pacing_data)
            logger.info("Loaded pacing config from %s", path)
            return config
        except Exception as e:
            logger.warning(
                "Failed to load pacing config from %s: %s. Using defaults.", path, e
            )

    return PacingConfig()


class MontageGenerator:
    """
    Generates a video montage synchronized to audio analysis.

    Architecture:
        1. Build segment plan (pure Python — maps beats to clip durations)
        2. Extract segments (FFmpeg subprocess — one at a time)
        3. Concatenate segments (FFmpeg concat demuxer)
        4. Overlay audio (FFmpeg subprocess)
    """

    @staticmethod
    def _prepare_clips(
        video_clips: list[VideoAnalysisResult],
        config: PacingConfig,
    ) -> tuple[list[VideoAnalysisResult], list[VideoAnalysisResult]]:
        """
        Deduplicate, separate forced clips, and sort regular clips.

        Returns:
            Tuple containing:
            - sorted_clips: List of regular clips sorted by priority/intensity.
            - forced_clips: List of clips with numeric prefix (e.g. '1_start.mp4').
        """
        # Deduplicate identical clips (e.g. same footage in multiple folders)
        unique_clips = []
        seen = set()
        for c in video_clips:
            key = (round(c.duration, 1), round(c.intensity_score, 3), c.is_vertical)
            if key not in seen:
                seen.add(key)
                unique_clips.append(c)

        forced_clips_tuple = []
        for c in unique_clips:
            basename = os.path.basename(c.path)
            match = re.match(r"^(\d+)_", basename)
            if match:
                prefix = int(match.group(1))
                forced_clips_tuple.append((prefix, c))

        forced_clips_tuple.sort(key=lambda x: x[0])
        forced_clips = [fc[1] for fc in forced_clips_tuple]

        # FEAT-017: Rotate prefix clips for per-track intro variety
        if config.prefix_offset and forced_clips:
            offset = config.prefix_offset % len(forced_clips)
            forced_clips = forced_clips[offset:] + forced_clips[:offset]

        # Only force the first prefix clip as the intro;
        # remaining prefix clips return to the regular pool.
        if len(forced_clips) > 1:
            overflow = forced_clips[1:]
            forced_clips = forced_clips[:1]
            # Add overflow back so they participate in intensity selection
            for clip in overflow:
                if clip not in unique_clips:
                    unique_clips.append(clip)

        # Sort clips by intensity score (highest first) for matching
        if config.is_shorts:
            # Prioritise vertical clips first
            sorted_clips = sorted(
                unique_clips,
                key=lambda c: (c.is_vertical, c.intensity_score),
                reverse=True,
            )
        else:
            sorted_clips = sorted(
                unique_clips, key=lambda c: c.intensity_score, reverse=True
            )

        return sorted_clips, forced_clips

    @staticmethod
    def _build_intensity_pools(
        clips: list[VideoAnalysisResult],
        config: PacingConfig,
    ) -> dict:
        """
        Bucket clips into high / medium / low pools by intensity_score.

        Uses the same thresholds as audio intensity classification.

        Returns:
            Dict with keys 'high', 'medium', 'low' mapping to lists of clips.
        """
        pools: dict = {"high": [], "medium": [], "low": []}
        for clip in clips:
            if clip.intensity_score >= config.high_intensity_threshold:
                pools["high"].append(clip)
            elif clip.intensity_score < config.low_intensity_threshold:
                pools["low"].append(clip)
            else:
                pools["medium"].append(clip)
        return pools

    @staticmethod
    def _pick_from_pool(
        pools: dict[str, list[VideoAnalysisResult]],
        pool_indices: dict[str, int],
        target_level: str,
    ) -> VideoAnalysisResult:
        """
        Pick a clip from the target intensity pool with round-robin.

        Falls back to adjacent pools if the target pool is empty:
            high   → medium → low
            low    → medium → high
            medium → high   → low

        Args:
            pools: Dict of intensity pools built by _build_intensity_pools.
            pool_indices: Mutable dict tracking per-pool round-robin index.
            target_level: Desired intensity level ('high', 'medium', 'low').

        Returns:
            A VideoAnalysisResult from the best available pool.
        """
        fallback_order = {
            "high": ["high", "medium", "low"],
            "medium": ["medium", "high", "low"],
            "low": ["low", "medium", "high"],
        }
        for level in fallback_order[target_level]:
            pool = pools[level]
            if pool:
                idx = pool_indices[level] % len(pool)
                pool_indices[level] += 1
                return pool[idx]

        # Should be unreachable if clips were provided, but guard anyway
        raise ValueError("All intensity pools are empty — no clips available.")

    @staticmethod
    def _calculate_segment_params(
        config: PacingConfig,
        intensity: float,
        progress: float,
        clip_idx: int,
        beat_idx: int,
        spb: float,
        min_beats: int,
    ) -> tuple[int, str, float]:
        """
        Determine target beats, intensity level string, and playback speed.

        Returns:
            Tuple of (target_beats, level_name, speed_factor)
        """
        # Pick target duration and speed based on intensity level
        if intensity >= config.high_intensity_threshold:
            target_seconds = config.high_intensity_seconds
            level = "high"
            speed = config.high_intensity_speed if config.speed_ramp_enabled else 1.0
        elif intensity < config.low_intensity_threshold:
            target_seconds = config.low_intensity_seconds
            level = "low"
            speed = config.low_intensity_speed if config.speed_ramp_enabled else 1.0
        else:
            target_seconds = config.medium_intensity_seconds
            level = "medium"
            speed = config.medium_intensity_speed if config.speed_ramp_enabled else 1.0

        # Dynamic Flow: accelerate pacing towards the end (reduce duration by up to 40%)
        if config.accelerate_pacing:
            target_seconds *= 1.0 - (0.4 * progress)

        # Human Touch: randomize speed ramps slightly (+/- 10%)
        if config.randomize_speed_ramps and config.speed_ramp_enabled:
            seed_val = f"{config.seed}_{clip_idx}_{beat_idx}"
            rng = random.Random(seed_val)
            speed *= rng.uniform(0.9, 1.1)

        # Convert target to beats, then enforce minimum
        if config.snap_to_beats:
            target_beats = max(min_beats, round(target_seconds / spb))
        else:
            target_beats = max(min_beats, math.ceil(target_seconds / spb))

        return target_beats, level, speed

    def _select_clip(
        self,
        *,
        forced_clips: list[VideoAnalysisResult],
        forced_clip_idx: int,
        is_broll: bool,
        broll_clips: list[VideoAnalysisResult] | None,
        broll_idx: int,
        timeline_pos: float,
        last_broll_time: float,
        config: PacingConfig,
        pools: dict,
        pool_indices: dict,
        level: str,
        clip_idx: int,
    ) -> tuple[VideoAnalysisResult, int, int, int, float, float, str]:
        """Pick the next clip and advance the relevant index.

        Returns:
            ``(clip, forced_clip_idx, broll_idx, clip_idx,
            last_broll_time, target_broll_interval, reason)``.
        """
        target_broll_interval = config.broll_interval_seconds + random.uniform(
            -config.broll_interval_variance, config.broll_interval_variance
        )
        if forced_clip_idx < len(forced_clips):
            clip = forced_clips[forced_clip_idx]
            forced_clip_idx += 1
            reason = "Forced prefix ordering (FEAT-008)"
        elif is_broll:
            assert broll_clips is not None
            clip = broll_clips[broll_idx % len(broll_clips)]
            broll_idx += 1
            last_broll_time = timeline_pos
            timeline_pos - (last_broll_time - timeline_pos + timeline_pos)
            reason = f"B-roll interval triggered ({target_broll_interval:.1f}s)"
        else:
            clip = self._pick_from_pool(pools, pool_indices, level)
            clip_idx += 1
            reason = (
                f"Intensity matched: {level} pool "
                f"(score={clip.intensity_score:.2f})"
            )
        return (clip, forced_clip_idx, broll_idx, clip_idx,
                last_broll_time, target_broll_interval, reason)

    @staticmethod
    def _compute_start_offset(
        clip: VideoAnalysisResult,
        segment_duration: float,
        config: PacingConfig,
        clip_idx: int,
    ) -> float:
        """Deterministic start offset within *clip* for variety."""
        max_start = max(0.0, clip.duration - segment_duration)
        if config.clip_variety_enabled and max_start > 0:
            seed_str = f"{config.seed}:{clip.path}:{clip_idx}"
            seed = int(
                hashlib.md5(seed_str.encode()).hexdigest()[:8],
                16,
            )
            return (seed % int(max_start * 1000)) / 1000.0
        return 0.0

    @staticmethod
    def _find_section_label(
        sections: list,
        current_time: float,
    ) -> str | None:
        """Return the section label covering *current_time*, or ``None``."""
        for sec in sections:
            if sec.start_time <= current_time < sec.end_time:
                return sec.label
        return None

    def build_segment_plan(
        self,
        audio_data: AudioAnalysisResult,
        video_clips: list[VideoAnalysisResult],
        pacing: PacingConfig | None = None,
        broll_clips: list[VideoAnalysisResult] | None = None,
    ) -> list[SegmentPlan]:
        """
        Build a timeline of clip segments from audio beat/intensity data.

        Clip duration is time-based (not beat-count) and snaps to beat
        boundaries so cuts feel musical. A hard minimum floor is enforced.

        Args:
            audio_data: Analysed audio with beat_times and intensity_curve.
            video_clips: Available video clips sorted by intensity.
            pacing: Optional pacing configuration. Uses defaults if None.

        Returns:
            Ordered list of SegmentPlan objects covering the audio duration.
        """
        if not video_clips:
            return []

        beat_times = audio_data.beat_times
        intensity_curve = audio_data.intensity_curve

        if not beat_times:
            return []

        config = pacing or PacingConfig()

        # Calculate seconds-per-beat from BPM
        spb = 60.0 / audio_data.bpm if audio_data.bpm > 0 else 0.5

        # Minimum beats to satisfy the floor
        min_beats = max(1, math.ceil(config.min_clip_seconds / spb))

        # Prepare clips (deduplication, sorting, forced ordering)
        sorted_clips, forced_clips = self._prepare_clips(video_clips, config)

        # FEAT-009: Build intensity-matched pools for clip selection
        pools = self._build_intensity_pools(sorted_clips, config)
        pool_indices: dict = {"high": 0, "medium": 0, "low": 0}
        logger.debug(
            "Intensity pools — high: %d, medium: %d, low: %d",
            len(pools["high"]),
            len(pools["medium"]),
            len(pools["low"]),
        )

        segments: list[SegmentPlan] = []
        self._last_decisions: list[SegmentDecision] = []
        timeline_pos = 0.0

        # FEAT-019: skip beats before audio_start_offset
        if config.audio_start_offset > 0:
            beat_idx = bisect.bisect_left(
                beat_times, config.audio_start_offset
            )
        else:
            beat_idx = 0
        clip_idx = 0
        broll_idx = 0
        forced_clip_idx = 0

        # B-Roll tracking
        last_broll_time = (
            -config.broll_interval_seconds
        )  # Allow B-roll early on if configured
        target_broll_interval = config.broll_interval_seconds + random.uniform(
            -config.broll_interval_variance, config.broll_interval_variance
        )

        # Pre-compute section lookup from audio sections
        sections = audio_data.sections or []

        while beat_idx < len(beat_times):
            # Test mode: stop if we've hit the clip limit
            if config.max_clips is not None and len(segments) >= config.max_clips:
                break

            # Test mode: stop if we've hit the duration limit
            if (
                config.max_duration_seconds is not None
                and timeline_pos >= config.max_duration_seconds
            ):
                break

            # Calculate progress ratio for dynamic pacing and cliffhanger
            total_dur = config.max_duration_seconds or audio_data.duration
            progress = min(1.0, timeline_pos / total_dur) if total_dur > 0 else 0.0

            # Determine intensity at this beat
            intensity = (
                intensity_curve[beat_idx] if beat_idx < len(intensity_curve) else 0.5
            )

            # Calculate segment parameters (target beats, level, speed)
            target_beats, level, speed = self._calculate_segment_params(
                config, intensity, progress, clip_idx, beat_idx, spb, min_beats
            )

            # Don't exceed available beats
            beat_count = min(target_beats, len(beat_times) - beat_idx)
            segment_duration = beat_count * spb

            # Test mode: trim segment if it would exceed duration limit
            if config.max_duration_seconds is not None:
                remaining = config.max_duration_seconds - timeline_pos
                segment_duration = min(segment_duration, remaining)

            # Determine if this segment should be B-Roll
            is_broll = False
            if (
                broll_clips
                and (timeline_pos - last_broll_time) >= target_broll_interval
            ):
                # Don't use B-roll for the very first clip if possible
                if timeline_pos > 0.0:
                    is_broll = True

            # Pick clip (forced prefix → B-roll → intensity pool)
            (clip, forced_clip_idx, broll_idx, clip_idx,
             last_broll_time, target_broll_interval, reason) = self._select_clip(
                forced_clips=forced_clips,
                forced_clip_idx=forced_clip_idx,
                is_broll=is_broll,
                broll_clips=broll_clips,
                broll_idx=broll_idx,
                timeline_pos=timeline_pos,
                last_broll_time=last_broll_time,
                config=config,
                pools=pools,
                pool_indices=pool_indices,
                level=level,
                clip_idx=clip_idx,
            )

            # Compute start offset within clip
            start_time = self._compute_start_offset(
                clip, segment_duration, config, clip_idx
            )

            # Clamp segment duration to remaining clip after start offset
            actual_duration = min(segment_duration, clip.duration - start_time)

            # Look up musical section for this beat position
            current_time = (
                beat_times[beat_idx] if beat_idx < len(beat_times) else timeline_pos
            )
            section_label = self._find_section_label(sections, current_time)

            if actual_duration > 0:
                segments.append(
                    SegmentPlan(
                        video_path=clip.path,
                        start_time=start_time,
                        duration=actual_duration,
                        timeline_position=timeline_pos,
                        intensity_level=level,
                        speed_factor=speed,
                        section_label=section_label,
                    )
                )

                # FEAT-025: collect decision if explain mode is active
                if config.explain:
                    self._last_decisions.append(
                        SegmentDecision(
                            timeline_start=segments[-1].timeline_position,
                            clip_path=clip.path,
                            intensity_score=clip.intensity_score,
                            section_label=section_label,
                            duration=actual_duration,
                            speed=speed,
                            reason=reason,
                        )
                    )

                timeline_pos += actual_duration

            beat_idx += beat_count

        return segments

    def _write_explain_log(
        self,
        output_path: str,
        config: PacingConfig,
    ) -> None:
        """Write collected decisions to a Markdown file next to output.

        File is named ``{output_stem}_explain.md``.
        """
        stem = os.path.splitext(output_path)[0]
        log_path = f"{stem}_explain.md"

        lines: list[str] = [
            "# Decision Explainability Log\n",
            "",
            "## Segment Decisions\n",
            "",
            "| # | Time | Clip | Intensity | Section | Duration | Speed | Reason |",
            "|---|------|------|-----------|---------|----------|-------|--------|",
        ]
        for i, d in enumerate(self._last_decisions, 1):
            clip_name = os.path.basename(d.clip_path)
            section = d.section_label or "—"
            lines.append(
                f"| {i} | {d.timeline_start:.2f}s "
                f"| {clip_name} "
                f"| {d.intensity_score:.2f} "
                f"| {section} "
                f"| {d.duration:.2f}s "
                f"| {d.speed:.2f}x "
                f"| {d.reason} |"
            )

        lines.append("")
        lines.append("## Config Applied\n")
        lines.append("")
        lines.append(f"- **Min clip duration**: {config.min_clip_seconds}s")
        lines.append(
            f"- **Intensity durations**: "
            f"high={config.high_intensity_seconds}s "
            f"mid={config.medium_intensity_seconds}s "
            f"low={config.low_intensity_seconds}s"
        )
        lines.append(f"- **Max clips**: {config.max_clips}")
        lines.append(f"- **Max duration**: {config.max_duration_seconds}")
        if config.video_style and config.video_style != "none":
            lines.append(f"- **Video style**: {config.video_style}")
        if config.audio_overlay and config.audio_overlay != "none":
            lines.append(f"- **Audio overlay**: {config.audio_overlay}")
        lines.append("")

        with open(log_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        logger.info("Explain log written to: %s", log_path)

    def generate(
        self,
        audio_data: AudioAnalysisResult,
        video_clips: list[VideoAnalysisResult],
        output_path: str,
        audio_path: str | None = None,
        observer: ProgressObserver | None = None,
        pacing: PacingConfig | None = None,
        broll_clips: list[VideoAnalysisResult] | None = None,
    ) -> str:
        """
        Generate a montage video synchronized to the audio.

        Pipeline:
            1. Build segment plan from audio analysis
            2. Extract each segment via FFmpeg (one at a time)
            3. Concatenate all segments via FFmpeg concat demuxer
            4. Overlay the original audio track

        Args:
            audio_data: Analyzed audio features (BPM, beats, intensity).
            video_clips: Analyzed video clips with intensity scores.
            output_path: Path for the final output video.
            audio_path: Optional path to audio file to overlay.
            observer: Optional progress observer for status updates.
            pacing: Optional pacing configuration. Loaded from file if None.
            broll_clips: Optional list of B-roll video clips.

        Returns:
            Path to the generated output video.

        Raises:
            ValueError: If no video clips are provided.
            RuntimeError: If FFmpeg fails during any stage.
        """
        if not video_clips:
            raise ValueError("No video clips provided for montage.")

        # Verify ffmpeg is available
        if not shutil.which("ffmpeg"):
            raise RuntimeError(
                "FFmpeg is not installed or not on PATH. "
                "Install it with: brew install ffmpeg"
            )

        # Load pacing config (explicit > file > defaults)
        config = pacing or load_pacing_config()

        # 1. Build segment plan
        segments = self.build_segment_plan(audio_data, video_clips, config, broll_clips)
        if not segments:
            raise ValueError(
                "Could not build a segment plan — no beats detected "
                "in the audio analysis."
            )

        total_dur = segments[-1].timeline_position + segments[-1].duration
        logger.info(
            "Built segment plan: %d segments, total duration: %.1fs",
            len(segments),
            total_dur,
        )
        if config.max_clips or config.max_duration_seconds:
            logger.info(
                "Test mode active — limits: max_clips=%s, max_duration=%.1fs",
                config.max_clips,
                config.max_duration_seconds or total_dur,
            )

        # FEAT-025: Write decision explainability log
        if config.explain and self._last_decisions:
            self._write_explain_log(output_path, config)

        # Create temp directory for intermediate files
        temp_dir = tempfile.mkdtemp(prefix="montage_")

        try:
            # 2. Extract segments (one FFmpeg process at a time)
            segment_files = extract_segments(segments, temp_dir, config, observer)

            # 3. Group-and-transition or simple concat
            transitions_enabled = (
                config.transition_type and config.transition_type.lower() != "none"
            )

            if transitions_enabled:
                # Group segments by musical section
                groups = self._group_segments_by_section(segments)

                if len(groups) > 1:
                    # Concat within each group, then xfade between groups
                    group_files = []
                    file_idx = 0
                    for g_idx, group in enumerate(groups):
                        group_seg_files = segment_files[
                            file_idx : file_idx + len(group)
                        ]
                        file_idx += len(group)

                        if len(group_seg_files) == 1:
                            group_files.append(group_seg_files[0])
                        else:
                            group_out = os.path.join(temp_dir, f"group_{g_idx:04d}.mp4")
                            concatenate_segments(group_seg_files, group_out)
                            group_files.append(group_out)

                    # Apply xfade transitions between groups
                    concat_path = os.path.join(temp_dir, "concat_output.mp4")
                    apply_transitions(
                        group_files,
                        concat_path,
                        config.transition_type,
                        config.transition_duration,
                    )
                else:
                    # Only one section — fall back to simple concat
                    concat_path = os.path.join(temp_dir, "concat_output.mp4")
                    concatenate_segments(segment_files, concat_path)
            else:
                # No transitions — simple concat (current behaviour)
                concat_path = os.path.join(temp_dir, "concat_output.mp4")
                concatenate_segments(segment_files, concat_path)

            # 4. Overlay audio (or just copy if no audio)
            if audio_path and os.path.exists(audio_path):
                video_dur = get_video_duration(concat_path)
                overlay_audio(
                    concat_path, audio_path, output_path, config,
                    video_duration=video_dur,
                )
            else:
                shutil.move(concat_path, output_path)

            logger.info("Montage complete: %s", output_path)
            return output_path

        finally:
            # Clean up temp directory (memory safety guarantee)
            shutil.rmtree(temp_dir, ignore_errors=True)

    @staticmethod
    def _group_segments_by_section(
        segments: list[SegmentPlan],
    ) -> list[list[SegmentPlan]]:
        """
        Group consecutive segments that share the same section_label.

        Returns a list of groups, where each group is a list of
        SegmentPlan objects with the same musical section label.
        Adjacent segments with matching labels are merged into one group.
        """
        if not segments:
            return []

        groups: list[list[SegmentPlan]] = []
        current_group: list[SegmentPlan] = [segments[0]]

        for seg in segments[1:]:
            if seg.section_label == current_group[-1].section_label:
                current_group.append(seg)
            else:
                groups.append(current_group)
                current_group = [seg]

        groups.append(current_group)
        return groups

