"""
Shared FFmpeg utility functions.

Single source of truth for subprocess FFmpeg invocation, timeout
handling, and error formatting used by both MontageGenerator and
AudioMixer.
"""

import logging
import subprocess

logger = logging.getLogger(__name__)

# Timeout per FFmpeg subprocess call (seconds)
FFMPEG_TIMEOUT = 600


def run_ffmpeg(cmd: list[str], stage_name: str) -> None:
    """
    Execute an FFmpeg command with timeout and error handling.

    Args:
        cmd: The FFmpeg command as a list of arguments.
        stage_name: Human-readable name for error messages.

    Raises:
        RuntimeError: If FFmpeg exits with non-zero or times out.
    """
    logger.debug("FFmpeg [%s]: %s", stage_name, " ".join(cmd))

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=FFMPEG_TIMEOUT,
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
            f"(>{FFMPEG_TIMEOUT}s). The input file may be too large."
        )
