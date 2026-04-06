"""Progress tracking and logging for background pipeline execution.

This module provides utilities to track pipeline progress, estimate ETA,
and collect logs from background threads into a central queue.
"""

from __future__ import annotations

import logging
import queue
import time
from dataclasses import dataclass


@dataclass
class StageInfo:
    """Stage progress information."""

    name: str
    current: int
    total: int
    estimated_percent: float

    @property
    def pct(self) -> float:
        """Return percentage for this stage."""
        return (self.current / self.total * 100) if self.total > 0 else 0


class ProgressTracker:
    """Tracks pipeline progress, stage, elapsed time, and estimates ETA."""

    # Stage duration heuristics (as % of total runtime)
    STAGE_HEURISTICS = {
        "Analysing audio": 10,
        "Scanning video": 10,
        "Configuring pacing": 5,
        "Planning segment": 5,
        "Rendering montage": 65,
        "Generating Excel": 5,
    }

    def __init__(self) -> None:
        self.start_time: float | None = None
        self.current_stage: str = ""
        # stage -> (current, total)
        self.stage_progress: dict[str, tuple[int, int]] = {}
        self.log_count: int = 0

    def start(self) -> None:
        """Mark the start of processing."""
        self.start_time = time.time()

    def update(self, message: str) -> None:
        """Update progress based on log message."""
        self.log_count += 1

        # Extract stage name from log message (e.g., "[1/4] Analysing audio…")
        for stage_key in self.STAGE_HEURISTICS:
            if stage_key in message:
                self.current_stage = stage_key
                break

        # Parse "[N/M]" progress
        if "[" in message and "/" in message:
            try:
                bracket = message[message.index("[") : message.index("]") + 1]
                parts = bracket.strip("[]").split("/")
                current, total = int(parts[0]), int(parts[1])
                self.stage_progress[self.current_stage] = (current, total)
            except (ValueError, IndexError):
                pass

    def elapsed_seconds(self) -> float:
        """Return elapsed time in seconds."""
        if self.start_time is None:
            return 0.0
        return time.time() - self.start_time

    def elapsed_str(self) -> str:
        """Return elapsed time as HH:MM:SS."""
        seconds = int(self.elapsed_seconds())
        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def estimate_eta_seconds(self) -> float | None:
        """Estimate remaining time based on elapsed time and stage heuristics."""
        if self.start_time is None or not self.current_stage:
            return None

        elapsed = self.elapsed_seconds()
        if elapsed < 1:
            return None

        # Find estimated total based on current stage
        current_heuristic = self.STAGE_HEURISTICS.get(self.current_stage, 50)
        estimated_total = elapsed / (current_heuristic / 100.0)
        estimated_remaining = estimated_total - elapsed
        return max(0, estimated_remaining)

    def estimate_eta_str(self) -> str:
        """Return estimated remaining time as HH:MM:SS or '?'."""
        eta = self.estimate_eta_seconds()
        if eta is None:
            return "—"
        seconds = int(eta)
        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def stage_label(self) -> str:
        """Return a readable stage label (e.g., '2 of 4')."""
        if not self.stage_progress:
            return "starting…"
        # Get the highest stage number seen
        max_current = max((c for c, _ in self.stage_progress.values()), default=0)
        max_total = max((t for _, t in self.stage_progress.values()), default=0)
        return f"{max_current} of {max_total}"


class QueueLogHandler(logging.Handler):
    """Logging handler that pushes formatted records onto a queue."""

    def __init__(self, log_queue: queue.Queue) -> None:
        super().__init__()
        self._queue = log_queue

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._queue.put_nowait(self.format(record))
        except Exception:  # noqa: BLE001
            pass


class QueueProgressObserver:
    """Progress observer that pushes status updates to a log queue."""

    def __init__(self, log_queue: queue.Queue) -> None:
        self._queue = log_queue

    def on_progress(self, current: int, total: int, message: str = "") -> None:
        """Pushes a progress message to the queue."""
        percent = (current / total * 100) if total > 0 else 0
        formatted = f"PROGRESS: {message} ({percent:.0f}%)"
        self._queue.put(formatted)
