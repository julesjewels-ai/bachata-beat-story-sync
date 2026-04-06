"""Typed session state wrapper for Streamlit application.

Provides a strongly-typed interface to st.session_state instead of using
magic string keys throughout the UI code.
"""

from __future__ import annotations

import queue

import streamlit as st

from src.workers.progress import ProgressTracker


class SessionState:
    """Typed wrapper around st.session_state.

    Replaces magic string keys with typed properties, enabling IDE autocomplete
    and preventing typos.

    Example:
        state = SessionState()
        state.is_running = True  # Type-safe, autocomplete works
        path = state.audio_path  # No string typos possible
    """

    def __init__(self) -> None:
        """Initialize state with defaults if not already present."""
        self._ensure_defaults()

    @staticmethod
    def _ensure_defaults() -> None:
        """Create session state keys with defaults if they don't exist."""
        defaults = {
            "running": False,
            "log_lines": [],
            "result_path": None,
            "error": None,
            "plan_report": None,
            "log_queue": queue.Queue(),
            "audio_path": "",
            "video_dir": "",
            "broll_dir": "",
            "output_path": "output_story.mp4",
            "progress_tracker": ProgressTracker(),
        }
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value

    # =========================================================================
    # Execution state
    # =========================================================================

    @property
    def is_running(self) -> bool:
        """Whether the pipeline is currently running."""
        return st.session_state.get("running", False)

    @is_running.setter
    def is_running(self, value: bool) -> None:
        """Set pipeline running state."""
        st.session_state["running"] = value

    # =========================================================================
    # Logging and progress
    # =========================================================================

    @property
    def log_lines(self) -> list[str]:
        """List of log messages to display to the user."""
        return st.session_state.get("log_lines", [])

    @log_lines.setter
    def log_lines(self, value: list[str]) -> None:
        """Set log messages."""
        st.session_state["log_lines"] = value

    def append_log(self, line: str) -> None:
        """Append a single log line."""
        st.session_state["log_lines"].append(line)

    @property
    def log_queue(self) -> queue.Queue:
        """Thread-safe queue for collecting logs from background worker."""
        return st.session_state.get("log_queue", queue.Queue())

    @log_queue.setter
    def log_queue(self, value: queue.Queue) -> None:
        """Set the log queue."""
        st.session_state["log_queue"] = value

    @property
    def progress_tracker(self) -> ProgressTracker:
        """Progress tracker for ETA estimation and stage updates."""
        return st.session_state.get("progress_tracker", ProgressTracker())

    @progress_tracker.setter
    def progress_tracker(self, value: ProgressTracker) -> None:
        """Set the progress tracker."""
        st.session_state["progress_tracker"] = value

    # =========================================================================
    # Results and errors
    # =========================================================================

    @property
    def result_path(self) -> str | None:
        """Path to the generated output video, or None if not ready."""
        return st.session_state.get("result_path")

    @result_path.setter
    def result_path(self, value: str | None) -> None:
        """Set the result path."""
        st.session_state["result_path"] = value

    @property
    def error(self) -> str | None:
        """Error message from pipeline execution, or None if successful."""
        return st.session_state.get("error")

    @error.setter
    def error(self, value: str | None) -> None:
        """Set the error message."""
        st.session_state["error"] = value

    @property
    def plan_report(self) -> str | None:
        """Dry-run plan report, or None if not generated."""
        return st.session_state.get("plan_report")

    @plan_report.setter
    def plan_report(self, value: str | None) -> None:
        """Set the plan report."""
        st.session_state["plan_report"] = value

    # =========================================================================
    # File paths (user inputs)
    # =========================================================================

    @property
    def audio_path(self) -> str:
        """Path to the audio file (user-selected or uploaded)."""
        return st.session_state.get("audio_path", "")

    @audio_path.setter
    def audio_path(self, value: str) -> None:
        """Set the audio file path."""
        st.session_state["audio_path"] = value

    @property
    def video_dir(self) -> str:
        """Path to the video clips directory."""
        return st.session_state.get("video_dir", "")

    @video_dir.setter
    def video_dir(self, value: str) -> None:
        """Set the video directory path."""
        st.session_state["video_dir"] = value

    @property
    def broll_dir(self) -> str:
        """Path to the B-roll directory (optional)."""
        return st.session_state.get("broll_dir", "")

    @broll_dir.setter
    def broll_dir(self, value: str) -> None:
        """Set the B-roll directory path."""
        st.session_state["broll_dir"] = value

    @property
    def output_path(self) -> str:
        """Path where the output video will be saved."""
        return st.session_state.get("output_path", "output_story.mp4")

    @output_path.setter
    def output_path(self, value: str) -> None:
        """Set the output file path."""
        st.session_state["output_path"] = value

    # =========================================================================
    # Batch operations
    # =========================================================================

    def reset_execution(self) -> None:
        """Reset execution state (run a new pipeline)."""
        self.is_running = True
        self.log_lines = []
        self.result_path = None
        self.error = None
        self.plan_report = None
        self.log_queue = queue.Queue()
        self.progress_tracker = ProgressTracker()

    def finish_with_error(self, error_message: str) -> None:
        """Mark execution as finished with an error."""
        self.is_running = False
        self.error = error_message

    def finish_with_result(self, result_path: str) -> None:
        """Mark execution as finished successfully."""
        self.is_running = False
        self.result_path = result_path
        self.error = None

    def clear_results(self) -> None:
        """Clear all results and error messages."""
        self.result_path = None
        self.error = None
        self.plan_report = None
        self.log_lines = []
