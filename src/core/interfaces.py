"""
Core interfaces and protocols for Bachata Beat-Story Sync.
"""

from typing import Protocol, TypeVar

from src.core.models import VideoAnalysisResult

T = TypeVar("T")


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
    """
    Protocol for video analysis inputs.
    """

    file_path: str


class VideoAnalyzerProtocol(Protocol):
    """
    Protocol for video analysis services.
    """

    def analyze(self, input_data: VideoAnalysisInputProtocol) -> VideoAnalysisResult:
        """
        Analyzes a video file.

        Args:
            input_data: Validated input containing the file path.

        Returns:
            A VideoAnalysisResult.
        """
        ...


class RepositoryProtocol(Protocol[T]):
    """
    Generic protocol for persistence repositories.
    """

    def get(self, key: str) -> T | None:
        """Retrieve an item by its key."""
        ...

    def save(self, key: str, item: T) -> None:
        """Save an item with the given key."""
        ...
