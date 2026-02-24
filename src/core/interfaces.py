"""
Core interfaces and protocols for Bachata Beat-Story Sync.
"""
from typing import Protocol, List, TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.models import AudioAnalysisResult, VideoAnalysisResult, SegmentPlan


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


class TimelineExporter(Protocol):
    """
    Protocol for exporting timeline data to external formats (EDL, XML, etc).
    """
    def export(self, plans: List['SegmentPlan'], output_path: str, fps: float = 30.0) -> str:
        """
        Export the segment plans to a file.

        Args:
            plans: List of segment plans to export.
            output_path: Path to the output file.
            fps: Frames per second of the project.

        Returns:
            The path to the exported file.
        """
        ...


class ReportGenerator(Protocol):
    """
    Protocol for generating analysis reports.
    """
    def generate_report(self,
                        audio_data: 'AudioAnalysisResult',
                        video_data: List['VideoAnalysisResult'],
                        output_path: str) -> str:
        """
        Generates a report from analysis data.

        Args:
            audio_data: The audio analysis result.
            video_data: List of video analysis results.
            output_path: Destination path for the report file.

        Returns:
            The path to the generated file.
        """
        ...
