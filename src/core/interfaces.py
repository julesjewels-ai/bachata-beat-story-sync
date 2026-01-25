from typing import Protocol

class ProgressObserver(Protocol):
    """
    Protocol for objects that can observe progress of long-running operations.
    """
    def on_progress(self, current: int, total: int, message: str = "") -> None:
        """
        Called when progress is made.

        Args:
            current: The current number of items processed.
            total: The total number of items to process.
            message: A descriptive message about the current operation.
        """
        ...
