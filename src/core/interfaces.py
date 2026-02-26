"""
Core interfaces and protocols for Bachata Beat-Story Sync.
"""
from typing import Protocol, Optional
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


class VideoAnalyzerProtocol(Protocol):
    """
    Protocol for video analysis services.
    """
    def analyze(self, input_data: VideoAnalysisInput) -> VideoAnalysisResult:
        """
        Analyzes a video file to calculate a visual intensity score.
        """
        ...


class AnalysisRepository(Protocol):
    """
    Protocol for persisting analysis results.
    """
    def save_video_analysis(self, key: str, result: VideoAnalysisResult) -> None:
        """Saves a video analysis result."""
        ...

    def get_video_analysis(self, key: str) -> Optional[VideoAnalysisResult]:
        """Retrieves a video analysis result by key."""
        ...
