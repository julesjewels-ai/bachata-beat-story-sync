"""
Core interfaces and protocols for Bachata Beat-Story Sync.
"""
from typing import Protocol, List
from src.core.models import SegmentPlan


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
    Protocol for services that export montage plans to external timeline formats.
    """
    def export(
        self,
        plans: List[SegmentPlan],
        output_path: str,
        fps: float = 30.0
    ) -> str:
        """
        Exports the montage plan to a timeline file (e.g., EDL, XML).

        Args:
            plans: The list of segment plans to export.
            output_path: The destination path for the exported file.
            fps: The target frame rate for timecode calculations.

        Returns:
            The path to the exported file.
        """
        ...
