"""
Integration tests for the System Diagnostics Service.
"""
import pytest
from unittest.mock import MagicMock, patch
from src.core.models import DiagnosticStatus, DiagnosticResult
from src.services.diagnostics import SystemDiagnosticManager, FFmpegCheck, DiskSpaceCheck


def test_diagnostics_manager_workflow():
    """
    Verifies that the manager can register checks and aggregate results correctly.
    """
    manager = SystemDiagnosticManager()

    # Mock checks to avoid system dependency in this test
    mock_check_pass = MagicMock()
    mock_check_pass.run.return_value = DiagnosticResult(
        check_name="Mock Pass",
        status=DiagnosticStatus.PASS,
        message="All good"
    )

    mock_check_fail = MagicMock()
    mock_check_fail.run.return_value = DiagnosticResult(
        check_name="Mock Fail",
        status=DiagnosticStatus.FAIL,
        message="Oh no"
    )

    manager.register_check(mock_check_pass)
    manager.register_check(mock_check_fail)

    results = manager.run_diagnostics()

    assert len(results) == 2
    assert results[0].status == DiagnosticStatus.PASS
    assert results[1].status == DiagnosticStatus.FAIL


@patch("shutil.which")
@patch("subprocess.run")
def test_ffmpeg_check_integration(mock_subprocess, mock_which):
    """
    Verifies FFmpegCheck integration with mocked system calls.
    """
    # Simulate FFmpeg present
    mock_which.side_effect = lambda x: "/usr/bin/" + x if x in ["ffmpeg", "ffprobe"] else None
    mock_subprocess.return_value.stdout = "ffmpeg version 4.4.2"

    check = FFmpegCheck()
    result = check.run()

    assert result.status == DiagnosticStatus.PASS
    assert "FFmpeg found" in result.message


@patch("shutil.disk_usage")
def test_disk_space_check_integration(mock_usage):
    """
    Verifies DiskSpaceCheck integration.
    """
    # Simulate low space (0.5 GB free)
    mock_usage.return_value.free = 0.5 * 1024**3
    mock_usage.return_value.total = 100 * 1024**3
    mock_usage.return_value.used = 99.5 * 1024**3

    check = DiskSpaceCheck(min_gb=1.0)
    result = check.run()

    assert result.status == DiagnosticStatus.FAIL
    assert "LOW SPACE" in result.details
