"""
Console UI implementation using Rich.
"""
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from src.core.interfaces import ProgressObserver

class RichConsole(ProgressObserver):
    """
    Implementation of ProgressObserver using Rich.
    """
    def __init__(self):
        self.console = Console()
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console
        )
        self.task_id = None
        self._started = False

    def start(self, description: str, total: int):
        """Starts the progress bar."""
        self.progress.start()
        self.task_id = self.progress.add_task(description, total=total)
        self._started = True

    def stop(self):
        """Stops the progress bar."""
        if self._started:
            self.progress.stop()
            self._started = False

    def on_progress(self, current: int, total: int, message: str = "") -> None:
        """
        Updates the progress bar.

        Args:
            current: The current item count processed.
            total: The total number of items to process.
            message: Optional status message.
        """
        if not self._started:
            self.start(message or "Processing...", total)

        # Update description if message is provided
        if message:
            self.progress.update(self.task_id, description=message)

        self.progress.update(self.task_id, completed=current, total=total)

    def print_success(self, message: str):
        self.console.print(f"[bold green]SUCCESS:[/bold green] {message}")

    def print_error(self, message: str):
        self.console.print(f"[bold red]ERROR:[/bold red] {message}")

    def print_info(self, message: str):
        self.console.print(f"[blue]INFO:[/blue] {message}")

    def print_header(self, message: str):
        self.console.rule(f"[bold purple]{message}[/bold purple]")
