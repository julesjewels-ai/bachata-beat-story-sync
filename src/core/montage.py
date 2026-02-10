"""
Montage generation module for Bachata Beat-Story Sync.
Handles the synchronization of video clips to audio.
"""
import logging
import random
import os
from typing import List, Optional, Tuple
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips
from src.core.models import AudioAnalysisResult, VideoAnalysisResult

logger = logging.getLogger(__name__)


class MontageGenerator:
    """
    Generates a video montage by syncing video clips to audio beats.
    """

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

    def _collect_video_segments(
        self,
        clips: List[VideoFileClip],
        source_clips: List[VideoFileClip],
        total_duration: float,
        bar_duration: float,
        video_results: List[VideoAnalysisResult]
    ) -> None:
        """
        Collects video segments to fill the total duration.
        Populates the provided clips and source_clips lists.
        """
        current_time = 0.0
        attempts = 0
        max_attempts = len(video_results) * 2

        # Use a queue to ensure variety
        video_queue = list(video_results)
        random.shuffle(video_queue)

        while current_time < total_duration and attempts < max_attempts:
            remaining = total_duration - current_time
            seg_duration = min(bar_duration, remaining)

            # Refill queue if empty
            if not video_queue:
                video_queue = list(video_results)
                random.shuffle(video_queue)

            # Select a video clip
            video_data = video_queue.pop()
            attempts += 1

            result = self._create_video_segment(video_data, seg_duration)
            if result:
                segment, source = result
                clips.append(segment)
                source_clips.append(source)
                current_time += seg_duration
                attempts = 0  # Reset attempts on success

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

            self._collect_video_segments(
                clips, source_clips, duration, bar_duration, video_results
            )

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
