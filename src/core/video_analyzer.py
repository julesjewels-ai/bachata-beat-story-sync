"""
Video analysis module for Bachata Beat-Story Sync.
"""
import cv2
import numpy as np
import os
from typing import Dict, Any

class VideoAnalyzer:
    """
    Analyzes video files to determine their visual intensity and other metrics.
    """

    def analyze(self, file_path: str) -> Dict[str, Any]:
        """
        Analyzes a video file to calculate a visual intensity score.

        Args:
            file_path: The path to the video file.

        Returns:
            A dictionary with the video's path, intensity score, and duration.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Video file not found: {file_path}")

        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            raise IOError(f"Could not open video file: {file_path}")

        frame_rate = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / frame_rate if frame_rate > 0 else 0

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

        cap.release()

        intensity_score = np.mean(motion_scores) if motion_scores else 0.0

        return {
            "path": file_path,
            "intensity_score": intensity_score / 100,  # Normalize score
            "duration": duration
        }
