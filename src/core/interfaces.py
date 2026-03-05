"""
Core interfaces and protocols for Bachata Beat-Story Sync.
"""

from typing import Protocol

from src.core.models import VideoAnalysisResult


class VideoAnalysisInputProtocol(Protocol):
    """
    Protocol defining the input required for video analysis.
    """

    file_path: str


class VideoAnalyzerProtocol(Protocol):
    """
    Protocol for objects that can analyze video files.
    """

    def analyze(self, input_data: VideoAnalysisInputProtocol) -> VideoAnalysisResult:
        """Analyzes a video file and returns its metrics."""
        ...


class AnalysisRepository(Protocol):
    """
    Protocol for persisting and retrieving analysis results.
    """

    def get_analysis(self, file_path: str) -> VideoAnalysisResult | None:
        """Retrieves cached analysis for a file, or None if not found."""
        ...

    def save_analysis(self, file_path: str, result: VideoAnalysisResult) -> None:
        """Persists the analysis result for a file."""
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
