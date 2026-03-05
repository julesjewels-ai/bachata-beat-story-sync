"""
Console UI implementations using Rich.
"""

from rich.progress import BarColumn, Progress, SpinnerColumn, TaskID, TextColumn


class RichProgressObserver:
    """
    Implementation of ProgressObserver using the Rich library.

    Supports context manager usage to guarantee cleanup on error::

        with RichProgressObserver() as observer:
            engine.scan_video_library(directory, observer=observer)
    """

    def __init__(self) -> None:
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        )
        self.task_id: TaskID | None = None
        self.started = False

    # --- Context manager protocol ---

    def __enter__(self) -> "RichProgressObserver":
        return self

    from typing import Any

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
        return None

    def close(self) -> None:
        """Stop the progress bar if it is still running."""
        if self.started:
            self.progress.stop()
            self.started = False

    # --- ProgressObserver protocol ---

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
            self.close()
