"""
Core interfaces and protocols for Bachata Beat-Story Sync.
"""
from typing import Protocol, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.video_analyzer import VideoAnalysisInput
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


class CacheBackend(Protocol):
    """
    Protocol for cache backends.
    Allows different storage mechanisms (JSON, SQLite, Redis) to be swapped.
    """
    def get(self, key: str) -> Optional[Any]:
        """Retrieves a value from the cache."""
        ...

    def set(self, key: str, value: Any) -> None:
        """Sets a value in the cache."""
        ...

    def delete(self, key: str) -> None:
        """Deletes a value from the cache."""
        ...

    def clear(self) -> None:
        """Clears the entire cache."""
        ...


class IVideoAnalyzer(Protocol):
    """
    Protocol for video analysis services.
    Decouples the sync engine from the concrete analyzer implementation.
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
