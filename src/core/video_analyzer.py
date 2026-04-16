"""
Video analysis module for Bachata Beat-Story Sync.
"""

import logging
from collections.abc import Iterator
from typing import NamedTuple

import cv2
import numpy as np
from pydantic import BaseModel, Field, field_validator

from src.core.models import VideoAnalysisResult
from src.core.validation import validate_file_path
from src.core.ffmpeg_renderer import get_video_duration

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

# Scene-change detection (FEAT-020)
SCENE_CHANGE_THRESHOLD = 30.0  # Mean pixel diff to flag a scene change
MAX_SCENE_CHANGES = 5  # Keep only the strongest N changes per clip
OPENING_WINDOW_SECONDS = 2.0  # Window for computing opening_intensity


class IntensityResult(NamedTuple):
    """Return value of _calculate_intensity — typed for readability."""

    mean_motion: float
    scene_changes: list[float]
    opening_intensity: float


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
            duration = self._validate_video_properties(cap, file_path)

            # Check aspect ratio for vertical shorts (9:16)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            is_vertical = height > width

            thumbnail_data = self._extract_thumbnail(cap)

            # Reset frame position for intensity calculation
            if not cap.set(cv2.CAP_PROP_POS_FRAMES, 0):
                logger.warning("Could not reset frame position for %s", file_path)

            result = self._calculate_intensity(cap)

            return VideoAnalysisResult(
                path=file_path,
                intensity_score=result.mean_motion / NORMALIZATION_FACTOR,
                duration=duration,
                is_vertical=is_vertical,
                thumbnail_data=thumbnail_data,
                scene_changes=result.scene_changes,
                opening_intensity=result.opening_intensity,
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

    def _validate_video_properties(
        self, cap: cv2.VideoCapture, file_path: str
    ) -> float:
        """
        Validates frame count and duration to prevent DoS.
        Uses ffprobe for accurate duration (OpenCV CAP_PROP_FRAME_COUNT is unreliable).
        Returns the video duration in seconds.
        """
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Security Check: Prevent DoS via massive video files
        if frame_count > MAX_VIDEO_FRAMES:
            raise ValueError(
                f"Video exceeds maximum allowed frames ({MAX_VIDEO_FRAMES})"
            )

        # Get duration via ffprobe (more reliable than OpenCV's frame count)
        duration = get_video_duration(file_path)
        if duration <= 0:
            fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
            if frame_count > 0 and fps > 0:
                duration = frame_count / fps
                logger.warning(
                    "Could not probe duration for %s via ffprobe; "
                    "falling back to frame_count/fps (%.2fs)",
                    file_path,
                    duration,
                )

        if duration <= 0:
            raise ValueError(f"Could not determine duration for video: {file_path}")

        if duration > MAX_VIDEO_DURATION_SECONDS:
            raise ValueError(
                f"Video exceeds maximum duration ({MAX_VIDEO_DURATION_SECONDS}s)"
            )

        return duration

    def _calculate_intensity(
        self,
        cap: cv2.VideoCapture,
    ) -> IntensityResult:
        """Calculates motion intensity, scene changes, and opening intensity.

        Samples frames at ANALYSIS_FPS and downscales to
        ANALYSIS_RESOLUTION to minimise memory usage.

        Returns:
            IntensityResult with mean_motion, scene_changes, opening_intensity.
        """
        video_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        skip = max(1, int(video_fps / ANALYSIS_FPS))

        prev_frame = None
        motion_scores: list[float] = []
        # FEAT-020: collect (timestamp, score) for scene-change candidates
        scene_candidates: list[tuple[float, float]] = []
        opening_scores: list[float] = []
        frame_idx = 0

        for frame in self._yield_frames(cap):
            if frame_idx % skip != 0:
                frame_idx += 1
                continue

            timestamp = frame_idx / video_fps

            # Downscale to small resolution before processing
            small = cv2.resize(frame, ANALYSIS_RESOLUTION)
            processed_frame = self._preprocess_frame(small)

            if prev_frame is not None:
                frame_delta = cv2.absdiff(prev_frame, processed_frame)
                score = float(np.mean(frame_delta))
                motion_scores.append(score)

                # FEAT-020: scene-change detection
                if score >= SCENE_CHANGE_THRESHOLD:
                    scene_candidates.append((timestamp, score))

                # FEAT-020: opening intensity (first N seconds)
                if timestamp <= OPENING_WINDOW_SECONDS:
                    opening_scores.append(score)

            prev_frame = processed_frame
            frame_idx += 1

        mean_motion = float(np.mean(motion_scores)) if motion_scores else 0.0

        # Keep only the strongest scene changes, sorted by timestamp
        scene_candidates.sort(key=lambda x: x[1], reverse=True)
        top_changes = scene_candidates[:MAX_SCENE_CHANGES]
        scene_changes = sorted(t for t, _ in top_changes)

        opening_intensity = (
            float(np.mean(opening_scores)) / NORMALIZATION_FACTOR
            if opening_scores
            else 0.0
        )

        return IntensityResult(
            mean_motion=mean_motion,
            scene_changes=scene_changes,
            opening_intensity=opening_intensity,
        )

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
