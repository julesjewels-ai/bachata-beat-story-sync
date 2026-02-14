"""
Memory-safe montage generator for Bachata Beat-Story Sync.

Uses an open-close-per-clip pattern to prevent memory leaks:
- Only ONE VideoFileClip is open at a time
- Each segment is written to a temp file, then the clip is closed
- Final concatenation uses a single FFmpeg pass
"""
import logging
import os
import tempfile
import subprocess
from dataclasses import dataclass
from typing import List, Optional, Tuple

from src.core.models import AudioAnalysisResult, VideoAnalysisResult

logger = logging.getLogger(__name__)

# Intensity thresholds for beat-count mapping
HIGH_INTENSITY_THRESHOLD = 0.65
LOW_INTENSITY_THRESHOLD = 0.35

# Beat multipliers for segment duration
BEATS_HIGH = 2    # Fast, energetic cuts
BEATS_MEDIUM = 4  # Standard bar
BEATS_LOW = 8     # Breathing room / holds


@dataclass
class SegmentPlan:
    """A planned segment in the montage timeline."""
    clip_path: str
    clip_start: float
    segment_duration: float
    intensity: float


class MontageGenerator:
    """
    Generates a video montage synchronized to audio analysis.

    Memory-safe design:
    - Opens at most 1 VideoFileClip at a time
    - Each segment rendered to a temp file, clip closed immediately
    - Final output assembled via FFmpeg concat demuxer
    """

    def generate(
        self,
        audio_data: AudioAnalysisResult,
        video_clips: List[VideoAnalysisResult],
        output_path: str,
        audio_path: Optional[str] = None,
    ) -> str:
        """
        Generate a montage video synchronized to the audio.

        Args:
            audio_data: Analyzed audio features (BPM, peaks, duration).
            video_clips: Analyzed video clips with intensity scores.
            output_path: Path for the final output video.
            audio_path: Optional path to audio file to overlay.

        Returns:
            Path to the generated output video.

        Raises:
            ValueError: If no video clips are provided.
            RuntimeError: If montage generation fails.
        """
        if not video_clips:
            raise ValueError("No video clips provided for montage.")

        logger.info(
            f"Building montage: {len(video_clips)} clips, "
            f"{audio_data.bpm} BPM, {audio_data.duration:.1f}s duration"
        )

        # 1. Build the segment plan
        segment_plan = self._build_segment_plan(audio_data, video_clips)
        logger.info(f"Segment plan: {len(segment_plan)} segments")

        # 2. Render each segment to a temp file (ONE clip open at a time)
        temp_dir = tempfile.mkdtemp(prefix="montage_")
        temp_files: List[str] = []

        try:
            for i, segment in enumerate(segment_plan):
                temp_path = os.path.join(temp_dir, f"seg_{i:04d}.mp4")
                self._render_segment(segment, temp_path)
                temp_files.append(temp_path)
                logger.info(
                    f"Rendered segment {i + 1}/{len(segment_plan)}: "
                    f"{segment.segment_duration:.2f}s"
                )

            # 3. Concatenate all segments into the final output
            self._concatenate_segments(
                temp_files, output_path, audio_path
            )
            logger.info(f"Montage saved to: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Montage generation failed: {e}")
            raise RuntimeError(f"Montage generation failed: {e}") from e
        finally:
            # Cleanup temp files
            self._cleanup_temp_files(temp_files, temp_dir)

    def _build_segment_plan(
        self,
        audio_data: AudioAnalysisResult,
        video_clips: List[VideoAnalysisResult],
    ) -> List[SegmentPlan]:
        """
        Build a list of segments that cover the full audio duration.

        Segments have variable duration based on local audio intensity
        (peak density in each window).
        """
        beat_duration = 60.0 / audio_data.bpm
        total_duration = audio_data.duration
        peaks = sorted(audio_data.peaks)

        segments: List[SegmentPlan] = []
        current_time = 0.0

        while current_time < total_duration:
            # Calculate local intensity based on peak density
            local_intensity = self._calculate_local_intensity(
                current_time, beat_duration * BEATS_MEDIUM, peaks
            )

            # Map intensity to beat count
            beat_count = self._intensity_to_beat_count(local_intensity)
            segment_duration = beat_duration * beat_count

            # Don't overshoot the audio duration
            remaining = total_duration - current_time
            if segment_duration > remaining:
                segment_duration = remaining
            if segment_duration < 0.1:
                break

            # Select the best clip for this intensity
            clip = self._select_clip_for_intensity(
                local_intensity, video_clips
            )

            # Calculate a start offset within the clip
            clip_start = self._calculate_clip_start(
                clip, segment_duration
            )

            segments.append(SegmentPlan(
                clip_path=clip.path,
                clip_start=clip_start,
                segment_duration=segment_duration,
                intensity=local_intensity,
            ))

            current_time += segment_duration

        return segments

    @staticmethod
    def _calculate_local_intensity(
        time_pos: float, window: float, peaks: List[float]
    ) -> float:
        """
        Calculate the local intensity at a given time position
        based on peak density within a window.

        Returns a value between 0.0 and 1.0.
        """
        window_start = time_pos
        window_end = time_pos + window
        peak_count = sum(
            1 for p in peaks if window_start <= p < window_end
        )

        # Normalize: ~8+ peaks in a 4-beat window → max intensity
        max_expected_peaks = 8
        return min(peak_count / max_expected_peaks, 1.0)

    @staticmethod
    def _intensity_to_beat_count(intensity: float) -> int:
        """
        Map audio intensity to beat count for segment duration.

        - High intensity (≥0.65) → 2-beat cuts (fast, energetic)
        - Medium intensity (0.35–0.65) → 4-beat bars (standard)
        - Low intensity (<0.35) → 8-beat holds (breathing room)
        """
        if intensity >= HIGH_INTENSITY_THRESHOLD:
            return BEATS_HIGH
        elif intensity >= LOW_INTENSITY_THRESHOLD:
            return BEATS_MEDIUM
        else:
            return BEATS_LOW

    @staticmethod
    def _select_clip_for_intensity(
        target_intensity: float,
        video_clips: List[VideoAnalysisResult],
    ) -> VideoAnalysisResult:
        """
        Select the video clip whose visual intensity best matches
        the target audio intensity.
        """
        return min(
            video_clips,
            key=lambda c: abs(c.intensity_score - target_intensity)
        )

    @staticmethod
    def _calculate_clip_start(
        clip: VideoAnalysisResult, segment_duration: float
    ) -> float:
        """
        Calculate a safe start time within the clip for the segment.

        Uses a deterministic offset based on clip duration to get
        varied but reproducible content from each clip.
        """
        available = clip.duration - segment_duration
        if available <= 0:
            return 0.0
        # Use golden ratio offset for visual variety
        golden_ratio = 0.618
        return available * golden_ratio

    def _render_segment(
        self, segment: SegmentPlan, temp_path: str
    ) -> None:
        """
        Render a single segment to a temp file.

        MEMORY SAFETY: Opens ONE clip, extracts subclip, writes, closes.
        """
        from moviepy import VideoFileClip  # Lazy import (moviepy v2)

        clip = None
        subclip = None
        try:
            clip = VideoFileClip(segment.clip_path)

            # Calculate safe end time
            end_time = min(
                segment.clip_start + segment.segment_duration,
                clip.duration
            )
            start_time = max(0, end_time - segment.segment_duration)

            subclip = clip.subclip(start_time, end_time)

            # Write without audio (we overlay the master audio later)
            subclip.write_videofile(
                temp_path,
                codec="libx264",
                audio=False,
                logger=None,  # Suppress MoviePy's verbose output
                preset="ultrafast",
            )
        finally:
            # CRITICAL: Always close to prevent FFmpeg process leaks
            if subclip is not None:
                try:
                    subclip.close()
                except Exception:
                    pass
            if clip is not None:
                try:
                    clip.close()
                except Exception:
                    pass

    def _concatenate_segments(
        self,
        temp_files: List[str],
        output_path: str,
        audio_path: Optional[str] = None,
    ) -> None:
        """
        Concatenate temp segment files into the final output
        using FFmpeg's concat demuxer (no Python clip objects).

        Optionally overlays the original audio track.
        """
        if not temp_files:
            raise ValueError("No segments to concatenate.")

        # Build FFmpeg concat file
        concat_list = os.path.join(
            os.path.dirname(temp_files[0]), "concat.txt"
        )
        with open(concat_list, 'w') as f:
            for temp_file in temp_files:
                # FFmpeg concat format requires escaped paths
                escaped = temp_file.replace("'", "'\\''")
                f.write(f"file '{escaped}'\n")

        # Get ffmpeg binary from imageio (bundled with moviepy)
        ffmpeg_binary = self._get_ffmpeg_binary()

        # Build FFmpeg command
        cmd = [
            ffmpeg_binary,
            "-y",  # Overwrite output
            "-f", "concat",
            "-safe", "0",
            "-i", concat_list,
        ]

        if audio_path and os.path.exists(audio_path):
            cmd.extend([
                "-i", audio_path,
                "-c:v", "copy",
                "-c:a", "aac",
                "-shortest",
            ])
        else:
            cmd.extend(["-c", "copy"])

        cmd.append(output_path)

        logger.info(f"Concatenating {len(temp_files)} segments...")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode != 0:
            logger.error(f"FFmpeg concat failed: {result.stderr}")
            raise RuntimeError(
                f"FFmpeg concatenation failed: {result.stderr[:500]}"
            )

    @staticmethod
    def _get_ffmpeg_binary() -> str:
        """Get the FFmpeg binary path from imageio (bundled with moviepy)."""
        try:
            from imageio_ffmpeg import get_ffmpeg_exe
            return get_ffmpeg_exe()
        except ImportError:
            # Fallback to system ffmpeg
            return "ffmpeg"

    @staticmethod
    def _cleanup_temp_files(
        temp_files: List[str], temp_dir: str
    ) -> None:
        """Clean up temporary segment files and directory."""
        for f in temp_files:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except OSError as e:
                logger.warning(f"Failed to remove temp file {f}: {e}")

        # Also remove concat list if it exists
        concat_list = os.path.join(temp_dir, "concat.txt")
        try:
            if os.path.exists(concat_list):
                os.remove(concat_list)
        except OSError:
            pass

        try:
            os.rmdir(temp_dir)
        except OSError as e:
            logger.warning(f"Failed to remove temp dir {temp_dir}: {e}")
