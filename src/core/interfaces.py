"""
Core interfaces and protocols for Bachata Beat-Story Sync.
"""
from typing import Protocol, Optional
from src.core.models import VideoAnalysisResult


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


class VideoAnalysisInputProtocol(Protocol):
    """Protocol for video analysis input to decouple concrete models."""
    @property
    def file_path(self) -> str:
        ...


class VideoAnalyzerProtocol(Protocol):
    """Protocol for analyzing video files."""
    def analyze(self, input_data: VideoAnalysisInputProtocol) -> VideoAnalysisResult:
        """
        Analyzes a video file.
        """
        ...


class AnalysisRepository(Protocol):
    """Protocol for persisting analysis results."""
    def save(self, result: VideoAnalysisResult) -> None:
        """Saves a video analysis result."""
        ...

    def get(self, file_path: str) -> Optional[VideoAnalysisResult]:
        """
        Retrieves a saved video analysis result by its source file path.
        Returns None if not found or invalid.
        """
        ...
