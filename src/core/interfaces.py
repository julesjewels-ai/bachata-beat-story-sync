"""
Core interfaces and protocols for Bachata Beat-Story Sync.
"""
from typing import Protocol, Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.models import VideoAnalysisResult
    from src.core.video_analyzer import VideoAnalysisInput


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
    Protocol for video analysis components.
    """
    def analyze(self, input_data: "VideoAnalysisInput") -> "VideoAnalysisResult":
        """
        Analyzes a video file to calculate visual metrics.

        Args:
            input_data: Validated input containing the file path.

        Returns:
            A VideoAnalysisResult with the analysis data.
        """
        ...


class CacheBackend(Protocol):
    """
    Protocol for caching backends.
    """
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a value from the cache.

        Args:
            key: The cache key.

        Returns:
            The cached value (dictionary) or None if not found.
        """
        ...

    def set(self, key: str, value: Dict[str, Any]) -> None:
        """
        Sets a value in the cache.

        Args:
            key: The cache key.
            value: The value to cache (must be serializable to the backend format).
        """
        ...
