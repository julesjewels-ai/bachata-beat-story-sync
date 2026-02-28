"""
Core interfaces and protocols for Bachata Beat-Story Sync.
"""
from typing import Protocol, TYPE_CHECKING, Optional

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
    Protocol for analyzing video files.
    """
    def analyze(self, input_data: 'VideoAnalysisInput') -> 'VideoAnalysisResult':
        """
        Analyzes a video file to calculate visual metrics.
        """
        ...


class AnalysisRepository(Protocol):
    """
    Protocol for persisting analysis results.
    """
    def get_video_analysis(self, cache_key: str) -> Optional['VideoAnalysisResult']:
        """
        Retrieves a cached video analysis result by key.
        """
        ...

    def save_video_analysis(self, cache_key: str, result: 'VideoAnalysisResult') -> None:
        """
        Persists a video analysis result using the given key.
        """
        ...
