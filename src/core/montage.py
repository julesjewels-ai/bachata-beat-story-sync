"""
Montage generator for Bachata Beat-Story Sync.

Uses direct FFmpeg subprocess calls for memory-safe video processing.
Only one FFmpeg process runs at a time — no memory leaks.
"""
import hashlib
import logging
import math
import os
import shutil
import subprocess
import tempfile
import random
import re
import yaml
from pathlib import Path
from typing import List, Optional, Tuple
from src.core.interfaces import ProgressObserver
from src.core.models import (
    AudioAnalysisResult,
    MusicalSection,
    PacingConfig,
    SegmentPlan,
    VideoAnalysisResult,
)

logger = logging.getLogger(__name__)

# Timeout per FFmpeg subprocess call (seconds)
FFMPEG_TIMEOUT = 600

# Target resolution for all extracted segments (ensures xfade compatibility)
TARGET_WIDTH = 1920
TARGET_HEIGHT = 1080
TARGET_FPS = 30

# Default config file location (project root)
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "montage_config.yaml"


def load_pacing_config(
    config_path: Optional[str] = None,
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
            with open(path, "r") as f:
                raw = yaml.safe_load(f) or {}
            pacing_data = raw.get("pacing", {})
            config = PacingConfig(**pacing_data)
            logger.info("Loaded pacing config from %s", path)
            return config
        except Exception as e:
            logger.warning(
                "Failed to load pacing config from %s: %s. "
                "Using defaults.",
                path, e
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
        video_clips: List[VideoAnalysisResult],
        config: PacingConfig,
    ) -> Tuple[List[VideoAnalysisResult], List[VideoAnalysisResult]]:
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
            match = re.match(r'^(\d+)_', basename)
            if match:
                prefix = int(match.group(1))
                forced_clips_tuple.append((prefix, c))

        forced_clips_tuple.sort(key=lambda x: x[0])
        forced_clips = [fc[1] for fc in forced_clips_tuple]

        # Sort clips by intensity score (highest first) for matching
        if config.is_shorts:
            # Prioritise vertical clips first
            sorted_clips = sorted(
                unique_clips, key=lambda c: (c.is_vertical, c.intensity_score), reverse=True
            )
        else:
            sorted_clips = sorted(
                unique_clips, key=lambda c: c.intensity_score, reverse=True
            )

        return sorted_clips, forced_clips

    @staticmethod
    def _calculate_segment_params(
        config: PacingConfig,
        intensity: float,
        progress: float,
        clip_idx: int,
        beat_idx: int,
        spb: float,
        min_beats: int,
    ) -> Tuple[int, str, float]:
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
            target_seconds *= (1.0 - (0.4 * progress))

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

    def build_segment_plan(
        self,
        audio_data: AudioAnalysisResult,
        video_clips: List[VideoAnalysisResult],
        pacing: Optional[PacingConfig] = None,
        broll_clips: Optional[List[VideoAnalysisResult]] = None,
    ) -> List[SegmentPlan]:
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

        segments: List[SegmentPlan] = []
        timeline_pos = 0.0
        beat_idx = 0
        clip_idx = 0
        broll_idx = 0
        forced_clip_idx = 0

        # B-Roll tracking
        last_broll_time = -config.broll_interval_seconds # Allow B-roll early on if configured
        target_broll_interval = config.broll_interval_seconds + random.uniform(-config.broll_interval_variance, config.broll_interval_variance)

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
                intensity_curve[beat_idx]
                if beat_idx < len(intensity_curve)
                else 0.5
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
            if broll_clips and (timeline_pos - last_broll_time) >= target_broll_interval:
                # Don't use B-roll for the very first clip if possible
                if timeline_pos > 0.0:
                    is_broll = True

            # Pick clip (forced prefix followed by round-robin)
            if forced_clip_idx < len(forced_clips):
                clip = forced_clips[forced_clip_idx]
                forced_clip_idx += 1
            elif is_broll:
                clip = broll_clips[broll_idx % len(broll_clips)]
                broll_idx += 1
                last_broll_time = timeline_pos
                target_broll_interval = config.broll_interval_seconds + random.uniform(-config.broll_interval_variance, config.broll_interval_variance)
            else:
                clip = sorted_clips[clip_idx % len(sorted_clips)]
                clip_idx += 1

            # Compute start offset within clip
            max_start = max(0.0, clip.duration - segment_duration)
            if config.clip_variety_enabled and max_start > 0:
                # Deterministic per-segment offset using clip path + usage index + seed
                seed_str = f"{config.seed}:{clip.path}:{clip_idx}"
                seed = int(
                    hashlib.md5(
                        seed_str.encode()
                    ).hexdigest()[:8],
                    16,
                )
                start_time = (seed % int(max_start * 1000)) / 1000.0
            else:
                start_time = 0.0

            # Clamp segment duration to remaining clip after start offset
            actual_duration = min(segment_duration, clip.duration - start_time)

            # Look up musical section for this beat position
            current_time = beat_times[beat_idx] if beat_idx < len(beat_times) else timeline_pos
            section_label = None
            for sec in sections:
                if sec.start_time <= current_time < sec.end_time:
                    section_label = sec.label
                    break

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
                timeline_pos += actual_duration

            beat_idx += beat_count

        return segments

    def generate(
        self,
        audio_data: AudioAnalysisResult,
        video_clips: List[VideoAnalysisResult],
        output_path: str,
        audio_path: Optional[str] = None,
        observer: Optional[ProgressObserver] = None,
        pacing: Optional[PacingConfig] = None,
        broll_clips: Optional[List[VideoAnalysisResult]] = None,
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
            len(segments), total_dur,
        )
        if config.max_clips or config.max_duration_seconds:
            logger.info(
                "Test mode active — limits: max_clips=%s, max_duration=%.1fs",
                config.max_clips,
                config.max_duration_seconds or total_dur,
            )

        # Create temp directory for intermediate files
        temp_dir = tempfile.mkdtemp(prefix="montage_")

        try:
            # 2. Extract segments (one FFmpeg process at a time)
            segment_files = self._extract_segments(
                segments, temp_dir, config, observer
            )

            # 3. Group-and-transition or simple concat
            transitions_enabled = (
                config.transition_type
                and config.transition_type.lower() != "none"
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
                            file_idx:file_idx + len(group)
                        ]
                        file_idx += len(group)

                        if len(group_seg_files) == 1:
                            group_files.append(group_seg_files[0])
                        else:
                            group_out = os.path.join(
                                temp_dir, f"group_{g_idx:04d}.mp4"
                            )
                            self._concatenate_segments(
                                group_seg_files, group_out
                            )
                            group_files.append(group_out)

                    # Apply xfade transitions between groups
                    concat_path = os.path.join(
                        temp_dir, "concat_output.mp4"
                    )
                    self._apply_transitions(
                        group_files,
                        concat_path,
                        config.transition_type,
                        config.transition_duration,
                    )
                else:
                    # Only one section — fall back to simple concat
                    concat_path = os.path.join(
                        temp_dir, "concat_output.mp4"
                    )
                    self._concatenate_segments(
                        segment_files, concat_path
                    )
            else:
                # No transitions — simple concat (current behaviour)
                concat_path = os.path.join(
                    temp_dir, "concat_output.mp4"
                )
                self._concatenate_segments(segment_files, concat_path)

            # 4. Overlay audio (or just copy if no audio)
            if audio_path and os.path.exists(audio_path):
                self._overlay_audio(concat_path, audio_path, output_path)
            else:
                shutil.move(concat_path, output_path)

            logger.info("Montage complete: %s", output_path)
            return output_path

        finally:
            # Clean up temp directory (memory safety guarantee)
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _extract_segments(
        self,
        segments: List[SegmentPlan],
        temp_dir: str,
        config: PacingConfig,
        observer: Optional[ProgressObserver] = None,
    ) -> List[str]:
        """
        Extract each segment from its source video using FFmpeg.

        Only ONE FFmpeg process runs at a time. Each completes and
        releases all resources before the next starts.
        """
        segment_files: List[str] = []
        total = len(segments)

        for i, seg in enumerate(segments):
            if not os.path.exists(seg.video_path):
                logger.warning(
                    "Skipping segment %d/%d: source file missing: %s",
                    i + 1, total, seg.video_path,
                )
                continue

            if observer:
                observer.on_progress(
                    i, total, f"Extracting segment {i + 1}/{total}..."
                )

            output_file = os.path.join(temp_dir, f"seg_{i:04d}.mp4")

            # When speed-ramped, extract more (slow-mo) or less (fast)
            # source material so the output fills the planned duration.
            extract_duration = seg.duration * seg.speed_factor

            cmd = [
                "ffmpeg",
                "-y",                       # Overwrite output
                "-ss", f"{seg.start_time:.3f}",  # Seek to start
                "-i", seg.video_path,       # Input file
                "-t", f"{extract_duration:.3f}",  # Duration (adjusted for speed)
            ]

            # Build video filter chain:
            # 1. Resolution normalization (all segments → same size for xfade)
            # 2. Speed ramp via setpts (if needed)
            t_width = 1080 if config.is_shorts else TARGET_WIDTH
            t_height = 1920 if config.is_shorts else TARGET_HEIGHT

            if config.is_shorts:
                # Crop center to 9:16 aspect ratio (safe for both horizontal drop-ins and slight vertical variances)
                vf_parts = [
                    f"crop='min(iw,ih*9/16)':'min(ih,iw*16/9)'",
                    f"scale={t_width}:{t_height}",
                ]
            else:
                vf_parts = [
                    f"scale={t_width}:{t_height}"
                    f":force_original_aspect_ratio=decrease",
                    f"pad={t_width}:{t_height}:(ow-iw)/2:(oh-ih)/2",
                ]

            if seg.speed_factor != 1.0:
                vf_parts.append(f"setpts=PTS/{seg.speed_factor}")
                # FEAT-010: Smooth Slow Motion Interpolation
                if seg.speed_factor < 1.0 and config.interpolation_method != "none":
                    if config.interpolation_method == "mci":
                        vf_parts.append(f"minterpolate=fps={TARGET_FPS}:mi_mode=mci")
                    else:
                        vf_parts.append(f"minterpolate=fps={TARGET_FPS}:mi_mode=blend")
            
            # Normalize frame rate for ALL segments to ensure clean concatenation
            vf_parts.append(f"fps={TARGET_FPS}")
            
            cmd.extend(["-vf", ",".join(vf_parts)])

            cmd.extend([
                "-c:v", "libx264",          # Re-encode for consistent format
                "-preset", "fast",          # Fast encoding
                "-crf", "23",               # Good quality
                "-an",                      # Strip audio (overlaid later)
                "-pix_fmt", "yuv420p",      # Compatibility
                "-movflags", "+faststart",  # Web-friendly
                output_file,
            ])

            self._run_ffmpeg(cmd, f"segment extraction {i + 1}")
            segment_files.append(output_file)

        if observer:
            observer.on_progress(total, total, "Segment extraction complete.")

        return segment_files

    @staticmethod
    def _group_segments_by_section(
        segments: List[SegmentPlan],
    ) -> List[List[SegmentPlan]]:
        """
        Group consecutive segments that share the same section_label.

        Returns a list of groups, where each group is a list of
        SegmentPlan objects with the same musical section label.
        Adjacent segments with matching labels are merged into one group.
        """
        if not segments:
            return []

        groups: List[List[SegmentPlan]] = []
        current_group: List[SegmentPlan] = [segments[0]]

        for seg in segments[1:]:
            if seg.section_label == current_group[-1].section_label:
                current_group.append(seg)
            else:
                groups.append(current_group)
                current_group = [seg]

        groups.append(current_group)
        return groups

    def _concatenate_segments(
        self, segment_files: List[str], output_path: str
    ) -> None:
        """
        Concatenate extracted segments using FFmpeg concat demuxer.

        Uses a file list to avoid shell argument limits.
        """
        # Write concat file list
        concat_list_path = output_path + ".txt"
        try:
            with open(concat_list_path, "w") as f:
                for seg_file in segment_files:
                    # FFmpeg concat requires escaped single quotes
                    escaped = seg_file.replace("'", "'\\''")
                    f.write(f"file '{escaped}'\n")

            cmd = [
                "ffmpeg",
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_list_path,
                "-c", "copy",       # No re-encode (already consistent)
                output_path,
            ]

            self._run_ffmpeg(cmd, "segment concatenation")
        finally:
            if os.path.exists(concat_list_path):
                os.remove(concat_list_path)

    def _apply_transitions(
        self,
        group_files: List[str],
        output_path: str,
        transition_type: str,
        transition_duration: float,
    ) -> None:
        """
        Apply xfade transitions between group files.

        Uses FFmpeg's xfade filter to blend between section groups.
        Only processes pairs of files sequentially to keep memory bounded.

        Args:
            group_files: Ordered list of group video files.
            transition_type: FFmpeg xfade transition name (e.g. 'fade').
            transition_duration: Duration of each transition in seconds.
            output_path: Path for the final transitioned output.
        """
        if len(group_files) < 2:
            # Single group — just copy to output
            if group_files:
                shutil.copy2(group_files[0], output_path)
            return

        # Process transitions pairwise: A+B → AB, AB+C → ABC, etc.
        # Each step only buffers 2 streams = bounded memory.
        current_input = group_files[0]
        temp_dir = os.path.dirname(output_path)

        # Get duration of the first input for offset calculation
        current_duration = self._get_video_duration(current_input)

        for i in range(1, len(group_files)):
            next_input = group_files[i]
            is_last = (i == len(group_files) - 1)

            # Offset = current duration minus transition overlap
            offset = max(0.0, current_duration - transition_duration)

            if is_last:
                step_output = output_path
            else:
                step_output = os.path.join(
                    temp_dir, f"xfade_step_{i:04d}.mp4"
                )

            cmd = [
                "ffmpeg",
                "-y",
                "-i", current_input,
                "-i", next_input,
                "-filter_complex",
                f"[0:v][1:v]xfade=transition={transition_type}"
                f":duration={transition_duration:.3f}"
                f":offset={offset:.3f}[v]",
                "-map", "[v]",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-pix_fmt", "yuv420p",
                "-an",
                step_output,
            ]

            try:
                self._run_ffmpeg(cmd, f"transition {i}/{len(group_files) - 1}")
            except RuntimeError as e:
                logger.warning(
                    "xfade transition %d failed, falling back to concat: %s",
                    i, e,
                )
                # Fallback: just concatenate without transition
                self._concatenate_segments(
                    [current_input, next_input], step_output
                )

            # Eagerly clean up previous intermediate file (not a source group)
            if (
                current_input != group_files[0]
                and os.path.exists(current_input)
            ):
                os.remove(current_input)

            # Update for next iteration
            next_duration = self._get_video_duration(next_input)
            # New duration = old + new - overlap
            current_duration = (
                current_duration + next_duration - transition_duration
            )
            current_input = step_output

    @staticmethod
    def _get_video_duration(video_path: str) -> float:
        """
        Get the duration of a video file using ffprobe.

        Returns:
            Duration in seconds, or 0.0 if probe fails.
        """
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "csv=p=0",
                    video_path,
                ],
                capture_output=True,
                text=True,
                timeout=10,
                shell=False,
            )  # nosec B603
            return float(result.stdout.strip())
        except (ValueError, subprocess.TimeoutExpired, OSError):
            logger.warning(
                "Could not probe duration for %s, estimating.",
                video_path,
            )
            return 0.0

    def _overlay_audio(
        self, video_path: str, audio_path: str, output_path: str
    ) -> None:
        """
        Replace the video's audio track with the original song.

        Trims audio to match video duration automatically via -shortest.
        """
        cmd = [
            "ffmpeg",
            "-y",
            "-i", video_path,       # Video (no audio)
            "-i", audio_path,       # Audio source
            "-c:v", "copy",         # Don't re-encode video
            "-c:a", "aac",          # Encode audio to AAC
            "-b:a", "192k",         # Good audio quality
            "-shortest",            # Trim to shorter stream
            "-movflags", "+faststart",
            output_path,
        ]

        self._run_ffmpeg(cmd, "audio overlay")

    @staticmethod
    def _run_ffmpeg(cmd: List[str], stage_name: str) -> None:
        """
        Execute an FFmpeg command with timeout and error handling.

        Args:
            cmd: The FFmpeg command as a list of arguments.
            stage_name: Human-readable name for error messages.

        Raises:
            RuntimeError: If FFmpeg exits with non-zero or times out.
        """
        logger.debug("FFmpeg [%s]: %s", stage_name, ' '.join(cmd))

        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                timeout=FFMPEG_TIMEOUT,
                shell=False,
            )  # nosec B603

            if result.returncode != 0:
                stderr_tail = result.stderr[-500:] if result.stderr else ""
                raise RuntimeError(
                    f"FFmpeg failed during {stage_name} "
                    f"(exit code {result.returncode}): {stderr_tail}"
                )

        except subprocess.TimeoutExpired:
            raise RuntimeError(
                f"FFmpeg timed out during {stage_name} "
                f"(>{FFMPEG_TIMEOUT}s). The input file may be too large."
            )
