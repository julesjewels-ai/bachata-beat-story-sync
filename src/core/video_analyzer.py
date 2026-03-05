"""
Video analysis module for Bachata Beat-Story Sync.
"""

import logging
from collections.abc import Iterator

import cv2
import numpy as np
from pydantic import BaseModel, Field, field_validator

from src.core.models import VideoAnalysisResult
from src.core.validation import validate_file_path

logger = logging.getLogger(__name__)

# Security constants to prevent DoS
MAX_VIDEO_FRAMES = 100_000  # Approx 1 hour at 30 FPS
MAX_VIDEO_DURATION_SECONDS = 3600  # 1 hour

SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}
BLUR_KERNEL_SIZE = (21, 21)
NORMALIZATION_FACTOR = 100

# Performance: sample at this FPS for intensity analysis (saves ~90% memory)
ANALYSIS_FPS = 3.0
# Performance: downscale frames to this resolution for analysis
ANALYSIS_RESOLUTION = (320, 180)


class VideoAnalysisInput(BaseModel):
    """
    Input model for video analysis validation.
    """

    file_path: str = Field(..., description="Path to the video file")

    @field_validator("file_path")
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
            A VideoAnalysisResult with the video's path, intensity score,
            and duration.
        """
        file_path = input_data.file_path

        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            raise OSError(f"Could not open video file: {file_path}")

        try:
            duration = self._validate_video_properties(cap)

            # Check aspect ratio for vertical shorts (9:16)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            is_vertical = height > width

            thumbnail_data = self._extract_thumbnail(cap)

            # Reset frame position for intensity calculation
            if not cap.set(cv2.CAP_PROP_POS_FRAMES, 0):
                logger.warning("Could not reset frame position for %s", file_path)

            intensity_score = self._calculate_intensity(cap)

            return VideoAnalysisResult(
                path=file_path,
                intensity_score=intensity_score / NORMALIZATION_FACTOR,
                duration=duration,
                is_vertical=is_vertical,
                thumbnail_data=thumbnail_data,
            )
        finally:
            cap.release()

    def _extract_thumbnail(self, cap: cv2.VideoCapture) -> bytes | None:
        """Extracts a thumbnail from the middle of the video."""
        try:
            frame = self._get_middle_frame(cap)
            if frame is None:
                return None

            frame = self._resize_frame(frame)

            success, buffer = cv2.imencode(".png", frame)
            if not success:
                return None

            return buffer.tobytes()
        except Exception as e:
            logger.warning("Failed to extract thumbnail: %s", e)
            return None

    def _get_middle_frame(self, cap: cv2.VideoCapture) -> np.ndarray | None:
        """Retrieves the frame at the middle of the video."""
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if frame_count <= 0:
            return None

        middle_frame = frame_count // 2
        cap.set(cv2.CAP_PROP_POS_FRAMES, middle_frame)

        ret, frame = cap.read()
        return frame if ret else None

    def _resize_frame(self, frame: np.ndarray, max_width: int = 160) -> np.ndarray:
        """Resizes the frame while preserving aspect ratio."""
        height, width = frame.shape[:2]
        if width <= max_width:
            return frame

        scale_ratio = max_width / width
        new_width = max_width
        new_height = int(height * scale_ratio)
        return cv2.resize(frame, (new_width, new_height))

    def _validate_video_properties(self, cap: cv2.VideoCapture) -> float:
        """
        Validates frame count and duration to prevent DoS.
        Returns the video duration in seconds.
        """
        frame_rate = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Security Check: Prevent DoS via massive video files
        if frame_count > MAX_VIDEO_FRAMES:
            raise ValueError(
                f"Video exceeds maximum allowed frames ({MAX_VIDEO_FRAMES})"
            )

        duration = frame_count / frame_rate if frame_rate > 0 else 0
        if duration > MAX_VIDEO_DURATION_SECONDS:
            raise ValueError(
                f"Video exceeds maximum duration ({MAX_VIDEO_DURATION_SECONDS}s)"
            )

        return duration

    def _calculate_intensity(self, cap: cv2.VideoCapture) -> float:
        """Calculates the average motion intensity of the video.

        Samples frames at ANALYSIS_FPS and downscales to
        ANALYSIS_RESOLUTION to minimise memory usage.
        """
        video_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        skip = max(1, int(video_fps / ANALYSIS_FPS))

        prev_frame = None
        motion_scores = []
        frame_idx = 0

        for frame in self._yield_frames(cap):
            if frame_idx % skip != 0:
                frame_idx += 1
                continue

            # Downscale to small resolution before processing
            small = cv2.resize(frame, ANALYSIS_RESOLUTION)
            processed_frame = self._preprocess_frame(small)

            if prev_frame is not None:
                frame_delta = cv2.absdiff(prev_frame, processed_frame)
                motion_scores.append(np.mean(frame_delta))

            prev_frame = processed_frame
            frame_idx += 1

        return np.mean(motion_scores) if motion_scores else 0.0

    def _yield_frames(self, cap: cv2.VideoCapture) -> Iterator[np.ndarray]:
        """Yields frames from the video capture until end of stream."""
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            yield frame

    def _preprocess_frame(self, frame: np.ndarray) -> np.ndarray:
        """Converts frame to grayscale and applies Gaussian blur."""
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return cv2.GaussianBlur(gray_frame, BLUR_KERNEL_SIZE, 0)
