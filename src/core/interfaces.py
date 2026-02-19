"""
Core interfaces and protocols for Bachata Beat-Story Sync.
"""
from typing import Protocol, List, TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.models import AudioAnalysisResult, VideoAnalysisResult


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


class ReportGenerator(Protocol):
    """
    Protocol for generating analysis reports in various formats.
    """
    def generate(self, audio_data: "AudioAnalysisResult",
                 video_data: List["VideoAnalysisResult"],
                 output_path: str) -> str:
        """
        Generates a report file.

        Args:
            audio_data: The audio analysis result.
            video_data: List of video analysis results.
            output_path: Destination path for the report file.

        Returns:
            The path to the generated file.
        """
        ...
