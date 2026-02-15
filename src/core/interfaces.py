"""
Core interfaces and protocols for Bachata Beat-Story Sync.
"""
from typing import Protocol, Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
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


class IVideoAnalyzer(Protocol):
    """
    Protocol for video analysis services.
    """
    def analyze(self, input_data: "VideoAnalysisInput") -> "VideoAnalysisResult":
        """
        Analyzes a video file to calculate a visual intensity score.
        """
        ...


class CacheBackend(Protocol):
    """
    Protocol for caching backends.
    """
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieves an item from the cache."""
        ...

    def set(self, key: str, value: Dict[str, Any]) -> None:
        """Stores an item in the cache."""
        ...

    def delete(self, key: str) -> None:
        """Removes an item from the cache."""
        ...
