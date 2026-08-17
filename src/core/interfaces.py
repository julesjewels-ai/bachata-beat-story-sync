"""
Core interfaces and protocols for Bachata Beat-Story Sync.
"""

from collections.abc import Iterable
from typing import Any, Protocol

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


class ManagedProgressObserver(ProgressObserver, Protocol):
    """ProgressObserver that also supports context manager usage."""

    def __enter__(self) -> "ManagedProgressObserver": ...

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None: ...

    def close(self) -> None: ...


class VideoAnalysisRepository(Protocol):
    """
    Protocol for repositories storing video analysis results.
    """

    def get_by_path(self, file_path: str) -> VideoAnalysisResult | None:
        """Retrieves a cached analysis result by its exact file path."""
        ...

    def save(self, result: VideoAnalysisResult) -> None:
        """Saves an analysis result."""
        ...

    def get_all(self) -> Iterable[VideoAnalysisResult]:
        """Retrieves all saved analysis results."""
        ...
