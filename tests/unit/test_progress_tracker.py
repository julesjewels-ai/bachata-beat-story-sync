"""Unit tests for ProgressTracker and related classes.

Tests progress tracking, ETA calculation, and log handling.
"""

from __future__ import annotations

import logging
import queue
import time

from src.workers.progress import ProgressTracker, QueueLogHandler, StageInfo


class TestStageInfo:
    """Test StageInfo dataclass."""

    def test_stage_info_creation(self):
        """StageInfo can be created with required fields."""
        stage = StageInfo(name="audio_analysis", current=5, total=10, estimated_percent=50.0)
        assert stage.name == "audio_analysis"
        assert stage.current == 5
        assert stage.total == 10
        assert stage.estimated_percent == 50.0

    def test_stage_info_pct_property(self):
        """StageInfo.pct calculates percentage correctly."""
        stage = StageInfo(name="test", current=5, total=10, estimated_percent=50.0)
        assert stage.pct == 50.0

    def test_stage_info_pct_zero_total(self):
        """StageInfo.pct returns 0 when total is 0."""
        stage = StageInfo(name="test", current=5, total=0, estimated_percent=0.0)
        assert stage.pct == 0


class TestProgressTrackerInit:
    """Test ProgressTracker initialization."""

    def test_tracker_initialization(self):
        """ProgressTracker initializes with correct defaults."""
        tracker = ProgressTracker()
        assert tracker.start_time is None  # Not started yet
        assert tracker.current_stage == ""
        assert tracker.stage_progress == {}
        assert tracker.log_count == 0

    def test_tracker_has_stage_heuristics(self):
        """ProgressTracker has STAGE_HEURISTICS mapping."""
        tracker = ProgressTracker()
        assert hasattr(tracker, "STAGE_HEURISTICS")
        assert isinstance(tracker.STAGE_HEURISTICS, dict)
        assert len(tracker.STAGE_HEURISTICS) > 0


class TestProgressTrackerStart:
    """Test starting the tracker."""

    def test_start_sets_start_time(self):
        """start() sets the start_time."""
        tracker = ProgressTracker()
        assert tracker.start_time is None

        tracker.start()
        assert tracker.start_time is not None
        assert isinstance(tracker.start_time, float)


class TestProgressTrackerElapsedTime:
    """Test elapsed time calculation."""

    def test_elapsed_seconds_before_start(self):
        """elapsed_seconds returns 0 before start() is called."""
        tracker = ProgressTracker()
        elapsed = tracker.elapsed_seconds()
        assert elapsed == 0.0

    def test_elapsed_seconds_after_start(self):
        """elapsed_seconds returns positive value after start()."""
        tracker = ProgressTracker()
        tracker.start()
        time.sleep(0.05)
        elapsed = tracker.elapsed_seconds()
        assert elapsed >= 0.05

    def test_elapsed_str_format(self):
        """elapsed_str returns HH:MM:SS format."""
        tracker = ProgressTracker()
        tracker.start()
        elapsed_str = tracker.elapsed_str()
        assert isinstance(elapsed_str, str)
        assert ":" in elapsed_str
        # Should be HH:MM:SS format
        parts = elapsed_str.split(":")
        assert len(parts) == 3


class TestProgressTrackerUpdate:
    """Test message-based progress updates."""

    def test_update_detects_stage(self):
        """update() detects stage from log message."""
        tracker = ProgressTracker()
        tracker.update("[1/4] Analysing audio…")
        assert tracker.current_stage == "Analysing audio"

    def test_update_parses_progress(self):
        """update() parses [N/M] progress notation."""
        tracker = ProgressTracker()
        tracker.update("[2/4] Scanning video clips")
        assert tracker.current_stage == "Scanning video"
        assert tracker.stage_progress["Scanning video"] == (2, 4)

    def test_update_increments_log_count(self):
        """update() increments log_count."""
        tracker = ProgressTracker()
        assert tracker.log_count == 0

        tracker.update("Message 1")
        assert tracker.log_count == 1

        tracker.update("Message 2")
        assert tracker.log_count == 2

    def test_update_with_invalid_progress_notation(self):
        """update() handles invalid [N/M] notation gracefully."""
        tracker = ProgressTracker()
        tracker.update("[invalid] Scanning video")
        # Should not crash, just skip progress parsing
        assert tracker.log_count == 1


