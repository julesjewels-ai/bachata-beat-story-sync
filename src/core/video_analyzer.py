"""
Video analysis module for Bachata Beat-Story Sync.
"""
import cv2
import numpy as np
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator
from src.core.validation import validate_file_path
from src.core.models import VideoAnalysisResult

logger = logging.getLogger(__name__)

# Security constants to prevent DoS
MAX_VIDEO_FRAMES = 100_000  # Approx 1 hour at 30 FPS
MAX_VIDEO_DURATION_SECONDS = 3600  # 1 hour

SUPPORTED_VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv'}
BLUR_KERNEL_SIZE = (21, 21)
NORMALIZATION_FACTOR = 100

class VideoAnalysisInput(BaseModel):
    """
    Input model for video analysis validation.
    """
    file_path: str = Field(..., description="Path to the video file")

    @field_validator('file_path')
    @classmethod
    def validate_path(cls, v: str) -> str:
        return validate_file_path(v, SUPPORTED_VIDEO_EXTENSIONS)

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
            thumbnail_data = self._extract_thumbnail(cap)

            return VideoAnalysisResult(
                path=file_path,
                intensity_score=intensity_score / NORMALIZATION_FACTOR,
                duration=duration,
                thumbnail_data=thumbnail_data
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
        # Reset position to start just in case, though usually it starts at 0.
        # However, _validate uses .get() so it shouldn't move.
        # But let's be safe if we reuse this method.
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

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

    def _extract_thumbnail(self, cap: cv2.VideoCapture) -> Optional[bytes]:
        """
        Extracts a thumbnail from the middle of the video.
        """
        try:
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if frame_count <= 0:
                return None

            middle_frame = frame_count // 2
            cap.set(cv2.CAP_PROP_POS_FRAMES, middle_frame)

            ret, frame = cap.read()
            if not ret:
                logger.warning("Could not read frame for thumbnail.")
                return None

            # Resize to save space (e.g., height 100px)
            height, width = frame.shape[:2]
            target_height = 100
            if height > 0:
                scale = target_height / height
                target_width = int(width * scale)
                resized = cv2.resize(frame, (target_width, target_height))
            else:
                resized = frame # Should not happen if ret is True

            # Encode as JPEG
            success, encoded_img = cv2.imencode('.jpg', resized)
            if not success:
                return None

            return encoded_img.tobytes()

        except Exception as e:
            logger.warning(f"Thumbnail extraction failed: {e}")
            return None
