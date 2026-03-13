"""
Shared FFmpeg utility functions.

Single source of truth for subprocess FFmpeg invocation, timeout
handling, and error formatting used by both MontageGenerator and
AudioMixer.
"""

import logging
import subprocess

logger = logging.getLogger(__name__)

# Default timeout per FFmpeg subprocess call (seconds)
FFMPEG_TIMEOUT = 600


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
            stderr_tail = result.stderr[-500:] if result.stderr else ""
            raise RuntimeError(
                f"FFmpeg failed during {stage_name} "
                f"(exit code {result.returncode}): {stderr_tail}"
            )

    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"FFmpeg timed out during {stage_name} "
            f"(>{effective_timeout}s). The input file may be too large."
        ) from None
