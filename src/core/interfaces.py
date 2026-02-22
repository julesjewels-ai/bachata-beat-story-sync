"""
Core interfaces and protocols for Bachata Beat-Story Sync.
"""
from typing import Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.models import DiagnosticResult


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


class DiagnosticCheck(Protocol):
    """
    Protocol for a system diagnostic check.
    """
    def run(self) -> "DiagnosticResult":
        """
        Executes the check and returns a result.

        Returns:
            A DiagnosticResult object indicating PASS/WARN/FAIL.
        """
        ...
