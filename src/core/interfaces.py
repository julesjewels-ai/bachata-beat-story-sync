"""
Core interfaces and protocols for Bachata Beat-Story Sync.
"""
from typing import Protocol, Any, Optional
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
    def analyze(self, input_data: VideoAnalysisInput) -> VideoAnalysisResult:
        """
        Analyzes a video file.

        Args:
            input_data: Validated input containing the file path.

        Returns:
            Analysis result including intensity score and duration.
        """
        ...


class CacheBackend(Protocol):
    """
    Protocol for cache backends.
    """
    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a value from the cache.

        Args:
            key: The cache key.

        Returns:
            The value if found, else None.
        """
        ...

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set a value in the cache.

        Args:
            key: The cache key.
            value: The value to store.
            ttl: Time to live in seconds (optional).
        """
        ...

    def delete(self, key: str) -> None:
        """
        Delete a value from the cache.

        Args:
            key: The cache key.
        """
        ...

    def clear(self) -> None:
        """
        Clear the entire cache.
        """
        ...
