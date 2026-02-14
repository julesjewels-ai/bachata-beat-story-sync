"""
Montage generator for Bachata Beat-Story Sync.

Uses direct FFmpeg subprocess calls for memory-safe video processing.
Only one FFmpeg process runs at a time — no memory leaks.
"""
import logging
import os
import shutil
import subprocess
import tempfile
from typing import List, Optional

from src.core.interfaces import ProgressObserver
from src.core.models import (
    AudioAnalysisResult,
    SegmentPlan,
    VideoAnalysisResult,
)

logger = logging.getLogger(__name__)

# Intensity thresholds for variable clip duration (FEAT-001)
HIGH_INTENSITY_THRESHOLD = 0.65
LOW_INTENSITY_THRESHOLD = 0.35

# Timeout per FFmpeg subprocess call (seconds)
FFMPEG_TIMEOUT = 60


class MontageGenerator:
    """
    Generates a video montage synchronized to audio analysis.

    Architecture:
        1. Build segment plan (pure Python — maps beats to clip durations)
        2. Extract segments (FFmpeg subprocess — one at a time)
        3. Concatenate segments (FFmpeg concat demuxer)
        4. Overlay audio (FFmpeg subprocess)
    """

    def build_segment_plan(
        self,
        audio_data: AudioAnalysisResult,
        video_clips: List[VideoAnalysisResult],
    ) -> List[SegmentPlan]:
        """
        Build a timeline of clip segments from audio beat/intensity data.

        Clip duration varies by intensity:
            - High (>=0.65): 2-beat duration (fast, energetic cuts)
            - Medium (0.35-0.65): 4-beat duration (standard)
            - Low (<0.35): 8-beat duration (breathing room)

        Args:
            audio_data: Analysed audio with beat_times and intensity_curve.
            video_clips: Available video clips sorted by intensity.

        Returns:
            Ordered list of SegmentPlan objects covering the audio duration.
        """
        if not video_clips:
            return []

        beat_times = audio_data.beat_times
        intensity_curve = audio_data.intensity_curve

        if not beat_times:
            return []

        # Calculate seconds-per-beat from BPM
        spb = 60.0 / audio_data.bpm if audio_data.bpm > 0 else 0.5

        # Sort clips by intensity score (highest first) for matching
        sorted_clips = sorted(
            video_clips, key=lambda c: c.intensity_score, reverse=True
        )

        segments: List[SegmentPlan] = []
        timeline_pos = 0.0
        beat_idx = 0
        clip_idx = 0

        while beat_idx < len(beat_times):
            # Determine intensity at this beat
            intensity = (
                intensity_curve[beat_idx]
                if beat_idx < len(intensity_curve)
                else 0.5
            )

            # Variable duration based on intensity
            if intensity >= HIGH_INTENSITY_THRESHOLD:
                beat_count = 2
                level = "high"
            elif intensity < LOW_INTENSITY_THRESHOLD:
                beat_count = 8
                level = "low"
            else:
                beat_count = 4
                level = "medium"

            # Don't exceed available beats
            beat_count = min(beat_count, len(beat_times) - beat_idx)
            segment_duration = beat_count * spb

            # Pick clip (round-robin)
            clip = sorted_clips[clip_idx % len(sorted_clips)]
            clip_idx += 1

            # Clamp start_time within clip bounds
            max_start = max(0.0, clip.duration - segment_duration)
            start_time = min(max_start, 0.0)

            # Clamp segment duration to clip length
            actual_duration = min(segment_duration, clip.duration)

            if actual_duration > 0:
                segments.append(
                    SegmentPlan(
                        video_path=clip.path,
                        start_time=start_time,
                        duration=actual_duration,
                        timeline_position=timeline_pos,
                        intensity_level=level,
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

        # 1. Build segment plan
        segments = self.build_segment_plan(audio_data, video_clips)
        if not segments:
            raise ValueError(
                "Could not build a segment plan — no beats detected "
                "in the audio analysis."
            )

        logger.info(
            f"Built segment plan: {len(segments)} segments, "
            f"total duration: {segments[-1].timeline_position + segments[-1].duration:.1f}s"
        )

        # Create temp directory for intermediate files
        temp_dir = tempfile.mkdtemp(prefix="montage_")

        try:
            # 2. Extract segments (one FFmpeg process at a time)
            segment_files = self._extract_segments(
                segments, temp_dir, observer
            )

            # 3. Concatenate segments
            concat_path = os.path.join(temp_dir, "concat_output.mp4")
            self._concatenate_segments(segment_files, concat_path)

            # 4. Overlay audio (or just copy if no audio)
            if audio_path and os.path.exists(audio_path):
                self._overlay_audio(concat_path, audio_path, output_path)
            else:
                shutil.move(concat_path, output_path)

            logger.info(f"Montage complete: {output_path}")
            return output_path

        finally:
            # Clean up temp directory (memory safety guarantee)
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _extract_segments(
        self,
        segments: List[SegmentPlan],
        temp_dir: str,
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
            if observer:
                observer.on_progress(
                    i, total, f"Extracting segment {i + 1}/{total}..."
                )

            output_file = os.path.join(temp_dir, f"seg_{i:04d}.mp4")

            cmd = [
                "ffmpeg",
                "-y",                       # Overwrite output
                "-ss", f"{seg.start_time:.3f}",  # Seek to start
                "-i", seg.video_path,       # Input file
                "-t", f"{seg.duration:.3f}",  # Duration
                "-c:v", "libx264",          # Re-encode for consistent format
                "-preset", "fast",          # Fast encoding
                "-crf", "23",               # Good quality
                "-an",                      # Strip audio (overlaid later)
                "-pix_fmt", "yuv420p",      # Compatibility
                "-movflags", "+faststart",  # Web-friendly
                output_file,
            ]

            self._run_ffmpeg(cmd, f"segment extraction {i + 1}")
            segment_files.append(output_file)

        if observer:
            observer.on_progress(total, total, "Segment extraction complete.")

        return segment_files

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
        logger.debug(f"FFmpeg [{stage_name}]: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=FFMPEG_TIMEOUT,
            )

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
