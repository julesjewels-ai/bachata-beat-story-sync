"""
Core interfaces and protocols for Bachata Beat-Story Sync.
"""
from typing import Protocol, Optional, Any
from src.core.models import VideoAnalysisResult, VideoAnalysisInput


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


class CacheBackend(Protocol):
    """
    Protocol for cache backends (e.g., JSON file, Redis).
    """
    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a value from the cache.
        Returns None if the key does not exist.
        """
        ...

    def set(self, key: str, value: Any) -> None:
        """
        Store a JSON-serializable value in the cache.
        """
        ...

    def delete(self, key: str) -> None:
        """
        Remove a value from the cache.
        """
        ...


class IVideoAnalyzer(Protocol):
    """
    Protocol for video analysis services.
    """
    def analyze(self, input_data: VideoAnalysisInput) -> VideoAnalysisResult:
        """
        Analyzes a video file to calculate a visual intensity score.

        Args:
            input_data: Validated input containing the file path.

        Returns:
            A VideoAnalysisResult with the video's path, intensity score,
            and duration.
        """
        ...
