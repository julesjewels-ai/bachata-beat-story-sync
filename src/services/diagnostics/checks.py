"""
Concrete implementations of diagnostic checks.
"""
import shutil
import subprocess
import os
from typing import Optional, List

from src.core.models import DiagnosticResult, DiagnosticStatus


class FFmpegCheck:
    """Checks for FFmpeg and FFprobe availability."""

    def run(self) -> DiagnosticResult:
        """
        Verifies that ffmpeg and ffprobe are installed and accessible.
        """
        ffmpeg_path = shutil.which("ffmpeg")
        ffprobe_path = shutil.which("ffprobe")

        if not ffmpeg_path:
            return DiagnosticResult(
                check_name="FFmpeg Check",
                status=DiagnosticStatus.FAIL,
                message="FFmpeg binary not found",
                details="Please install FFmpeg and ensure it is in your PATH."
            )

        if not ffprobe_path:
            return DiagnosticResult(
                check_name="FFmpeg Check",
                status=DiagnosticStatus.WARN,
                message="FFprobe binary not found",
                details="FFprobe is recommended for accurate duration analysis."
            )

        # Check version
        try:
            result = subprocess.run(
                [ffmpeg_path, "-version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            version_line = result.stdout.split('\n')[0]
        except Exception as e:
            version_line = f"Unknown version ({e})"

        return DiagnosticResult(
            check_name="FFmpeg Check",
            status=DiagnosticStatus.PASS,
            message="FFmpeg found",
            details=f"Path: {ffmpeg_path}\nVersion: {version_line}"
        )


class DiskSpaceCheck:
    """Checks for available disk space in critical directories."""

    def __init__(self, min_gb: float = 1.0, paths: Optional[List[str]] = None):
        """
        Initialize the check.

        Args:
            min_gb: Minimum required free space in Gigabytes.
            paths: List of paths to check. Defaults to current directory.
        """
        self.min_bytes = int(min_gb * 1024 * 1024 * 1024)
        self.paths = paths or ["."]

    def run(self) -> DiagnosticResult:
        """
        Checks disk usage for configured paths.
        """
        details = []
        status = DiagnosticStatus.PASS

        for path in self.paths:
            # Resolve path to ensure it exists or check parent if file/missing
            check_path = path
            if not os.path.exists(check_path):
                check_path = os.path.dirname(os.path.abspath(check_path))
                if not os.path.exists(check_path):
                     # If parent doesn't exist, fall back to current dir
                     check_path = "."

            try:
                usage = shutil.disk_usage(check_path)
                free_gb = usage.free / (1024**3)

                if usage.free < self.min_bytes:
                    status = DiagnosticStatus.FAIL
                    details.append(f"{path}: LOW SPACE ({free_gb:.2f} GB free)")
                else:
                    details.append(f"{path}: OK ({free_gb:.2f} GB free)")
            except OSError as e:
                # If we fail to check, warn but don't fail hard unless critical
                if status != DiagnosticStatus.FAIL:
                    status = DiagnosticStatus.WARN
                details.append(f"{path}: Error checking space ({e})")

        return DiagnosticResult(
            check_name="Disk Space Check",
            status=status,
            message="Disk space check complete",
            details="\n".join(details)
        )
