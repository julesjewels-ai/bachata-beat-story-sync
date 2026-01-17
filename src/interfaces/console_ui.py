"""
Console UI implementation using Rich.
"""
from typing import Dict, Any, Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint

class ConsoleUI:
    """
    Handles user interaction via the console using Rich.
    """
    def __init__(self):
        self.console = Console()

    def display_welcome(self):
        """Displays the welcome message."""
        self.console.print(Panel.fit(
            "[bold magenta]Bachata Beat-Story Sync[/bold magenta]\n"
            "[cyan]Automated Video Editor[/cyan]",
            border_style="magenta"
        ))

    def show_error(self, message: str):
        """Displays an error message."""
        self.console.print(f"[bold red]Error:[/bold red] {message}")

    def show_success(self, message: str):
        """Displays a success message."""
        self.console.print(f"[bold green]Success:[/bold green] {message}")

    def display_results(self, results: Dict[str, Any]):
        """Displays simulation results in a table."""
        table = Table(title="Simulation Results")

        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", style="magenta")

        for key, value in results.items():
            table.add_row(key.replace("_", " ").title(), str(value))

        self.console.print(table)

    class ProgressContext:
        """
        Context manager for handling progress bars.
        """
        def __init__(self, console: Console):
            self.console = console
            self.progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=self.console
            )
            self.task_id = None

        def __enter__(self):
            self.progress.start()
            self.task_id = self.progress.add_task("Starting...", total=100)
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.progress.stop()

        def update(self, completed: float, description: str):
            """Updates the progress bar."""
            if self.task_id is not None:
                self.progress.update(self.task_id, completed=completed, description=description)

    def create_progress_tracker(self):
        """Returns a progress tracker context manager."""
        return self.ProgressContext(self.console)
