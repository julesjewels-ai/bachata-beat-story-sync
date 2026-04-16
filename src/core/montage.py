"""Montage generation engine.

Features: FEAT-001, FEAT-002, ..., FEAT-025.
"""

from __future__ import annotations

import bisect
import dataclasses
import hashlib
import logging
import math
import os
import random
import re
import shutil
import tempfile
import uuid

from src.config.app_config import load_app_config
from src.core.ffmpeg_renderer import (
    apply_text_overlay,
    apply_transitions,
    concatenate_segments,
    extract_segments,
    get_video_duration,
    overlay_audio,
)
from src.core.interfaces import ProgressObserver
from src.core.models import (
    AudioAnalysisResult,
    MusicalSection,
    PacingConfig,
    SegmentDecision,
    SegmentPlan,
    VideoAnalysisResult,
)
from src.core.pacing_views import (
    OverlayConfig,
    PlanningConfig,
    RenderConfig,
    overlay_config_from_pacing,
    planning_config_from_pacing,
    render_config_from_pacing,
)
from src.core.plan_validation import validate_segment_plan
from src.core.planner import append_tail_segment, select_clip

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class _LoopState:
    """Mutable state carried across build_segment_plan iterations."""

    beat_idx: int
    clip_idx: int
    forced_clip_idx: int
    broll_idx: int
    timeline_pos: float
    last_broll_time: float
    has_regular_clip_since_broll: bool
    target_broll_interval: float


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
    return load_app_config(config_path).pacing


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
        config: PlanningConfig,
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
            # FEAT-020: Prioritise vertical clips first, then score by opener
            # quality (opening_intensity + scene change near 4s mark).
            def _opener_score(c: VideoAnalysisResult) -> float:
                has_scene_near_4s = (
                    1.0 if any(3.0 <= t <= 5.0 for t in c.scene_changes) else 0.0
                )
                return 0.5 * c.opening_intensity + 0.5 * has_scene_near_4s

            sorted_clips = sorted(
                unique_clips,
                key=lambda c: (c.is_vertical, _opener_score(c), c.intensity_score),
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
        config: PlanningConfig,
    ) -> dict:
        """
        Bucket clips into high / medium / low pools by intensity_score.

        If a seed is provided in the config, the pools are shuffled based on
        that seed to ensure variety across runs. If the seed is empty, a random
        seed is used for the shuffle.

        Returns both the pools and pool_offset, which rotates the starting index
        for round-robin selection to ensure first clips vary per track.
        """
        pools: dict = {"high": [], "medium": [], "low": []}
        for clip in clips:
            if clip.intensity_score >= config.high_intensity_threshold:
                pools["high"].append(clip)
            elif clip.intensity_score < config.low_intensity_threshold:
                pools["low"].append(clip)
            else:
                pools["medium"].append(clip)

        # Shuffle each pool to ensure the round-robin selection is non-deterministic
        # unless a specific seed is forced for reproducibility.
        shuffle_seed = config.seed or str(uuid.uuid4())
        rng = random.Random(shuffle_seed)
        for level in pools:
            rng.shuffle(pools[level])

        # Compute starting offset for each pool based on seed to vary opening clips
        pool_offset = {}
        if shuffle_seed:
            offset_seed = int(
                hashlib.md5(f"{shuffle_seed}_offset".encode()).hexdigest()[:8],
                16,
            )
            pool_offset = {
                "high": offset_seed % max(1, len(pools["high"])),
                "medium": offset_seed % max(1, len(pools["medium"])),
                "low": offset_seed % max(1, len(pools["low"])),
            }
        else:
            pool_offset = {"high": 0, "medium": 0, "low": 0}

        return pools, pool_offset

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
        config: PlanningConfig,
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

    @staticmethod
    def _compute_speed_curve(
        intensity_slice: list[float],
        config: PlanningConfig,
    ) -> list[float]:
        """
        Compute per-beat speed multipliers from intensity values (FEAT-036).

        Maps intensity values through a smoothing curve and scales to
        [speed_ramp_min, speed_ramp_max] based on sensitivity.

        Args:
            intensity_slice: List of intensity values (0.0-1.0), one per beat
            config: PacingConfig with speed_ramp_* parameters

        Returns:
            List of speed multipliers, same length as intensity_slice
        """
        if not intensity_slice:
            return []

        # Normalise intensity within this segment's range
        min_intensity = min(intensity_slice)
        max_intensity = max(intensity_slice)
        intensity_range = max_intensity - min_intensity

        if intensity_range < 0.01:  # Flat section, use mid-point speed
            mid_speed = (config.speed_ramp_min + config.speed_ramp_max) / 2
            return [mid_speed] * len(intensity_slice)

        # Normalise to 0.0-1.0 relative to this segment
        normalised = [(i - min_intensity) / intensity_range for i in intensity_slice]

        # Apply smoothing curve
        if config.speed_ramp_curve == "ease_in":
            # Slow start, fast end
            curved = [x**2 for x in normalised]
        elif config.speed_ramp_curve == "ease_out":
            # Fast start, slow end
            curved = [1.0 - (1.0 - x) ** 2 for x in normalised]
        elif config.speed_ramp_curve == "ease_in_out":
            # Slow at edges, fast in middle
            curved = [(x**2) if x < 0.5 else (1.0 - (1.0 - x) ** 2) for x in normalised]
        else:  # linear
            curved = normalised

        # Apply sensitivity (amplify or dampen the curve)
        sensitivity = config.speed_ramp_sensitivity
        if sensitivity != 1.0:
            mid_point = 0.5
            curved = [mid_point + (c - mid_point) * sensitivity for c in curved]
            # Clamp to [0, 1]
            curved = [max(0.0, min(1.0, c)) for c in curved]

        # Scale to [speed_ramp_min, speed_ramp_max]
        speed_range = config.speed_ramp_max - config.speed_ramp_min
        speed_curve = [config.speed_ramp_min + c * speed_range for c in curved]

        return speed_curve

    @staticmethod
    def _compute_start_offset(
        clip: VideoAnalysisResult,
        segment_duration: float,
        config: PlanningConfig,
        clip_idx: int,
    ) -> float:
        """Deterministic start offset within *clip* for variety.

        FEAT-020: when the clip has scene_changes, snap the offset to
        the nearest viable scene-change boundary.
        """
        max_start = max(0.0, clip.duration - segment_duration)
        if not (config.clip_variety_enabled and max_start > 0):
            return 0.0

        # Hash-based base offset (deterministic)
        seed_str = f"{config.seed}:{clip.path}:{clip_idx}"
        seed = int(
            hashlib.md5(seed_str.encode()).hexdigest()[:8],
            16,
        )
        base_offset = (seed % int(max_start * 1000)) / 1000.0

        # FEAT-020: prefer a scene-change boundary close to base_offset
        if clip.scene_changes:
            viable = [t for t in clip.scene_changes if t <= max_start]
            if viable:
                best = min(viable, key=lambda t: abs(t - base_offset))
                return best

        return base_offset

    @staticmethod
    def _find_section_label(
        sections: list[MusicalSection],
        current_time: float,
    ) -> str | None:
        """Return the section label covering *current_time*, or ``None``."""
        for sec in sections:
            if sec.start_time <= current_time < sec.end_time:
                return sec.label
        return None

    @staticmethod
    def _should_stop_loop(
        state: _LoopState,
        segments: list[SegmentPlan],
        config: PlanningConfig,
        num_beats: int,
    ) -> bool:
        """Return True when the segment-building loop should terminate."""
        if state.beat_idx >= num_beats:
            logger.debug(
                "STOP: beat_idx (%d) >= num_beats (%d) | timeline_pos=%.2fs, segments=%d",
                state.beat_idx,
                num_beats,
                state.timeline_pos,
                len(segments),
            )
            return True
        if config.max_clips is not None and len(segments) >= config.max_clips:
            logger.debug(
                "STOP: segments (%d) >= max_clips (%d) | timeline_pos=%.2fs",
                len(segments),
                config.max_clips,
                state.timeline_pos,
            )
            return True
        if (
            config.max_duration_seconds is not None
            and state.timeline_pos >= config.max_duration_seconds
        ):
            logger.debug(
                "STOP: timeline_pos (%.2fs) >= max_duration_seconds (%.2fs) | segments=%d",
                state.timeline_pos,
                config.max_duration_seconds,
                len(segments),
            )
            return True
        return False

    def _create_next_segment(
        self,
        state: _LoopState,
        *,
        segments: list[SegmentPlan],
        audio_data: AudioAnalysisResult,
        config: PlanningConfig,
        pools: dict,
        pool_indices: dict,
        forced_clips: list[VideoAnalysisResult],
        broll_clips: list[VideoAnalysisResult] | None,
        sections: list[MusicalSection],
        spb: float,
        min_beats: int,
    ) -> None:
        """Process one iteration of the segment-building loop.

        Reads and mutates *state* in-place.  Appends to *segments* and
        ``self._last_decisions`` when the produced segment meets the
        minimum duration threshold.
        """
        beat_times = audio_data.beat_times
        intensity_curve = audio_data.intensity_curve

        # Calculate progress ratio for dynamic pacing and cliffhanger
        total_dur = config.max_duration_seconds or audio_data.duration
        progress = min(1.0, state.timeline_pos / total_dur) if total_dur > 0 else 0.0

        # Determine intensity at this beat
        intensity = (
            intensity_curve[state.beat_idx]
            if state.beat_idx < len(intensity_curve)
            else 0.5
        )

        # Calculate segment parameters (target beats, level, speed)
        target_beats, level, speed = self._calculate_segment_params(
            config, intensity, progress, state.clip_idx, state.beat_idx, spb, min_beats
        )

        # Don't exceed available beats
        beat_count = min(target_beats, len(beat_times) - state.beat_idx)
        segment_duration = beat_count * spb

        # Test mode: trim segment if it would exceed duration limit
        if config.max_duration_seconds is not None:
            remaining = config.max_duration_seconds - state.timeline_pos
            segment_duration = min(segment_duration, remaining)

        # Determine if this segment should be B-Roll
        # FEAT-033: Respect clip boundaries — only switch to B-roll after we've
        # completed at least one regular clip since the last B-roll. This prevents
        # inserting B-roll immediately and ensures a natural transition.
        is_broll = False
        if (
            broll_clips
            and (state.timeline_pos - state.last_broll_time)
            >= state.target_broll_interval
            and state.has_regular_clip_since_broll
        ):
            # Don't use B-roll for the very first clip if possible
            if state.timeline_pos > 0.0:
                is_broll = True

        selection = select_clip(
            forced_clips=forced_clips,
            forced_clip_idx=state.forced_clip_idx,
            is_broll=is_broll,
            broll_clips=broll_clips,
            broll_idx=state.broll_idx,
            timeline_pos=state.timeline_pos,
            last_broll_time=state.last_broll_time,
            config=config,
            pools=pools,
            pool_indices=pool_indices,
            level=level,
            clip_idx=state.clip_idx,
            pick_from_pool=self._pick_from_pool,
        )
        clip = selection.clip
        state.forced_clip_idx = selection.forced_clip_idx
        state.broll_idx = selection.broll_idx
        state.clip_idx = selection.clip_idx
        state.last_broll_time = selection.last_broll_time
        state.target_broll_interval = selection.target_broll_interval
        reason = selection.reason

        # Compute start offset within clip
        start_time = self._compute_start_offset(
            clip, segment_duration, config, state.clip_idx
        )

        # Calculate how much source material we need (accounting for speed ramping).
        # With speed_factor > 1 (fast), we extract less source material.
        # With speed_factor < 1 (slow), we need more source material.
        # The setpts filter uses PTS/speed_factor, so:
        #   speed_factor=1.2 → setpts=PTS/1.2 slows playback (needs more source)
        #   speed_factor=0.9 → setpts=PTS/0.9 speeds playback (needs less source)
        # Therefore, extract_duration = segment_duration * speed_factor
        required_source = segment_duration * speed
        available_source = clip.duration - start_time

        # Clamp segment duration to what's available from the source clip
        if required_source <= available_source:
            # We have enough source material for this speed-ramped segment
            actual_duration = segment_duration
        else:
            # Not enough source material; reduce planned segment duration
            # Account for the speed factor when calculating achievable duration
            actual_duration = (
                available_source / speed if speed > 0 else available_source
            )

        # Look up musical section for this beat position
        current_time = (
            beat_times[state.beat_idx]
            if state.beat_idx < len(beat_times)
            else state.timeline_pos
        )
        section_label = self._find_section_label(sections, current_time)

        if actual_duration >= config.min_clip_seconds:
            seg = SegmentPlan(
                video_path=clip.path,
                start_time=start_time,
                duration=actual_duration,
                clip_duration=clip.duration,
                timeline_position=state.timeline_pos,
                intensity_level=level,
                speed_factor=speed,
                section_label=section_label,
            )

            # FEAT-036: Compute per-beat organic speed ramping if enabled
            if config.speed_ramp_organic and beat_count > 0:
                # Slice intensity curve for this segment's beat range
                intensity_slice = intensity_curve[
                    state.beat_idx : min(
                        state.beat_idx + beat_count, len(intensity_curve)
                    )
                ]
                if intensity_slice:
                    speed_curve = self._compute_speed_curve(
                        intensity_slice, config
                    )
                    seg.speed_curve = speed_curve
                    # Update scalar speed_factor to mean for display/fallback
                    seg.speed_factor = sum(speed_curve) / len(speed_curve)

            segments.append(seg)

            # FEAT-033: Update the boundary-respecting flag
            if is_broll:
                # Need regular clip before next B-roll
                state.has_regular_clip_since_broll = False
            else:
                # Can use B-roll next if threshold is met
                state.has_regular_clip_since_broll = True

            # FEAT-025: collect decision if explain mode is active
            if config.explain:
                self._last_decisions.append(
                    SegmentDecision(
                        timeline_start=seg.timeline_position,
                        clip_path=clip.path,
                        intensity_score=clip.intensity_score,
                        section_label=section_label,
                        duration=actual_duration,
                        speed=speed,
                        reason=reason,
                    )
                )

            state.timeline_pos += actual_duration

        # Advance beat index proportionally to what we actually produced.
        # When source material was clamped (actual_duration < segment_duration),
        # advancing by the full planned beat_count skips audio we never made
        # video for — costing up to 30+ seconds on a full track.
        if actual_duration < segment_duration and segment_duration > 0:
            beats_used = max(1, round(actual_duration / spb))
            state.beat_idx += min(beats_used, beat_count)
        else:
            state.beat_idx += beat_count

    def build_segment_plan(
        self,
        audio_data: AudioAnalysisResult,
        video_clips: list[VideoAnalysisResult],
        pacing: PlanningConfig | PacingConfig | None = None,
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

        if not beat_times:
            return []

        if isinstance(pacing, PlanningConfig):
            config = pacing
        else:
            config = planning_config_from_pacing(pacing or PacingConfig())

        # DEBUG: Log audio/beat info at start
        logger.debug(
            "=== build_segment_plan START ===\n"
            "  Audio duration: %.2fs\n"
            "  BPM: %.1f\n"
            "  Beat count (librosa): %d\n"
            "  Config max_clips: %s\n"
            "  Config max_duration_seconds: %s\n"
            "  Config min_clip_seconds: %.2f",
            audio_data.duration,
            audio_data.bpm,
            len(beat_times),
            config.max_clips,
            config.max_duration_seconds,
            config.min_clip_seconds,
        )

        # Calculate seconds-per-beat from BPM
        spb = 60.0 / audio_data.bpm if audio_data.bpm > 0 else 0.5

        # Minimum beats to satisfy the floor
        min_beats = max(1, math.ceil(config.min_clip_seconds / spb))

        # Prepare clips (deduplication, sorting, forced ordering)
        sorted_clips, forced_clips = self._prepare_clips(video_clips, config)

        # FEAT-009: Build intensity-matched pools for clip selection
        pools, pool_offset = self._build_intensity_pools(sorted_clips, config)
        pool_indices: dict = {
            "high": pool_offset.get("high", 0),
            "medium": pool_offset.get("medium", 0),
            "low": pool_offset.get("low", 0),
        }
        logger.debug(
            "Intensity pools — high: %d, medium: %d, low: %d (offsets: %s)",
            len(pools["high"]),
            len(pools["medium"]),
            len(pools["low"]),
            pool_offset,
        )

        segments: list[SegmentPlan] = []
        self._last_decisions: list[SegmentDecision] = []

        # FEAT-019: skip beats before audio_start_offset
        if config.audio_start_offset > 0:
            initial_beat_idx = bisect.bisect_left(
                beat_times, config.audio_start_offset
            )
        else:
            initial_beat_idx = 0

        target_broll_interval = config.broll_interval_seconds + random.uniform(
            -config.broll_interval_variance, config.broll_interval_variance
        )

        state = _LoopState(
            beat_idx=initial_beat_idx,
            clip_idx=0,
            forced_clip_idx=0,
            broll_idx=0,
            timeline_pos=0.0,
            last_broll_time=0.0,
            has_regular_clip_since_broll=True,
            target_broll_interval=target_broll_interval,
        )

        # Pre-compute section lookup from audio sections
        sections = audio_data.sections or []

        while not self._should_stop_loop(
            state, segments, config, len(beat_times)
        ):
            self._create_next_segment(
                state,
                segments=segments,
                audio_data=audio_data,
                config=config,
                pools=pools,
                pool_indices=pool_indices,
                forced_clips=forced_clips,
                broll_clips=broll_clips,
                sections=sections,
                spb=spb,
                min_beats=min_beats,
            )

        logger.debug(
            "Main loop ended | segments=%d, timeline_pos=%.2fs, beat_idx=%d/%d",
            len(segments),
            state.timeline_pos,
            state.beat_idx,
            len(beat_times),
        )

        # DEBUG: Log tail segment decision
        tail_uncovered = audio_data.duration - state.timeline_pos
        logger.debug(
            "Before tail segment:\n"
            "  tail_uncovered: %.2fs\n"
            "  audio_data.duration: %.2fs\n"
            "  timeline_pos: %.2fs\n"
            "  min_clip_seconds: %.2f\n"
            "  will_append_tail: %s",
            tail_uncovered,
            audio_data.duration,
            state.timeline_pos,
            config.min_clip_seconds,
            tail_uncovered > 0.15
            and config.max_duration_seconds is None
            and config.max_clips is None
            and sorted_clips,
        )

        append_tail_segment(
            segments=segments,
            audio_data=audio_data,
            timeline_pos=state.timeline_pos,
            config=config,
            pools=pools,
            pool_indices=pool_indices,
            sorted_clips=sorted_clips,
            pick_from_pool=self._pick_from_pool,
            find_section_label=self._find_section_label,
            record_decision=self._last_decisions.append,
            logger=logger,
        )

        logger.debug(
            "=== build_segment_plan END ===\n"
            "  Total segments: %d\n"
            "  Final timeline_pos: %.2fs\n"
            "  Audio duration: %.2fs\n"
            "  Coverage: %.1f%%",
            len(segments),
            state.timeline_pos,
            audio_data.duration,
            100 * state.timeline_pos / audio_data.duration if audio_data.duration > 0 else 0,
        )

        expected_duration = (
            min(audio_data.duration, config.max_duration_seconds)
            if config.max_duration_seconds is not None
            else audio_data.duration
        )
        validation = validate_segment_plan(
            segments,
            expected_duration=expected_duration,
            min_clip_seconds=config.min_clip_seconds,
        )
        if not validation.is_valid:
            logger.warning(
                "Segment plan validation found %d issue(s): %s",
                len(validation.issues),
                " | ".join(validation.issues),
            )

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

    def _write_explain_html(
        self,
        output_path: str,
        config: PacingConfig,
        audio_data: AudioAnalysisResult,
    ) -> None:
        """Write collected decisions to an HTML report file.

        File path is taken from config.explain_html.
        """
        from src.services.explain_html import generate_explain_html  # noqa: WPS433

        if not config.explain_html or not self._last_decisions:
            return

        generate_explain_html(
            config.explain_html,
            audio_data,
            self._last_decisions,
            config,
        )
        logger.info("HTML explain report written to: %s", config.explain_html)

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

        # Load pacing config (explicit > file > defaults), then split by concern.
        config = pacing or load_pacing_config()
        planning_config: PlanningConfig = planning_config_from_pacing(config)
        render_config: RenderConfig = render_config_from_pacing(config)
        overlay_config: OverlayConfig = overlay_config_from_pacing(config)

        # 1. Build segment plan
        segments = self.build_segment_plan(
            audio_data,
            video_clips,
            planning_config,
            broll_clips,
        )
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
        if planning_config.max_clips or planning_config.max_duration_seconds:
            logger.info(
                "Test mode active — limits: max_clips=%s, max_duration=%.1fs",
                planning_config.max_clips,
                planning_config.max_duration_seconds or total_dur,
            )

        # FEAT-025: Write decision explainability log
        if config.explain and self._last_decisions:
            self._write_explain_log(output_path, config)
            # Also write HTML report if path is specified
            if config.explain_html:
                self._write_explain_html(output_path, config, audio_data)

        # Create temp directory for intermediate files
        temp_dir = tempfile.mkdtemp(prefix="montage_")

        try:
            # 2. Extract segments (one FFmpeg process at a time)
            segment_files = extract_segments(
                segments,
                temp_dir,
                render_config,
                observer,
                beat_times=audio_data.beat_times,
            )

            # 3. Group-and-transition or simple concat
            transitions_enabled = (
                render_config.transition_type
                and render_config.transition_type.lower() != "none"
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
                        render_config.transition_type,
                        render_config.transition_duration,
                        warm_wash=render_config.pacing_warm_wash,
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
                # Warn early if there's a significant length gap before overlaying
                if audio_data.duration > 0 and abs(video_dur - audio_data.duration) > 0.5:
                    logger.warning(
                        "Video length (%.1fs) differs from audio (%.1fs) by %.1fs "
                        "before overlay — possible dropped segments",
                        video_dur,
                        audio_data.duration,
                        audio_data.duration - video_dur,
                    )
                overlay_audio(
                    concat_path,
                    audio_path,
                    output_path,
                    overlay_config,
                    video_duration=video_dur,
                    target_duration=audio_data.duration,
                )
            else:
                shutil.move(concat_path, output_path)

            # 5. Text overlay (FEAT-045) — post-processing pass.
            # Also triggered by mix_fade_transitions (FEAT-050) which shares
            # the same FFmpeg pass to burn fade-to-black at track boundaries.
            wants_mix_fades = (
                render_config.mix_fade_transitions
                and bool(render_config.mix_track_segments)
            )
            if render_config.text_overlay_enabled or wants_mix_fades:
                from src.core.text_overlay import build_text_events

                text_events = (
                    build_text_events(config, audio_path)
                    if render_config.text_overlay_enabled
                    else []
                )
                if text_events or wants_mix_fades:
                    if os.path.isfile(output_path):
                        pre_text = output_path + ".pre_text.mp4"
                        shutil.move(output_path, pre_text)
                        try:
                            apply_text_overlay(
                                pre_text,
                                output_path,
                                text_events,
                                render_config,
                            )
                        finally:
                            if os.path.exists(pre_text):
                                os.remove(pre_text)
                    else:
                        logger.warning(
                            "Skipping text overlay post-pass because %s was not created.",
                            output_path,
                        )

            # Post-render duration sanity check (regression canary)
            output_dur = get_video_duration(output_path)
            if audio_data.duration > 0 and output_dur > 0:
                delta = abs(output_dur - audio_data.duration)
                if delta > 0.5:
                    logger.warning(
                        "Output duration mismatch: rendered=%.2fs  audio=%.2fs  "
                        "delta=%.2fs — run with --verbose to investigate",
                        output_dur,
                        audio_data.duration,
                        delta,
                    )
                else:
                    logger.debug(
                        "Duration check OK: rendered=%.2fs  audio=%.2fs  delta=%.2fs",
                        output_dur,
                        audio_data.duration,
                        delta,
                    )

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
