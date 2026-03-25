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


def detect_broll_dir(
    video_dir: str, explicit_broll_dir: str | None = None
) -> str | None:
    """Auto-detect B-roll subfolder inside *video_dir*.

    If *explicit_broll_dir* is provided it is returned unchanged.
    Otherwise checks for a ``broll/`` subdirectory inside *video_dir*.

    Args:
        video_dir: Root directory of the main video clips.
        explicit_broll_dir: Optional explicit override from the CLI.

    Returns:
        Path to the B-roll directory, or ``None`` if not found.
    """
    if explicit_broll_dir:
        return explicit_broll_dir
    auto = os.path.join(video_dir, "broll")
    if os.path.isdir(auto):
        logger.info("Auto-detected B-roll folder: %s", auto)
        return auto
    return None


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
        test_mode, genre, video_style, audio_overlay, audio_overlay_opacity,
        audio_overlay_position, audio_overlay_padding, broll_interval,
        broll_variance, explain, intro_effect, intro_effect_duration,
        dry_run, pacing_drift_zoom, pacing_crop_tighten,
        pacing_saturation_pulse.

    All padding values are integers (pixels ≥ 0). All opacity values are
    floats clamped to 0.0–1.0 by the renderer. Unrecognised/missing
    attributes are silently ignored via ``getattr`` with a safe default.

    Args:
        args: Parsed argparse.Namespace from any entry point.

    Returns:
        Dict suitable for splatting into ``PacingConfig(**kwargs)``.
    """
    kwargs: dict = {}

    if getattr(args, "test_mode", False):
        kwargs["max_clips"] = 4
        kwargs["max_duration_seconds"] = 10.0

    if getattr(args, "genre", None):
        kwargs["genre"] = args.genre
    if getattr(args, "video_style", None):
        kwargs["video_style"] = args.video_style
    if getattr(args, "audio_overlay", None):
        kwargs["audio_overlay"] = args.audio_overlay
    if getattr(args, "audio_overlay_opacity", None) is not None:
        kwargs["audio_overlay_opacity"] = args.audio_overlay_opacity
    if getattr(args, "audio_overlay_position", None):
        kwargs["audio_overlay_position"] = args.audio_overlay_position
    if getattr(args, "audio_overlay_padding", None) is not None:
        kwargs["audio_overlay_padding"] = args.audio_overlay_padding
    if getattr(args, "broll_interval", None) is not None:
        kwargs["broll_interval_seconds"] = args.broll_interval
    if getattr(args, "broll_variance", None) is not None:
        kwargs["broll_interval_variance"] = args.broll_variance
    if getattr(args, "explain", False):
        kwargs["explain"] = True
    if getattr(args, "intro_effect", None):
        kwargs["intro_effect"] = args.intro_effect
    if getattr(args, "intro_effect_duration", None) is not None:
        kwargs["intro_effect_duration"] = args.intro_effect_duration
    if getattr(args, "dry_run", False):
        kwargs["dry_run"] = True
    if getattr(args, "pacing_drift_zoom", False):
        kwargs["pacing_drift_zoom"] = True
    if getattr(args, "pacing_crop_tighten", False):
        kwargs["pacing_crop_tighten"] = True
    if getattr(args, "pacing_saturation_pulse", False):
        kwargs["pacing_saturation_pulse"] = True

    return kwargs


def add_visual_args(parser: argparse.ArgumentParser) -> None:
    """Register the visual/audio style arguments shared by all entry points.

    Adds: --video-style, --audio-overlay, --audio-overlay-opacity,
    --audio-overlay-position, --audio-overlay-padding, --broll-interval,
    --broll-variance.

    Args:
        parser: The ArgumentParser to add arguments to.
    """
    # Genre Preset (FEAT-027) — choices derived from registry
    from src.core.genre_presets import list_genres  # noqa: WPS433

    parser.add_argument(
        "--genre",
        type=str,
        default=None,
        choices=list_genres(),
        help="Genre preset: " + ", ".join(list_genres()),
    )
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
        "--audio-overlay-padding",
        type=int,
        default=None,
        help="Distance in pixels from the screen edge for the audio overlay (default: 10)",
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
    parser.add_argument(
        "--explain",
        action="store_true",
        default=False,
        help="Emit a Markdown decision log alongside the output video",
    )

    # Intro Visual Effects (FEAT-022) — choices derived from registry
    from src.core.ffmpeg_renderer import INTRO_EFFECTS  # noqa: WPS433

    parser.add_argument(
        "--intro-effect",
        type=str,
        default=None,
        choices=["none", *sorted(INTRO_EFFECTS.keys())],
        help="Visual effect on the first clip: none, "
        + ", ".join(sorted(INTRO_EFFECTS.keys())),
    )
    parser.add_argument(
        "--intro-effect-duration",
        type=float,
        default=None,
        help="Duration of the intro effect in seconds (default: 1.5)",
    )

    # Dry-Run Plan Mode (FEAT-026)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Preview the segment plan without rendering video",
    )
    parser.add_argument(
        "--dry-run-output",
        type=str,
        default=None,
        help="Write dry-run plan to a file instead of stdout",
    )

    # Pacing Visual Effects (FEAT-023)
    parser.add_argument(
        "--pacing-drift-zoom",
        action="store_true",
        default=False,
        help="Slow 100→105% Ken Burns zoom drift on every segment",
    )
    parser.add_argument(
        "--pacing-crop-tighten",
        action="store_true",
        default=False,
        help="Zoom in over first 10s of each segment (caps at 105%); "
        "mutually exclusive with --pacing-drift-zoom (both use zoompan)",
    )
    parser.add_argument(
        "--pacing-saturation-pulse",
        action="store_true",
        default=False,
        help="Brief saturation surge on each detected beat",
    )

    # Structured JSON Output (FEAT-028)
    parser.add_argument(
        "--output-json",
        type=str,
        default=None,
        metavar="PATH",
        help="Emit structured JSON output to a file or '-' for stdout",
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
# Shared audio analysis helpers
# ------------------------------------------------------------------


def analyze_audio(audio_path: str) -> tuple:
    """Resolve *audio_path* (file or folder) and run beat analysis.

    Handles the full bootstrap sequence shared by ``main.py`` and
    ``shorts_maker.py``: resolve via ``resolve_audio_path``, construct
    an ``AudioAnalysisInput``, run ``AudioAnalyzer.analyze()``, and
    log the key metrics.

    Args:
        audio_path: Path to an audio file **or** a folder of tracks
            (which will be mixed automatically).

    Returns:
        ``(resolved_path, audio_meta)`` where *resolved_path* is the
        concrete file path and *audio_meta* is the
        ``AudioAnalysisResult``.
    """
    # Lazy imports to avoid circular dependencies
    from src.core.audio_analyzer import (  # noqa: WPS433
        AudioAnalysisInput,
        AudioAnalyzer,
    )
    from src.core.audio_mixer import resolve_audio_path  # noqa: WPS433
    from src.ui.console import RichProgressObserver  # noqa: WPS433

    with RichProgressObserver() as obs:
        resolved = resolve_audio_path(audio_path, observer=obs)

    logger.info("Analyzing audio track: %s", resolved)
    audio_input = AudioAnalysisInput(file_path=resolved)
    audio_meta = AudioAnalyzer().analyze(audio_input)
    logger.info(
        "Detected BPM: %s | Emotional Peaks: %d",
        audio_meta.bpm,
        len(audio_meta.peaks),
    )
    return resolved, audio_meta


def strip_thumbnails(clips: list) -> list:
    """Return a copy of *clips* with ``thumbnail_data`` set to ``None``.

    This frees memory from decoded thumbnail images that are only
    needed for the preview UI, not for video generation.

    Args:
        clips: List of ``VideoAnalysisResult`` objects.

    Returns:
        New list with thumbnail data cleared on each clip.
    """
    return [clip.model_copy(update={"thumbnail_data": None}) for clip in clips]


# ------------------------------------------------------------------
# Shared dry-run handler
# ------------------------------------------------------------------


def run_dry_run_handler(
    engine,
    audio_meta,
    clips: list,
    pacing_kwargs: dict,
    *,
    dry_run_output: str | None,
    output_json: str | None,
    pacing_is_shorts: bool = False,
    report_prefix: str = "",
) -> str:
    """Plan-only mode: emit the segment plan report without rendering video.

    Extracted from ``shorts_maker.py`` and ``pipeline.py`` to keep the
    dry-run + JSON-output logic in one place.

    Args:
        engine: A ``BachataSyncEngine`` instance.
        audio_meta: ``AudioAnalysisResult`` for the audio track.
        clips: Pre-stripped list of ``VideoAnalysisResult`` clips.
        pacing_kwargs: Base pacing overrides (from ``build_pacing_kwargs``).
        dry_run_output: Path to write the plan report, or ``None`` for stdout.
        output_json: Path to write JSON output (or ``'-'`` for stdout), or ``None``.
        pacing_is_shorts: When ``True``, sets ``is_shorts=True`` on PacingConfig.
        report_prefix: Optional heading prepended to the plan text (e.g. ``"=== Mix ===\\n"``).

    Returns:
        The formatted plan report string.
    """
    from src.core.models import PacingConfig  # noqa: WPS433
    from src.services.plan_report import format_plan_report, write_plan_report  # noqa: WPS433

    pacing = PacingConfig(**{**pacing_kwargs, "is_shorts": pacing_is_shorts})
    segments = engine.plan_story(audio_meta, clips, pacing=pacing)
    report = format_plan_report(audio_meta, segments, clips, pacing)
    full_report = (report_prefix + report) if report_prefix else report
    write_plan_report(full_report, dry_run_output)

    if output_json:
        from src.services.json_output import build_json_output, write_json_output  # noqa: WPS433

        data = build_json_output(audio_meta, clips, segments, pacing)
        write_json_output(data, output_json)

    return full_report


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
