"""
Montage generation module for Bachata Beat-Story Sync.
Handles the synchronization of video clips to audio.
"""
import logging
import random
import os
import numpy as np
from typing import List, Optional, Tuple, Dict
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips, vfx
from src.core.models import AudioAnalysisResult, VideoAnalysisResult

logger = logging.getLogger(__name__)


class MontageGenerator:
    """
    Generates a video montage by syncing video clips to audio beats.
    """

    def _get_speed_factor(self, intensity: str) -> float:
        """
        Returns a playback speed multiplier based on audio intensity.

        Low intensity  → 0.7x  (slow-motion, emotional/breakdown)
        Medium intensity → 1.0x (normal speed)
        High intensity → 1.2x  (slight speed-up, energetic)
        """
        factors = {'low': 0.7, 'medium': 1.0, 'high': 1.2}
        return factors.get(intensity, 1.0)

    def _create_video_segment(
        self,
        video_data: VideoAnalysisResult,
        target_duration: float,
        intensity: str = 'medium'
    ) -> Optional[Tuple[VideoFileClip, VideoFileClip]]:
        """
        Creates a video segment of the specified duration from the given video data.
        Applies speed ramping based on audio intensity.
        Returns:
            Tuple[VideoFileClip, VideoFileClip]: (processed_segment, source_clip)
            The source_clip must be kept open while the segment is used.
        """
        if not os.path.exists(video_data.path):
            logger.warning(f"Video file not found: {video_data.path}")
            return None

        try:
            speed_factor = self._get_speed_factor(intensity)
            # Slow-mo needs more source footage; speed-up needs less
            source_duration = target_duration / speed_factor

            video_clip = VideoFileClip(video_data.path)

            # Handle short videos (check against source_duration)
            if video_clip.duration < source_duration:
                # Skip short videos for now
                video_clip.close()
                return None

            # Extract subclip (using source_duration for raw footage)
            max_start = max(0, video_clip.duration - source_duration)
            start_t = random.uniform(0, max_start)
            sub = video_clip.subclipped(
                start_t, start_t + source_duration
            )

            # Standardize resolution (HD 720p height)
            processed = sub.resized(height=720)

            # Apply speed ramping (only if not normal speed)
            if speed_factor != 1.0:
                processed = processed.fx(
                    vfx.speedx, speed_factor
                )
                logger.debug(
                    f"Applied {speed_factor}x speed to segment "
                    f"(intensity={intensity})"
                )

            return processed, video_clip

        except Exception as e:
            logger.warning(
                f"Error processing clip {video_data.path}: {e}"
            )
            return None

    def _bucket_videos(
        self, video_results: List[VideoAnalysisResult]
    ) -> Dict[str, List[VideoAnalysisResult]]:
        """
        Classifies videos into intensity buckets.
        """
        buckets: Dict[str, List[VideoAnalysisResult]] = {
            'low': [],
            'medium': [],
            'high': []
        }

        for v in video_results:
            if v.intensity_score < 0.3:
                buckets['low'].append(v)
            elif v.intensity_score < 0.7:
                buckets['medium'].append(v)
            else:
                buckets['high'].append(v)

        # Shuffle for randomness
        for key in buckets:
            random.shuffle(buckets[key])

        return buckets

    def _get_audio_intensity(
        self,
        start_time: float,
        end_time: float,
        peaks: List[float],
        percentiles: Tuple[float, float]
    ) -> str:
        """
        Determines audio intensity for a time segment based on peak density.
        """
        # Count peaks in the segment
        peak_count = sum(1 for p in peaks if start_time <= p < end_time)

        p33, p66 = percentiles
        if peak_count <= p33:
            return 'low'
        elif peak_count <= p66:
            return 'medium'
        else:
            return 'high'

    def _get_segment_duration(
        self, intensity: str, beat_duration: float
    ) -> float:
        """
        Returns the segment duration in seconds based on audio intensity.

        High intensity  → 2-beat cuts  (fast, energetic)
        Medium intensity → 4-beat bars  (standard)
        Low intensity   → 8-beat holds (breathing room)
        """
        multipliers = {'high': 2, 'medium': 4, 'low': 8}
        return beat_duration * multipliers.get(intensity, 4)

    def _calculate_peak_percentiles(
        self, duration: float, bar_duration: float, peaks: List[float]
    ) -> Tuple[float, float]:
        """
        Calculates the 33rd and 66th percentiles of peaks per bar.
        """
        peak_counts = []
        t = 0.0
        while t < duration:
            count = sum(1 for p in peaks if t <= p < t + bar_duration)
            peak_counts.append(count)
            t += bar_duration

        if not peak_counts:
            return 0.0, 0.0

        return (
            float(np.percentile(peak_counts, 33)),
            float(np.percentile(peak_counts, 66))
        )

    def _get_next_video(
        self,
        intensity: str,
        buckets: Dict[str, List[VideoAnalysisResult]]
    ) -> Optional[VideoAnalysisResult]:
        """
        Selects a video from the requested intensity bucket with fallback.
        Priority: Match -> Adjacent -> Any
        """
        # Define fallback priorities
        priorities = {
            'low': ['low', 'medium', 'high'],
            'medium': ['medium', 'high', 'low'],
            'high': ['high', 'medium', 'low']
        }

        check_order = priorities.get(intensity, ['medium', 'low', 'high'])

        for bucket_name in check_order:
            if buckets[bucket_name]:
                # Rotate the list to avoid reuse immediately if possible
                video = buckets[bucket_name].pop(0)
                buckets[bucket_name].append(video)  # Re-add to end for recycling
                return video

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
        # Reference bar (4 beats) used for consistent percentile calculation
        reference_bar = beat_duration * 4

        # Prepare buckets and audio analysis
        buckets = self._bucket_videos(video_results)
        peak_percentiles = self._calculate_peak_percentiles(
            audio_result.duration, reference_bar, audio_result.peaks
        )

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
            # Safety cap uses smallest possible segment (2 beats)
            min_seg = beat_duration * 2
            max_segments = int(duration / min_seg) + 10 if min_seg > 0 else 1000

            while current_time < duration and len(clips) < max_segments:
                remaining = duration - current_time

                # Peek at intensity using the reference bar window
                peek_end = min(current_time + reference_bar, duration)
                audio_intensity = self._get_audio_intensity(
                    current_time,
                    peek_end,
                    audio_result.peaks,
                    peak_percentiles
                )

                # Variable segment duration based on intensity
                seg_duration = min(
                    self._get_segment_duration(audio_intensity, beat_duration),
                    remaining
                )

                # Select video
                video_data = self._get_next_video(audio_intensity, buckets)

                if not video_data:
                    # This should theoretically not happen due to fallbacks unless ALL buckets empty
                    logger.error("No videos available in any bucket.")
                    break

                result = self._create_video_segment(
                    video_data, seg_duration, audio_intensity
                )

                if result:
                    segment, source = result
                    clips.append(segment)
                    source_clips.append(source)
                    current_time += seg_duration
                    attempts = 0
                else:
                    attempts += 1
                    # If we fail to create a segment multiple times, we might need to skip or force something
                    # But for now, just continue loop, _get_next_video rotates so we get a different one
                    if attempts > 10:
                        logger.warning("Failed to create segment after multiple attempts. Advancing time.")
                        current_time += seg_duration  # Skip this segment to avoid infinite loop

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
            self._cleanup_resources(audio_clip, final_video, clips, source_clips)

    def _cleanup_resources(
        self,
        audio_clip: Optional[AudioFileClip],
        final_video: Optional[VideoFileClip],
        clips: List[VideoFileClip],
        source_clips: List[VideoFileClip]
    ) -> None:
        """Helper to clean up resources."""
        if audio_clip:
            try:
                audio_clip.close()
            except Exception:
                pass
        if final_video:
            try:
                final_video.close()
            except Exception:
                pass
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
