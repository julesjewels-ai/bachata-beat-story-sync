"""
Unit tests for PipelineLogger (src/ui/console.py).

Tests verify that the correct Rich primitives are rendered.
They use a captured Rich Console to inspect output without TTY.
"""

from io import StringIO
from unittest.mock import patch

from rich.console import Console
from src.ui.console import PipelineLogger


def _make_logger(*, quiet: bool = False) -> tuple[PipelineLogger, Console, StringIO]:
    """Create a PipelineLogger backed by a string-captured Console."""
    buf = StringIO()
    console = Console(file=buf, force_terminal=True, width=80, highlight=False)
    log = PipelineLogger(quiet=quiet, console=console)
    return log, console, buf


class TestPhase:
    def test_phase_renders_rule(self):
        log, _, buf = _make_logger()
        log.phase("🎵 Mixing Audio")
        output = buf.getvalue()
        assert "Mixing Audio" in output

    def test_phase_quiet_suppressed(self):
        log, _, buf = _make_logger(quiet=True)
        log.phase("🎵 Mixing Audio")
        assert buf.getvalue() == ""


class TestSuccess:
    def test_success_has_checkmark(self):
        log, _, buf = _make_logger()
        log.success("Mix video saved")
        output = buf.getvalue()
        assert "✔" in output
        assert "Mix video saved" in output

    def test_success_quiet_suppressed(self):
        log, _, buf = _make_logger(quiet=True)
        log.success("Mix video saved")
        assert buf.getvalue() == ""


class TestStep:
    def test_step_has_info_prefix(self):
        log, _, buf = _make_logger()
        log.step("Found 5 tracks")
        output = buf.getvalue()
        assert "ℹ" in output
        assert "Found 5 tracks" in output


class TestDetail:
    def test_detail_message_present(self):
        log, _, buf = _make_logger()
        log.detail("BPM=128.0")
        output = buf.getvalue()
        assert "BPM=128.0" in output

    def test_detail_quiet_suppressed(self):
        log, _, buf = _make_logger(quiet=True)
        log.detail("BPM=128.0")
        assert buf.getvalue() == ""


class TestWarn:
    def test_warn_has_symbol(self):
        log, _, buf = _make_logger()
        log.warn("No B-roll found")
        output = buf.getvalue()
        assert "⚠" in output
        assert "No B-roll found" in output


class TestError:
    def test_error_renders_panel(self):
        log, _, buf = _make_logger()
        log.error("File not found")
        output = buf.getvalue()
        # Panel renders with border characters and the title
        assert "Error" in output
        assert "File not found" in output

    def test_error_includes_hint(self):
        log, _, buf = _make_logger()
        log.error("Permission denied", hint="Check file permissions")
        output = buf.getvalue()
        assert "Permission denied" in output
        assert "Check file permissions" in output

    def test_error_not_suppressed_in_quiet_mode(self):
        log, _, buf = _make_logger(quiet=True)
        log.error("Fatal error")
        output = buf.getvalue()
        assert "Fatal error" in output


class TestSummary:
    def test_summary_renders_panel(self):
        log, _, buf = _make_logger()
        log.summary(["output/mix.mp4", "output/track_01.mp4"], 125.0)
        output = buf.getvalue()
        assert "Summary" in output
        assert "Pipeline complete" in output
        assert "2m 5s" in output
        assert "output/mix.mp4" in output
        assert "2" in output  # file count

    def test_summary_short_time(self):
        log, _, buf = _make_logger()
        log.summary(["output/mix.mp4"], 42.0)
        output = buf.getvalue()
        assert "42s" in output


class TestStatus:
    @patch("src.ui.console.sys")
    def test_non_tty_falls_back_to_print(self, mock_sys):
        """When stdout is not a TTY, status should print instead of spin."""
        mock_sys.stdout.isatty.return_value = False
        buf = StringIO()
        console = Console(file=buf, force_terminal=True, width=80)
        log = PipelineLogger(console=console)
        # Force the _interactive flag since we mock after construction
        log._interactive = False

        with log.status("Working…"):
            pass

        output = buf.getvalue()
        assert "Working" in output

    def test_quiet_status_produces_no_output(self):
        log, _, buf = _make_logger(quiet=True)
        with log.status("Working…"):
            pass
        assert buf.getvalue() == ""
