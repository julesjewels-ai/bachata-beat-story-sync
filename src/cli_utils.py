"""
Shared CLI utilities for Bachata Beat-Story Sync entry points.

Houses functions shared by main.py, pipeline.py, and shorts_maker.py
so they don't drift out of sync.
"""

from __future__ import annotations

import argparse
import logging
import os
import random
import uuid

logger = logging.getLogger(__name__)


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


def add_visual_args(parser: argparse.ArgumentParser) -> None:
    """Register the visual/audio style arguments shared by all entry points.

    Adds: --video-style, --audio-overlay, --audio-overlay-opacity,
    --audio-overlay-position, --broll-interval, --broll-variance.

    Args:
        parser: The ArgumentParser to add arguments to.
    """
    parser.add_argument(
        "--video-style",
        type=str,
        default=None,
        choices=["none", "bw", "vintage", "warm", "cool", "golden"],
        help="Color grading style: none, bw, vintage, warm, cool, golden",
    )
    parser.add_argument(
        "--audio-overlay",
        type=str,
        default=None,
        choices=["none", "waveform", "bars"],
        help="Music-synced visualizer pattern: none, waveform, bars",
    )
    parser.add_argument(
        "--audio-overlay-opacity",
        type=float,
        default=None,
        help="Opacity of the audio visualizer block (0.0 to 1.0)",
    )
    parser.add_argument(
        "--audio-overlay-position",
        type=str,
        default=None,
        choices=["left", "center", "right"],
        help="Position of the audio overlay: left, center, right (default: right)",
    )
    parser.add_argument(
        "--broll-interval",
        type=float,
        default=None,
        help="Target interval between B-roll clips in seconds (default: 13.5)",
    )
    parser.add_argument(
        "--broll-variance",
        type=float,
        default=None,
        help="Allowed variance in B-roll intervals, ± seconds (default: 1.5)",
    )


def add_shorts_args(parser: argparse.ArgumentParser) -> None:
    """Register the shorts-specific arguments.

    Adds: --dynamic-flow, --human-touch, --cliffhanger,
    --smart-start / --no-smart-start.

    Args:
        parser: The ArgumentParser to add arguments to.
    """
    parser.add_argument(
        "--dynamic-flow",
        action="store_true",
        help="Accelerate pacing (shorter clips) towards the end",
    )
    parser.add_argument(
        "--human-touch",
        action="store_true",
        help="Apply small random variances to speed ramps",
    )
    parser.add_argument(
        "--cliffhanger",
        action="store_true",
        help="End abruptly for a cliffhanger effect",
    )
    parser.add_argument(
        "--smart-start",
        action="store_true",
        default=True,
        help="Use audio hook detection for smart start selection (default: on)",
    )
    parser.add_argument(
        "--no-smart-start",
        action="store_false",
        dest="smart_start",
        help="Disable smart start — all shorts start from beat 0",
    )


# ------------------------------------------------------------------
# Shared shorts-generation loop
# ------------------------------------------------------------------


def generate_shorts_batch(
    engine,
    audio_meta,
    clips: list,
    audio_path: str,
    output_dir: str,
    count: int,
    min_dur: float,
    max_dur: float,
    pacing_kwargs: dict,
    *,
    smart_start: bool = True,
    dynamic_flow: bool = False,
    human_touch: bool = False,
    cliffhanger: bool = False,
) -> list[str]:
    """Generate *count* shorts into *output_dir*, returning output paths.

    This is the single source of truth for the shorts-generation loop,
    called by both ``pipeline.py`` and ``shorts_maker.py``.

    Args:
        engine: A ``BachataSyncEngine`` instance.
        audio_meta: ``AudioAnalysisResult`` for the audio track.
        clips: Pre-scanned list of ``VideoAnalysisResult`` clips.
        audio_path: Path to the audio file on disk.
        output_dir: Directory to write shorts into (created if absent).
        count: Number of shorts to generate.
        min_dur: Minimum target duration in seconds.
        max_dur: Maximum target duration in seconds.
        pacing_kwargs: Base pacing overrides (from ``build_pacing_kwargs``).
        smart_start: Use audio-hook detection for varied start points.
        dynamic_flow: Accelerate pacing towards the end of each short.
        human_touch: Apply small random variances to speed ramps.
        cliffhanger: End abruptly for a cliffhanger effect.

    Returns:
        List of file paths for the generated shorts.
    """
    # Lazy imports to avoid circular dependencies
    from src.core.audio_analyzer import find_audio_hooks  # noqa: WPS433
    from src.core.models import PacingConfig  # noqa: WPS433
    from src.ui.console import RichProgressObserver  # noqa: WPS433

    os.makedirs(output_dir, exist_ok=True)
    generated: list[str] = []

    # FEAT-019: Find smart-start hooks for variety
    if smart_start:
        target_dur = (min_dur + max_dur) / 2.0
        hooks = find_audio_hooks(audio_meta, target_dur, count)
    else:
        hooks = [0.0] * count

    for i in range(count):
        target_duration = random.uniform(min_dur, max_dur)
        run_seed = str(uuid.uuid4())
        hook_offset = hooks[i] if i < len(hooks) else 0.0

        shorts_kwargs: dict = {
            **pacing_kwargs,
            "is_shorts": True,
            "seed": run_seed,
            "max_duration_seconds": target_duration,
            "audio_start_offset": hook_offset,
            "accelerate_pacing": dynamic_flow,
            "randomize_speed_ramps": human_touch,
            "abrupt_ending": cliffhanger,
        }
        # Remove full-video-only keys that conflict with shorts
        shorts_kwargs.pop("max_clips", None)

        pacing = PacingConfig(**shorts_kwargs)
        out_path = os.path.join(output_dir, f"short_{i + 1:03d}.mp4")

        logger.info(
            "Short %d/%d (%.0fs, hook@%.1fs)",
            i + 1, count, target_duration, hook_offset,
        )
        with RichProgressObserver() as obs:
            result = engine.generate_story(
                audio_meta,
                clips,
                out_path,
                audio_path=audio_path,
                observer=obs,
                pacing=pacing,
            )
        generated.append(result)

    return generated
