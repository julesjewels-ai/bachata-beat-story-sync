"""
Shared FFmpeg utility functions.

Single source of truth for subprocess FFmpeg invocation, timeout
handling, and error formatting used by both MontageGenerator and
AudioMixer.
"""

from __future__ import annotations

import logging
import platform
import subprocess

logger = logging.getLogger(__name__)

# Default timeout per FFmpeg subprocess call (seconds)
FFMPEG_TIMEOUT = 600


def _libx264_fallback_args() -> list[str]:
    """Return the software H.264 encoder arguments."""
    return [
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
    ]


def _with_libx264_fallback(cmd: list[str]) -> list[str] | None:
    """Swap a VideoToolbox encoder invocation for a libx264 fallback."""
    try:
        idx = cmd.index("h264_videotoolbox")
    except ValueError:
        return None

    start = idx - 1
    end = idx + 1
    while end < len(cmd) and cmd[end] in {"-b:v", "-pix_fmt"}:
        end += 2

    return [*cmd[:start], *_libx264_fallback_args(), *cmd[end:]]


def timeout_for_duration(duration_seconds: float) -> int:
    """
    Compute a reasonable FFmpeg timeout based on media duration.

    Uses max(FFMPEG_TIMEOUT, duration * 2) so short clips keep the
    standard 600 s floor while long mixes get proportional headroom.

    Args:
        duration_seconds: Length of the input media in seconds.

    Returns:
        Timeout value in seconds.
    """
    return max(FFMPEG_TIMEOUT, int(duration_seconds * 2))


def run_ffmpeg(
    cmd: list[str],
    stage_name: str,
    timeout_seconds: int | None = None,
) -> None:
    """
    Execute an FFmpeg command with timeout and error handling.

    Args:
        cmd: The FFmpeg command as a list of arguments.
        stage_name: Human-readable name for error messages.
        timeout_seconds: Optional override for the default timeout.

    Raises:
        RuntimeError: If FFmpeg exits with non-zero or times out.
    """
    effective_timeout = timeout_seconds or FFMPEG_TIMEOUT
    logger.debug(
        "FFmpeg [%s] (timeout=%ds): %s",
        stage_name,
        effective_timeout,
        " ".join(cmd),
    )

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=effective_timeout,
            shell=False,
        )  # nosec B603

        if result.returncode != 0:
            stderr_text = result.stderr or ""
            if "h264_videotoolbox" in cmd and "videotoolbox" in stderr_text.lower():
                fallback_cmd = _with_libx264_fallback(cmd)
                if fallback_cmd is not None:
                    logger.warning(
                        "FFmpeg [%s] failed with VideoToolbox; retrying with libx264.",
                        stage_name,
                    )
                    retry_result = subprocess.run(
                        fallback_cmd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=effective_timeout,
                        shell=False,
                    )  # nosec B603
                    if retry_result.returncode == 0:
                        return
                    stderr_text = retry_result.stderr or stderr_text

            stderr_tail = stderr_text[-500:] if stderr_text else ""
            raise RuntimeError(
                f"FFmpeg failed during {stage_name} "
                f"(exit code {result.returncode}): {stderr_tail}"
            )

    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"FFmpeg timed out during {stage_name} "
            f"(>{effective_timeout}s). The input file may be too large."
        ) from None


def get_audio_duration(path: str) -> float:
    """
    Probe the duration of an audio (or video) file via ffprobe.

    Returns:
        Duration in seconds, or 0.0 on failure.
    """
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "csv=p=0",
                path,
            ],
            capture_output=True,
            text=True,
            timeout=10,
            shell=False,
        )  # nosec B603
        return float(result.stdout.strip())
    except (ValueError, subprocess.TimeoutExpired, OSError):
        logger.warning("Could not probe duration for %s", path)
        return 0.0


def get_h264_encoder_args() -> list[str]:
    """
    Return the optimal H.264 encoder arguments for the current hardware.

    Leverages Apple Silicon VideoToolbox hardware acceleration if available,
    otherwise falls back to libx264 software encoding.

    Returns:
        List of FFmpeg command-line arguments.
    """
    is_mac = platform.system() == "Darwin"
    is_arm = platform.machine() == "arm64"

    if is_mac and is_arm:
        # Hardware acceleration for M1/M2/M3 chips
        return [
            "-c:v",
            "h264_videotoolbox",
            "-b:v",
            "8M",  # High quality target for 1080p
            "-pix_fmt",
            "yuv420p",  # Universal compatibility
        ]

    # Standard software encoding fallback
    return _libx264_fallback_args()
