"""
Montage generation module for Bachata Beat-Story Sync.
Handles the synchronization of video clips to audio.
"""
import logging
import random
import os
from typing import Dict, List, Optional, Tuple
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips
from src.core.models import AudioAnalysisResult, VideoAnalysisResult

logger = logging.getLogger(__name__)


class MontageGenerator:
    """
    Generates a video montage by syncing video clips to audio beats.
    """

    def _categorize_videos(
        self, video_results: List[VideoAnalysisResult]
    ) -> Dict[str, List[VideoAnalysisResult]]:
        """Categorizes videos into intensity buckets."""
        buckets: Dict[str, List[VideoAnalysisResult]] = {
            "low": [],
            "medium": [],
            "high": []
        }
        for video in video_results:
            if video.intensity_score > 0.7:
                buckets["high"].append(video)
            elif video.intensity_score < 0.3:
                buckets["low"].append(video)
            else:
                buckets["medium"].append(video)

        # Shuffle buckets for randomness
        for key in buckets:
            random.shuffle(buckets[key])

        return buckets

    def _get_next_video(
        self,
        target_intensity: str,
        active_buckets: Dict[str, List[VideoAnalysisResult]],
        master_buckets: Dict[str, List[VideoAnalysisResult]]
    ) -> Optional[VideoAnalysisResult]:
        """
        Selects the next video based on target intensity with fallback logic.
        """
        # Define fallback priorities
        priorities = {
            "high": ["high", "medium", "low"],
            "medium": ["medium", "low", "high"],
            "low": ["low", "medium", "high"]
        }

        search_order = priorities.get(target_intensity, ["medium", "low", "high"])

        for intensity in search_order:
            bucket = active_buckets[intensity]

            # Refill if empty
            if not bucket:
                if master_buckets[intensity]:
                    bucket.extend(master_buckets[intensity])
                    random.shuffle(bucket)

            if bucket:
                return bucket.pop()

        return None

    def _create_video_segment(
        self,
        video_data: VideoAnalysisResult,
        target_duration: float
    ) -> Optional[Tuple[VideoFileClip, VideoFileClip]]:
        """
        Creates a video segment of the specified duration from the given video data.
        Returns:
            Tuple[VideoFileClip, VideoFileClip]: (processed_segment, source_clip)
            The source_clip must be kept open while the segment is used.
        """
        if not os.path.exists(video_data.path):
            logger.warning(f"Video file not found: {video_data.path}")
            return None

        try:
            video_clip = VideoFileClip(video_data.path)

            # Handle short videos
            if video_clip.duration < target_duration:
                # Skip short videos for now
                video_clip.close()
                return None

            # Extract subclip
            max_start = max(0, video_clip.duration - target_duration)
            start_t = random.uniform(0, max_start)
            sub = video_clip.subclipped(
                start_t, start_t + target_duration
            )

            # Standardize resolution (HD 720p height)
            processed = sub.resized(height=720)
            return processed, video_clip

        except Exception as e:
            logger.warning(
                f"Error processing clip {video_data.path}: {e}"
            )
            return None

    def generate(
        self,
        audio_result: AudioAnalysisResult,
        video_results: List[VideoAnalysisResult],
        output_path: str
    ) -> str:
        """
        Generates the video montage.

        Args:
            audio_result: Analysis result of the audio track.
            video_results: List of analyzed video clips.
            output_path: Path where the output video will be saved.

        Returns:
            The path to the generated video file.
        """
        if not video_results:
            raise ValueError("No video clips provided for montage generation.")

        logger.info(f"Generating montage for {audio_result.filename}...")

        # Calculate timing
        bpm = audio_result.bpm
        if bpm <= 0:
            bpm = 120  # Fallback
            logger.warning("Invalid BPM detected, using fallback 120 BPM.")

        beat_duration = 60.0 / bpm
        bar_duration = beat_duration * 4  # Change clip every 4 beats

        audio_clip = None
        final_video = None
        clips: List[VideoFileClip] = []
        source_clips: List[VideoFileClip] = []

        try:
            if not os.path.exists(audio_result.file_path):
                raise FileNotFoundError(
                    f"Audio file not found: {audio_result.file_path}"
                )

            audio_clip = AudioFileClip(audio_result.file_path)
            duration = audio_clip.duration

            current_time = 0.0
            attempts = 0
            max_attempts = len(video_results) * 5  # Increase allowance

            # Initialize buckets
            master_buckets = self._categorize_videos(video_results)
            active_buckets: Dict[str, List[VideoAnalysisResult]] = {
                k: list(v) for k, v in master_buckets.items()
            }

            while current_time < duration and attempts < max_attempts:
                remaining = duration - current_time
                seg_duration = min(bar_duration, remaining)

                # Determine intensity based on peaks
                # Check if current time is near a peak
                is_high_intensity = any(
                    abs(peak - current_time) < (bar_duration / 2)
                    for peak in audio_result.peaks
                )
                target_intensity = "high" if is_high_intensity else "medium"

                # Select a video clip
                video_data = self._get_next_video(
                    target_intensity, active_buckets, master_buckets
                )

                if not video_data:
                    logger.warning("No video available despite fallback.")
                    break

                attempts += 1

                result = self._create_video_segment(video_data, seg_duration)
                if result:
                    segment, source = result
                    clips.append(segment)
                    source_clips.append(source)
                    current_time += seg_duration
                    attempts = 0  # Reset attempts on success

            if not clips:
                raise RuntimeError("No valid video clips could be generated.")

            # Concatenate
            logger.info(f"Stitching {len(clips)} clips...")
            final_video = concatenate_videoclips(clips, method="compose")

            # Set Audio
            final_video = final_video.with_audio(audio_clip)

            # Write Output
            logger.info(f"Writing output to {output_path}...")
            final_video.write_videofile(
                output_path,
                codec="libx264",
                audio_codec="aac",
                fps=24,
                logger=None,
                preset='ultrafast'
            )

            return output_path

        except Exception as e:
            logger.error(f"Error generating montage: {e}")
            raise e
        finally:
            # Cleanup
            if audio_clip:
                audio_clip.close()
            if final_video:
                final_video.close()
            for clip in clips:
                try:
                    clip.close()
                except Exception:
                    pass
            for source in source_clips:
                try:
                    source.close()
                except Exception:
                    pass
