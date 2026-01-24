from typing import Protocol

class ProgressObserver(Protocol):
    """
    Protocol for objects that observe progress of long-running operations.
    """
    def on_progress(self, current: int, total: int, message: str = "") -> None:
        """
        Called to update progress.

        Args:
            current: The current item count processed.
            total: The total number of items to process.
            message: Optional status message.
        """
        ...
