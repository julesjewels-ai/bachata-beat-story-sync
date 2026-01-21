"""
Core interfaces and protocols for Bachata Beat-Story Sync.
"""
from typing import Protocol, Optional

class ProgressObserver(Protocol):
    """
    Protocol for observing progress of long-running operations.
    """
    def on_progress(self, current: int, total: int, message: str = "") -> None:
        """
        Called when progress is made.

        Args:
            current: The current item count processed.
            total: The total number of items to process.
            message: Optional status message.
        """
        ...
