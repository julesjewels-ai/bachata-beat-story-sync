"""
Core interfaces and protocols for Bachata Beat-Story Sync.
"""

from typing import Protocol

from src.core.models import VideoAnalysisResult


class VideoAnalysisInputProtocol(Protocol):
    """
    Protocol for video analysis input.
    """
    file_path: str


class VideoAnalyzerProtocol(Protocol):
    """
    Protocol for objects that can analyze video files.
    """

    def analyze(self, input_data: VideoAnalysisInputProtocol) -> VideoAnalysisResult:
        """
        Analyzes a video file and returns the result.

        Args:
            input_data: The input configuration for the analysis.

        Returns:
            A VideoAnalysisResult containing the analysis data.
        """
        ...


class AnalysisRepositoryProtocol(Protocol):
    """
    Protocol for objects that persist and retrieve analysis results.
    """

    def get_video_analysis(self, video_path: str) -> VideoAnalysisResult | None:
        """
        Retrieves a cached video analysis result.

        Args:
            video_path: The path of the video file.

        Returns:
            The cached VideoAnalysisResult, or None if not found or invalid.
        """
        ...

    def save_video_analysis(self, result: VideoAnalysisResult) -> None:
        """
        Saves a video analysis result to the cache.

        Args:
            result: The analysis result to save.
        """
        ...


class ProgressObserver(Protocol):
    """
    Protocol for objects that observe progress of long-running operations.
    """

    def on_progress(self, current: int, total: int, message: str = "") -> None:
        """
        Called to update progress.

        Args:
            current: The current number of items processed.
            total: The total number of items to process.
            message: A descriptive message about the current operation.
        """
        ...
