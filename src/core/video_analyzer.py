"""
Video analysis module for Bachata Beat-Story Sync.
"""
import cv2
import numpy as np
import logging
from src.core.models import VideoAnalysisResult, VideoAnalysisInput
from src.core.constants import (
    MAX_VIDEO_FRAMES,
    MAX_VIDEO_DURATION_SECONDS,
    BLUR_KERNEL_SIZE,
    NORMALIZATION_FACTOR
)

logger = logging.getLogger(__name__)

class VideoAnalyzer:
    """
    Analyzes video files to determine their visual intensity and other metrics.
    """

    def analyze(self, input_data: VideoAnalysisInput) -> VideoAnalysisResult:
        """
        Analyzes a video file to calculate a visual intensity score.

        Args:
            input_data: Validated input containing the file path.

        Returns:
            A VideoAnalysisResult with the video's path, intensity score, and duration.
        """
        file_path = input_data.file_path

        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            raise IOError(f"Could not open video file: {file_path}")

        try:
            duration = self._validate_video_properties(cap)
            intensity_score = self._calculate_intensity(cap)

            return VideoAnalysisResult(
                path=file_path,
                intensity_score=intensity_score / NORMALIZATION_FACTOR,
                duration=duration
            )
        finally:
            cap.release()

    def _validate_video_properties(self, cap: cv2.VideoCapture) -> float:
        """
        Validates frame count and duration to prevent DoS.
        Returns the video duration in seconds.
        """
        frame_rate = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Security Check: Prevent DoS via massive video files
        if frame_count > MAX_VIDEO_FRAMES:
            raise ValueError(f"Video exceeds maximum allowed frames ({MAX_VIDEO_FRAMES})")

        duration = frame_count / frame_rate if frame_rate > 0 else 0
        if duration > MAX_VIDEO_DURATION_SECONDS:
            raise ValueError(f"Video exceeds maximum duration ({MAX_VIDEO_DURATION_SECONDS}s)")

        return duration

    def _calculate_intensity(self, cap: cv2.VideoCapture) -> float:
        """Calculates the average motion intensity of the video."""
        prev_frame = None
        motion_scores = []

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray_frame = cv2.GaussianBlur(gray_frame, BLUR_KERNEL_SIZE, 0)

            if prev_frame is not None:
                frame_delta = cv2.absdiff(prev_frame, gray_frame)
                motion_scores.append(np.mean(frame_delta))

            prev_frame = gray_frame

        return np.mean(motion_scores) if motion_scores else 0.0
