"""
Console UI implementation using Rich.
"""
from typing import Optional
from rich.console import Console
from rich.progress import (
    Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn, TaskID
)
from src.core.interfaces import ProgressObserver

class RichConsole(ProgressObserver):
    """
    Implementation of ProgressObserver using Rich library.
    """
    def __init__(self) -> None:
        self.console = Console()
        self.progress: Optional[Progress] = None
        self.task_id: Optional[TaskID] = None

    def on_progress(self, current: int, total: int, message: str = "") -> None:
        """
        Updates the progress bar.
        """
        if self.progress is None:
            # Start a new progress bar instance if not active
            self.progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeRemainingColumn(),
                console=self.console,
                transient=True
            )
            self.progress.start()
            self.task_id = self.progress.add_task(message or "Processing...", total=total)

        if self.task_id is not None:
            self.progress.update(
                self.task_id, completed=current, description=message or "Processing..."
            )

        # Cleanup if done
        if current >= total:
            self.stop()

    def stop(self) -> None:
        """Stops the progress display."""
        if self.progress:
            self.progress.stop()
            self.progress = None
            self.task_id = None

    def print(self, message: str, style: str = "white") -> None:
        """Helper to print styled messages."""
        self.console.print(message, style=style)
