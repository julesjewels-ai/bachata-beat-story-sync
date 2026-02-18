"""
Core interfaces and protocols for Bachata Beat-Story Sync.
"""
from typing import Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.models import VideoAnalysisResult
    from src.core.video_analyzer import VideoAnalysisInput


class IVideoAnalyzer(Protocol):
    """
    Protocol for video analysis implementations.
    """
    def analyze(self, input_data: "VideoAnalysisInput") -> "VideoAnalysisResult":
        """
        Analyze a video file and return its properties.

        Args:
            input_data: Validated input containing the file path.

        Returns:
            Analysis result including intensity score and duration.
        """
        ...


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
