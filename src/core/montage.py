"""
Montage generation module for Bachata Beat-Story Sync.
Handles the synchronization of video clips to audio.
"""
import logging
import random
import os
from typing import List, Optional, Tuple, Dict
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips
from src.core.models import AudioAnalysisResult, VideoAnalysisResult

logger = logging.getLogger(__name__)


class MontageGenerator:
    """
    Generates a video montage by syncing video clips to audio beats.
    """

    def _get_audio_segment_intensity(
        self,
        start_time: float,
        end_time: float,
        peaks: List[float],
        avg_density: float
    ) -> str:
        """
        Determines intensity level ('low', 'medium', 'high') for a time segment.
        Based on peak density relative to the track's average density.
        """
        duration = end_time - start_time
        if duration <= 0:
            return 'low'

        segment_peaks = [p for p in peaks if start_time <= p < end_time]
        local_density = len(segment_peaks) / duration

        if avg_density <= 0:
            return 'medium'

        ratio = local_density / avg_density

        if ratio > 1.2:
            return 'high'
        elif ratio < 0.8:
            return 'low'
        else:
            return 'medium'

    def _categorize_videos(
        self, video_results: List[VideoAnalysisResult]
    ) -> Dict[str, List[VideoAnalysisResult]]:
        """
        Splits videos into intensity buckets (low, medium, high).
        """
        if not video_results:
            return {'low': [], 'medium': [], 'high': []}

        sorted_videos = sorted(video_results, key=lambda x: x.intensity_score)
        n = len(sorted_videos)

        # Simple thirds split
        low_idx = n // 3
        high_idx = (2 * n) // 3

        return {
            'low': sorted_videos[:low_idx],
            'medium': sorted_videos[low_idx:high_idx],
            'high': sorted_videos[high_idx:]
        }

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

    def _get_next_video(
        self,
        intensity: str,
        video_buckets: Dict[str, List[VideoAnalysisResult]],
        used_queue: Dict[str, List[VideoAnalysisResult]]
    ) -> Optional[VideoAnalysisResult]:
        """
        Selects a video from the appropriate bucket, handling fallback and refill.
        """
        # Fallback order
        preferences = [intensity]
        if intensity == 'high':
            preferences.extend(['medium', 'low'])
        elif intensity == 'medium':
            preferences.extend(['high', 'low'])
        else:  # low
            preferences.extend(['medium', 'high'])

        for pref in preferences:
            bucket = used_queue[pref]
            if not bucket:
                # Refill from source if empty
                source = video_buckets[pref]
                if source:
                    bucket = list(source)
                    random.shuffle(bucket)
                    used_queue[pref] = bucket

            if bucket:
                return bucket.pop()

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

        # Filter out videos that are too short for the target bar duration
        # This prevents infinite loops and ensures quality
        valid_videos = [
            v for v in video_results if v.duration >= bar_duration
        ]

        if not valid_videos:
            logger.warning("No videos found with sufficient duration.")
            # If no videos are long enough, we can't generate a proper montage.
            # We could fallback to using whatever we have, but it's risky.
            raise ValueError(
                f"All videos are shorter than the required bar duration ({bar_duration:.2f}s)"
            )

        # Categorize videos
        video_buckets = self._categorize_videos(valid_videos)
        # Create working queues
        queues = {
            k: list(v) for k, v in video_buckets.items()
        }
        for k in queues:
            random.shuffle(queues[k])

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

            # Calculate average peak density
            total_peaks = len(audio_result.peaks)
            avg_density = total_peaks / duration if duration > 0 else 0

            current_time = 0.0
            attempts = 0
            # Rough safety break to prevent infinite loops
            max_attempts = int((duration / bar_duration) * 10) + len(video_results)

            while current_time < duration and attempts < max_attempts:
                remaining = duration - current_time
                seg_duration = min(bar_duration, remaining)

                # Determine Audio Intensity
                intensity = self._get_audio_segment_intensity(
                    current_time,
                    current_time + seg_duration,
                    audio_result.peaks,
                    avg_density
                )

                # Get Video
                video_data = self._get_next_video(
                    intensity, video_buckets, queues
                )

                if not video_data:
                    logger.error("Could not find any video clip.")
                    break

                result = self._create_video_segment(video_data, seg_duration)
                if result:
                    segment, source = result
                    clips.append(segment)
                    source_clips.append(source)
                    current_time += seg_duration
                else:
                    # Failed to process this specific video, loop continues
                    pass

                attempts += 1

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
