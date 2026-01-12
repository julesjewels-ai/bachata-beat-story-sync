"""
Video analysis module for Bachata Beat-Story Sync.
"""
import cv2
import numpy as np
import os
import logging
from typing import Dict, Any
from pydantic import BaseModel, Field, field_validator, ValidationError

logger = logging.getLogger(__name__)

# Security constants to prevent DoS
MAX_VIDEO_FRAMES = 100_000  # Approx 1 hour at 30 FPS
MAX_VIDEO_DURATION_SECONDS = 3600  # 1 hour

SUPPORTED_VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv'}

class VideoAnalysisInput(BaseModel):
    """
    Input model for video analysis validation.
    """
    file_path: str = Field(..., description="Path to the video file")

    @field_validator('file_path')
    @classmethod
    def validate_path(cls, v: str) -> str:
        if not os.path.exists(v):
            raise ValueError(f"Video file not found: {v}")

        # Security: Allowlist extensions
        _, ext = os.path.splitext(v)
        if ext.lower() not in SUPPORTED_VIDEO_EXTENSIONS:
            raise ValueError(f"Unsupported video extension: {ext}")
        return v

class VideoAnalyzer:
    """
    Analyzes video files to determine their visual intensity and other metrics.
    """

    def analyze(self, input_data: VideoAnalysisInput) -> Dict[str, Any]:
        """
        Analyzes a video file to calculate a visual intensity score.

        Args:
            input_data: Validated input containing the file path.

        Returns:
            A dictionary with the video's path, intensity score, and duration.
        """
        file_path = input_data.file_path

        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            raise IOError(f"Could not open video file: {file_path}")

        try:
            frame_rate = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            # Security Check: Prevent DoS via massive video files
            if frame_count > MAX_VIDEO_FRAMES:
                raise ValueError(f"Video exceeds maximum allowed frames ({MAX_VIDEO_FRAMES})")

            duration = frame_count / frame_rate if frame_rate > 0 else 0
            if duration > MAX_VIDEO_DURATION_SECONDS:
                 raise ValueError(f"Video exceeds maximum duration ({MAX_VIDEO_DURATION_SECONDS}s)")

            prev_frame = None
            motion_scores = []

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray_frame = cv2.GaussianBlur(gray_frame, (21, 21), 0)

                if prev_frame is not None:
                    frame_delta = cv2.absdiff(prev_frame, gray_frame)
                    motion_score = np.mean(frame_delta)
                    motion_scores.append(motion_score)

                prev_frame = gray_frame

            intensity_score = np.mean(motion_scores) if motion_scores else 0.0

            return {
                "path": file_path,
                "intensity_score": intensity_score / 100,  # Normalize score
                "duration": duration
            }
        finally:
            cap.release()
