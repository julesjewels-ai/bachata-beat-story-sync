"""
Core interfaces and protocols for Bachata Beat-Story Sync.
"""
from typing import Protocol, Optional, TYPE_CHECKING, Dict, Any

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
    Protocol for video analysis services.
    """
    def analyze(self, input_data: "VideoAnalysisInput") -> "VideoAnalysisResult":
        """
        Analyzes a video file to calculate a visual intensity score.

        Args:
            input_data: Validated input containing the file path.

        Returns:
            A VideoAnalysisResult with the video's path, intensity score,
            and duration.
        """
        ...


class CacheBackend(Protocol):
    """
    Protocol for key-value cache storage backends.
    """
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve a value from the cache."""
        ...

    def set(self, key: str, value: Dict[str, Any]) -> None:
        """Store a value in the cache."""
        ...
