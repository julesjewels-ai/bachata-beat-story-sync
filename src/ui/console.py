"""
Console UI implementations using Rich.
"""
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from src.core.interfaces import ProgressObserver

class RichProgressObserver:
    """
    Implementation of ProgressObserver using the Rich library.
    """
    def __init__(self) -> None:
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        )
        self.task_id = None
        self.started = False

    def on_progress(self, current: int, total: int, message: str = "") -> None:
        """
        Updates the rich progress bar.
        """
        if not self.started:
            self.progress.start()
            self.task_id = self.progress.add_task(message, total=total)
            self.started = True

        # Check if task_id is valid before updating
        if self.task_id is not None:
            self.progress.update(self.task_id, completed=current, description=message)

        if current >= total and self.started:
            self.progress.stop()
            self.started = False
