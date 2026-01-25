from typing import Optional
from rich.progress import Progress, TaskID, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.console import Console
from src.core.interfaces import ProgressObserver

class RichConsole:
    """
    Console UI implementation using Rich.
    Implements ProgressObserver to display progress bars.
    """
    def __init__(self) -> None:
        self.console = Console()
        self.progress: Optional[Progress] = None
        self.task_id: Optional[TaskID] = None

    def on_progress(self, current: int, total: int, message: str = "") -> None:
        """
        Updates the progress bar.

        Args:
            current: The current number of items processed.
            total: The total number of items to process.
            message: A descriptive message about the current operation.
        """
        if self.progress is None:
            self.progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=self.console
            )
            self.progress.start()

        if self.task_id is None:
            self.task_id = self.progress.add_task(description=message, total=total)

        # Update existing task
        self.progress.update(self.task_id, completed=current, total=total, description=message)

        # Auto-stop if complete
        if current >= total:
            self.stop()

    def stop(self) -> None:
        """Stops the progress display."""
        if self.progress:
            self.progress.stop()
            self.progress = None
            self.task_id = None

    def print(self, message: str) -> None:
        """Prints a message to the console."""
        self.console.print(message)