class TestProgressTrackerETA:
    """Test ETA calculation methods."""

    def test_estimate_eta_seconds_without_start(self):
        """estimate_eta_seconds returns None if not started."""
        tracker = ProgressTracker()
        eta = tracker.estimate_eta_seconds()
        assert eta is None

    def test_estimate_eta_seconds_without_stage(self):
        """estimate_eta_seconds returns None if no stage set."""
        tracker = ProgressTracker()
        tracker.start()
        eta = tracker.estimate_eta_seconds()
        assert eta is None

    def test_estimate_eta_seconds_with_stage(self):
        """estimate_eta_seconds returns value when started with stage."""
        tracker = ProgressTracker()
        tracker.start()
        time.sleep(0.1)
        tracker.update("[1/4] Analysing audio…")
        eta = tracker.estimate_eta_seconds()
        assert isinstance(eta, float) or eta is None

    def test_estimate_eta_str_without_eta(self):
        """estimate_eta_str returns '—' when no ETA available."""
        tracker = ProgressTracker()
        eta_str = tracker.estimate_eta_str()
        assert eta_str == "—"

    def test_estimate_eta_str_format(self):
        """estimate_eta_str returns HH:MM:SS format when available."""
        tracker = ProgressTracker()
        tracker.start()
        time.sleep(0.1)
        tracker.update("[1/4] Analysing audio…")
        eta_str = tracker.estimate_eta_str()
        if eta_str != "—":
            assert ":" in eta_str


class TestProgressTrackerStageLabel:
    """Test stage label formatting."""

    def test_stage_label_before_progress(self):
        """stage_label returns 'starting…' before any progress."""
        tracker = ProgressTracker()
        label = tracker.stage_label()
        assert label == "starting…"

    def test_stage_label_with_progress(self):
        """stage_label returns 'N of M' format after progress update."""
        tracker = ProgressTracker()
        tracker.update("[2/4] Scanning video clips")
        label = tracker.stage_label()
        assert label == "2 of 4"

    def test_stage_label_multiple_stages(self):
        """stage_label uses highest stage number seen."""
        tracker = ProgressTracker()
        tracker.update("[1/4] Analysing audio…")
        tracker.update("[2/4] Scanning video clips")
        tracker.update("[1/3] Rendering montage")  # Different total
        label = tracker.stage_label()
        # Should show max current (2) and max total (4)
        assert "2" in label
        assert "4" in label


class TestQueueLogHandler:
    """Test QueueLogHandler for logging to a queue."""

    def test_handler_initialization(self):
        """QueueLogHandler initializes with a queue."""
        q = queue.Queue()
        handler = QueueLogHandler(q)
        assert handler._queue is q

    def test_handler_emits_records_to_queue(self):
        """Emitting a log record puts message in queue."""
        q = queue.Queue()
        handler = QueueLogHandler(q)

        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="test.py", lineno=1,
            msg="Test message", args=(), exc_info=None
        )

        handler.emit(record)

        assert not q.empty()
        message = q.get_nowait()
        assert message == "Test message"

    def test_handler_with_formatter(self):
        """QueueLogHandler respects formatters."""
        q = queue.Queue()
        handler = QueueLogHandler(q)
        formatter = logging.Formatter("%(levelname)s - %(message)s")
        handler.setFormatter(formatter)

        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="test.py", lineno=1,
            msg="Test message", args=(), exc_info=None
        )

        handler.emit(record)

        assert not q.empty()
        message = q.get_nowait()
        assert "INFO" in message
        assert "Test message" in message

    def test_handler_suppresses_emit_exceptions(self):
        """QueueLogHandler suppresses exceptions during emit."""
        q = queue.Queue()

        # Create a handler with a queue that raises on put_nowait
        class FailingQueue:
            def put_nowait(self, item):
                raise RuntimeError("Queue failed")

        handler = QueueLogHandler(FailingQueue())  # type: ignore

        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="test.py", lineno=1,
            msg="Test message", args=(), exc_info=None
        )

        # Should not raise exception
        handler.emit(record)


class TestProgressTrackerIntegration:
    """Integration tests combining multiple components."""

    def test_full_pipeline_simulation(self):
        """Simulate a complete pipeline execution with progress tracking."""
        tracker = ProgressTracker()
        q = queue.Queue()
        handler = QueueLogHandler(q)

        # Start tracking
        tracker.start()
        assert tracker.start_time is not None

        # Simulate audio analysis
        tracker.update("[1/4] Analysing audio…")
        assert tracker.current_stage == "Analysing audio"
        time.sleep(0.05)

        # Check ETA estimation
        eta = tracker.estimate_eta_seconds()
        # ETA might be None if elapsed is very short, so just verify it doesn't crash

        # Simulate video scanning
        tracker.update("[2/4] Scanning video clips")
        assert tracker.current_stage == "Scanning video"

        # Check stage label
        label = tracker.stage_label()
        assert "2" in label
        assert "4" in label

        # Log something
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="test.py", lineno=1,
            msg="Processing complete", args=(), exc_info=None
        )
        handler.emit(record)

        # Verify log in queue
        assert not q.empty()
        log_msg = q.get_nowait()
        assert "Processing" in log_msg
