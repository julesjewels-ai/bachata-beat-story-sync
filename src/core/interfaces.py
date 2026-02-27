"""
Core interfaces and protocols for Bachata Beat-Story Sync.
"""
from typing import Protocol, Optional, TYPE_CHECKING

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


class VideoAnalyzerProtocol(Protocol):
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


class AnalysisRepository(Protocol):
    """
    Protocol for persisting analysis results.
    """
    def get(self, key: str) -> Optional["VideoAnalysisResult"]:
        """
        Retrieves a cached analysis result by key.

        Args:
            key: The unique cache key.

        Returns:
            The cached result if found, else None.
        """
        ...

    def save(self, key: str, result: "VideoAnalysisResult") -> None:
        """
        Saves an analysis result to the cache.

        Args:
            key: The unique cache key.
            result: The analysis result to store.
        """
        ...
