"""
Core interfaces and protocols for Bachata Beat-Story Sync.
"""
from typing import Protocol, Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.models import VideoAnalysisInput, VideoAnalysisResult


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


class IVideoAnalyzer(Protocol):
    """
    Protocol for video analysis services.
    """
    def analyze(self, input_data: "VideoAnalysisInput") -> "VideoAnalysisResult":
        """
        Analyzes a video file.

        Args:
            input_data: Validated input containing the file path.

        Returns:
            Analysis result containing intensity score, duration, etc.
        """
        ...


class CacheBackend(Protocol):
    """
    Protocol for cache backends.
    """
    def get(self, key: str) -> Optional[Any]:
        """
        Retrieves a value from the cache.

        Args:
            key: The cache key.

        Returns:
            The cached value, or None if not found.
        """
        ...

    def set(self, key: str, value: Any) -> None:
        """
        Sets a value in the cache.

        Args:
            key: The cache key.
            value: The value to cache.
        """
        ...

    def delete(self, key: str) -> None:
        """
        Deletes a value from the cache.

        Args:
            key: The cache key.
        """
        ...
