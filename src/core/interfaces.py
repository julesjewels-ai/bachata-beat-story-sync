"""
Core interfaces and protocols for Bachata Beat-Story Sync.
"""

from typing import Protocol

from src.core.models import VideoAnalysisResult


class BachataDomainError(Exception):
    """Base exception for all domain-specific errors."""

    pass


class CacheError(BachataDomainError):
    """Raised when there is an issue with caching."""

    pass


class VideoAnalysisInputProtocol(Protocol):
    """Protocol for video analysis inputs to decouple from concrete models."""

    file_path: str


class VideoAnalyzerProtocol(Protocol):
    """Protocol for core video analyzers."""

    def analyze(
        self, input_data: VideoAnalysisInputProtocol
    ) -> VideoAnalysisResult: ...


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
