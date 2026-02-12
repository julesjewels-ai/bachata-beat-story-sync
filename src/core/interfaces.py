"""
Core interfaces and protocols for Bachata Beat-Story Sync.
"""
from typing import Protocol, Optional
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
    """Protocol for video analysis services."""
    def analyze(self, input_data: VideoAnalysisInput) -> VideoAnalysisResult:
        """
        Analyzes a video file to calculate a visual intensity score.
        """
        ...


class CacheBackend(Protocol):
    """Protocol for caching backends."""
    def get(self, key: str) -> Optional[str]:
        """Retrieve a value from the cache."""
        ...

    def set(self, key: str, value: str) -> None:
        """Store a value in the cache."""
        ...
