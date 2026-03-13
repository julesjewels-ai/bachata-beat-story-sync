"""
Shared CLI utilities for Bachata Beat-Story Sync entry points.

Houses functions shared by main.py, pipeline.py, and shorts_maker.py
so they don't drift out of sync.
"""

import argparse


def parse_duration(duration_str: str) -> tuple[float, float]:
    """Parse a duration string like '60' or '10-15' into (min, max) floats.

    Args:
        duration_str: A string containing a single number or a 'min-max' range.

    Returns:
        Tuple of (min_duration, max_duration) in seconds.

    Raises:
        argparse.ArgumentTypeError: If the string is not a valid number or range.
    """
    if "-" in duration_str:
        parts = duration_str.split("-")
        if len(parts) == 2:
            try:
                min_d = float(parts[0].strip())
                max_d = float(parts[1].strip())
                return min_d, max_d
            except ValueError:
                pass
    try:
        val = float(duration_str.strip())
        return val, val
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid duration format: '{duration_str}'."
            " Use '60' or '10-15'."
        ) from None


def build_pacing_kwargs(args: argparse.Namespace) -> dict:
    """Build a dict of PacingConfig overrides from parsed CLI arguments.

    Inspects the common visual/style flags present on `args` and returns
    only the keys whose values are non-None.  Caller may merge additional
    entry-point-specific keys (e.g. ``is_shorts``, ``max_clips``) before
    constructing a ``PacingConfig``.

    Supported attributes on *args* (all optional):
        test_mode, video_style, audio_overlay, audio_overlay_opacity,
        audio_overlay_position, broll_interval, broll_variance.

    Args:
        args: Parsed argparse.Namespace from any entry point.

    Returns:
        Dict suitable for splatting into ``PacingConfig(**kwargs)``.
    """
    kwargs: dict = {}

    if getattr(args, "test_mode", False):
        kwargs["max_clips"] = 4
        kwargs["max_duration_seconds"] = 10.0

    if getattr(args, "video_style", None):
        kwargs["video_style"] = args.video_style
    if getattr(args, "audio_overlay", None):
        kwargs["audio_overlay"] = args.audio_overlay
    if getattr(args, "audio_overlay_opacity", None) is not None:
        kwargs["audio_overlay_opacity"] = args.audio_overlay_opacity
    if getattr(args, "audio_overlay_position", None):
        kwargs["audio_overlay_position"] = args.audio_overlay_position
    if getattr(args, "broll_interval", None) is not None:
        kwargs["broll_interval_seconds"] = args.broll_interval
    if getattr(args, "broll_variance", None) is not None:
        kwargs["broll_interval_variance"] = args.broll_variance

    return kwargs
