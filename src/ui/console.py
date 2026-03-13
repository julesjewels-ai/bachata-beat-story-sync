"""
Console UI implementations using Rich.
"""

from __future__ import annotations

import sys
from contextlib import contextmanager
from typing import Generator

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskID, TextColumn
from rich.rule import Rule


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


# ------------------------------------------------------------------
# Pipeline Logger — Rich-based CLI UX
# ------------------------------------------------------------------

# Shared console instance for all Rich output.
_console = Console()


class PipelineLogger:
    """
    Professional CLI output for the pipeline orchestrator.

    Provides visual hierarchy (phase headers, success markers, error panels)
    and spinners for long-running operations.  Falls back to plain text
    when stdout is not a TTY (CI / piped output).

    Usage::

        log = PipelineLogger()
        log.phase("🎵 Mixing Audio")
        with log.status("Mixing 5 tracks…"):
            mix_tracks()
        log.success("Mix ready: _mixed_audio.wav")
    """

    def __init__(
        self,
        *,
        quiet: bool = False,
        console: Console | None = None,
    ) -> None:
        self.console = console or _console
        self.quiet = quiet
        self._interactive = sys.stdout.isatty()

    # --- Phase & step output ---

    def phase(self, title: str) -> None:
        """Print a bold section rule for a major pipeline phase."""
        if self.quiet:
            return
        self.console.print()  # breathing room
        self.console.print(Rule(f"[bold cyan]{title}[/bold cyan]", style="cyan"))

    def step(self, message: str) -> None:
        """Print an informational step message (ℹ prefix)."""
        if self.quiet:
            return
        self.console.print(f"[cyan]ℹ[/cyan] {message}")

    def detail(self, message: str) -> None:
        """Print dimmed technical metadata."""
        if self.quiet:
            return
        self.console.print(f"  [dim]{message}[/dim]")

    def success(self, message: str) -> None:
        """Print a green success message (✔ prefix)."""
        if self.quiet:
            return
        self.console.print(f"[green]✔[/green] {message}")

    def warn(self, message: str) -> None:
        """Print a yellow warning message (⚠ prefix)."""
        if self.quiet:
            return
        self.console.print(f"[yellow]⚠[/yellow] {message}")

    # --- Error panel ---

    def error(self, message: str, *, hint: str | None = None) -> None:
        """Print a red error panel with an optional fix hint."""
        body = f"[bold red]{message}[/bold red]"
        if hint:
            body += f"\n\n[dim]💡 {hint}[/dim]"
        self.console.print(Panel(body, title="Error", border_style="red"))

    # --- Status spinner (context manager) ---

    @contextmanager
    def status(self, message: str) -> Generator[None, None, None]:
        """
        Show a spinner while a blocking operation runs.

        Falls back to a simple print when not running in a TTY.
        """
        if self.quiet:
            yield
            return

        if self._interactive:
            with self.console.status(
                f"[bold blue]{message}[/bold blue]", spinner="dots"
            ):
                yield
        else:
            self.console.print(f"… {message}")
            yield

    # --- Final summary panel ---

    def summary(
        self,
        generated_files: list[str],
        elapsed_seconds: float,
    ) -> None:
        """Print a bordered summary panel at the end of the pipeline."""
        mins, secs = divmod(int(elapsed_seconds), 60)
        time_str = f"{mins}m {secs}s" if mins else f"{secs}s"

        lines = [
            f"[bold green]✨ Pipeline complete[/bold green]",
            f"[dim]Elapsed:[/dim] {time_str}",
            f"[dim]Files generated:[/dim] {len(generated_files)}",
            "",
        ]
        for path in generated_files:
            lines.append(f"  [cyan]{path}[/cyan]")

        self.console.print()
        self.console.print(Panel(
            "\n".join(lines),
            title="Summary",
            border_style="green",
            expand=False,
        ))

