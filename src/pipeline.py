"""
Full Pipeline Orchestrator — FEAT-014 / FEAT-015 / FEAT-016 / FEAT-018.

Single command to:
  1. Mix a folder of audio tracks into one combined WAV.
  2. Generate a horizontal music video for the mix.
  3. Generate a horizontal music video for each individual track.
  4. Generate N YouTube Shorts for each individual track.

FEAT-018: Professional Rich-based CLI output with phase headers,
spinners, success markers, error panels, and a structured summary.
"""

import argparse
import logging
import os
import subprocess
import sys
import time

from pydantic import ValidationError

from src.cli_utils import (
    add_shorts_args,
    add_visual_args,
    build_pacing_kwargs,
    detect_broll_dir,
    generate_shorts_batch,
    parse_duration,
    run_dry_run_handler,
    strip_thumbnails,
)
from src.core.app import BachataSyncEngine
from src.core.audio_analyzer import AudioAnalysisInput, AudioAnalyzer
from src.core.audio_mixer import (
    SUPPORTED_AUDIO_EXTENSIONS,
    resolve_audio_path,
)
from src.core.models import PacingConfig
from src.ui.console import PipelineLogger, RichProgressObserver

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _discover_audio_files(folder_path: str) -> list[str]:
    """Return sorted list of audio files in *folder_path*, excluding cache."""
    files = []
    for name in os.listdir(folder_path):
        if name == "_mixed_audio.wav":
            continue
        if os.path.splitext(name)[1].lower() in SUPPORTED_AUDIO_EXTENSIONS:
            files.append(os.path.join(folder_path, name))
    return sorted(files)


def _scan_videos(
    engine: BachataSyncEngine,
    video_dir: str,
    broll_dir: str | None,
) -> tuple[list, list | None]:
    """Scan main clips and optional B-roll, stripping thumbnails."""
    exclude = [broll_dir] if broll_dir else None
    with RichProgressObserver() as obs:
        clips = engine.scan_video_library(video_dir, exclude_dirs=exclude, observer=obs)
    logger.info("Found %d main clips.", len(clips))

    broll = None
    if broll_dir and os.path.isdir(broll_dir):
        with RichProgressObserver() as obs:
            broll = engine.scan_video_library(broll_dir, observer=obs)
        logger.info("Found %d B-roll clips.", len(broll))

    clips = strip_thumbnails(clips)
    if broll:
        broll = strip_thumbnails(broll)

    return clips, broll


def _safe_filename(path: str) -> str:
    """Derive a filesystem-safe name from an audio file path."""
    stem = os.path.splitext(os.path.basename(path))[0]
    return stem.replace(" ", "_")


def _get_track_video_dir(
    track_path: str,
    pacing_config: "PacingConfig",
    global_video_dir: str,
) -> str:
    """
    Resolve the video clip directory for a track (FEAT-030).

    If a per-track clip folder is configured for the track, use it.
    Otherwise, fall back to the global video directory.

    Args:
        track_path: Absolute path to the audio track file.
        pacing_config: Loaded PacingConfig with per_track_clips mapping.
        global_video_dir: Fallback global video directory path.

    Returns:
        Path to the video clip directory for this track.

    Raises:
        FileNotFoundError: If per-track folder is configured but doesn't exist.
    """
    track_filename = os.path.basename(track_path)
    per_track_clips = pacing_config.per_track_clips or {}

    if track_filename in per_track_clips:
        per_track_dir = per_track_clips[track_filename]
        if not os.path.isdir(per_track_dir):
            raise FileNotFoundError(
                f"Per-track clip folder not found for {track_filename}: {per_track_dir}"
            )
        logger.info(
            "Using per-track clip folder for %s: %s",
            track_filename,
            per_track_dir,
        )
        return per_track_dir

    logger.info(
        "No per-track clip folder configured for %s, using global: %s",
        track_filename,
        global_video_dir,
    )
    return global_video_dir


def _get_track_video_style(
    track_path: str,
    pacing_config: "PacingConfig",
) -> str:
    """
    Resolve the video style filter for a track (FEAT-031).

    If a per-track style is configured for the track, use it.
    Otherwise, use the global video_style from the config.

    Args:
        track_path: Absolute path to the audio track file.
        pacing_config: Loaded PacingConfig with per_track_styles mapping.

    Returns:
        Style name (e.g. 'bw', 'vintage', 'none', etc.).

    Raises:
        ValueError: If per-track style is invalid.
    """
    track_filename = os.path.basename(track_path)
    per_track_styles = pacing_config.per_track_styles or {}
    valid_styles = {"none", "bw", "vintage", "warm", "cool", "golden"}

    if track_filename in per_track_styles:
        style = per_track_styles[track_filename]
        if style not in valid_styles:
            raise ValueError(
                f"Invalid per-track style for {track_filename}: {style}. "
                f"Valid options: {', '.join(sorted(valid_styles))}"
            )
        logger.info(
            "Using per-track video style for %s: %s",
            track_filename,
            style,
        )
        return style

    logger.info(
        "No per-track style configured for %s, using global: %s",
        track_filename,
        pacing_config.video_style,
    )
    return pacing_config.video_style


# ------------------------------------------------------------------
# Core Generation Helpers
# ------------------------------------------------------------------


def _generate_video(
    engine: BachataSyncEngine,
    audio_meta,
    clips: list,
    output_path: str,
    audio_path: str,
    pacing_kwargs: dict,
    broll_clips: list | None = None,
) -> str:
    """Generate a single horizontal music video."""
    pacing = PacingConfig(**pacing_kwargs) if pacing_kwargs else None
    with RichProgressObserver() as obs:
        return engine.generate_story(
            audio_meta,
            clips,
            output_path,
            broll_clips=broll_clips,
            audio_path=audio_path,
            observer=obs,
            pacing=pacing,
        )


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bachata Beat-Story Sync: Full Pipeline"
    )
    parser.add_argument(
        "--audio",
        required=True,
        help="Folder containing audio tracks to mix",
    )
    parser.add_argument(
        "--video-dir",
        required=True,
        help="Directory containing .mp4 video clips",
    )
    parser.add_argument(
        "--broll-dir",
        default=None,
        help="Optional B-roll directory (auto-detects broll/ inside video-dir)",
    )
    parser.add_argument(
        "--output-dir",
        default="output_pipeline",
        help="Root output directory (default: output_pipeline)",
    )
    parser.add_argument(
        "--skip-mix",
        action="store_true",
        help="Skip generation of the combined mix video",
    )
    parser.add_argument(
        "--shorts-count",
        type=int,
        default=1,
        help="Number of shorts per track (0 to skip shorts)",
    )
    parser.add_argument(
        "--shorts-duration",
        type=str,
        default="60",
        help="Target short duration in seconds (e.g. '60' or '10-15')",
    )
    parser.add_argument(
        "--shared-scan",
        action="store_true",
        help="Scan video library once and reuse for all tracks (faster, less variety)",
    )
    parser.add_argument(
        "--test-mode",
        action="store_true",
        help="Quick iteration (max 4 clips, 10s of music per video)",
    )
    add_visual_args(parser)
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug-level logging for troubleshooting",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress all output except errors",
    )
    add_shorts_args(parser)
    return parser.parse_args()


# ------------------------------------------------------------------
# Main Pipeline
# ------------------------------------------------------------------


def main() -> None:
    args = parse_args()

    # FEAT-028: Route logs to stderr when JSON goes to stdout
    log_kwargs = {}
    if getattr(args, "output_json", None) == "-":
        log_kwargs["stream"] = sys.stderr

    # Configure standard logging (for internal debug messages only)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        **log_kwargs,
    )

    log = PipelineLogger(quiet=args.quiet)
    t0 = time.time()

    audio_dir = args.audio
    if not os.path.isdir(audio_dir):
        log.error(
            f"--audio must be a directory of audio tracks, got: {audio_dir}",
            hint="Check that the path exists and is a directory.",
        )
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)

    # Parse shorts duration
    min_dur, max_dur = parse_duration(args.shorts_duration)

    # Shared pacing kwargs across all renders
    pacing_kwargs = build_pacing_kwargs(args)

    engine = BachataSyncEngine()
    analyzer = AudioAnalyzer()
    generated_files: list[str] = []

    try:
        # ----------------------------------------------------------
        # 1. Discover individual audio files
        # ----------------------------------------------------------
        log.phase("🔍 Discovering Audio")
        individual_tracks = _discover_audio_files(audio_dir)
        if not individual_tracks:
            log.error(
                f"No supported audio files found in {audio_dir}",
                hint="Supported formats: "
                + ", ".join(sorted(SUPPORTED_AUDIO_EXTENSIONS)),
            )
            sys.exit(1)
        log.step(f"Found {len(individual_tracks)} track(s) in [bold]{audio_dir}[/bold]")

        # ----------------------------------------------------------
        # 2. Mix tracks (via existing resolve_audio_path caching)
        # ----------------------------------------------------------
        log.phase("🎵 Mixing Audio")
        with log.status(f"Mixing {len(individual_tracks)} tracks…"):
            with RichProgressObserver() as obs:
                mix_path = resolve_audio_path(audio_dir, observer=obs)
        log.success(f"Mix ready: [bold]{mix_path}[/bold]")

        # ----------------------------------------------------------
        # 3. Detect B-roll
        # ----------------------------------------------------------
        broll_dir = detect_broll_dir(args.video_dir, args.broll_dir)
        if broll_dir:
            log.step(f"B-roll directory: [bold]{broll_dir}[/bold]")
        else:
            log.detail("No B-roll directory detected")

        # ----------------------------------------------------------
        # 4. Shared scan (if enabled)
        # ----------------------------------------------------------
        shared_clips = None
        shared_broll = None
        if args.shared_scan:
            log.phase("📹 Scanning Video Library")
            with log.status("Scanning clips…"):
                shared_clips, shared_broll = _scan_videos(
                    engine, args.video_dir, broll_dir
                )
            clip_msg = f"Found {len(shared_clips)} main clip(s)"
            if shared_broll:
                clip_msg += f", {len(shared_broll)} B-roll"
            log.step(clip_msg)

        # ----------------------------------------------------------
        # 4b. FEAT-026 + FEAT-028: Dry-run — plan-only, skip all rendering.
        # Logic delegated to cli_utils.run_dry_run_handler to avoid
        # duplication with shorts_maker.py.
        # ----------------------------------------------------------
        if pacing_kwargs.get("dry_run"):
            reports: list[str] = []

            # Plan for mix
            if not args.skip_mix:
                mix_audio_input = AudioAnalysisInput(file_path=mix_path)
                with log.status("Analyzing mix audio…"):
                    mix_meta = analyzer.analyze(mix_audio_input)
                clips_for_mix = (
                    shared_clips
                    if args.shared_scan
                    else _scan_videos(engine, args.video_dir, broll_dir)[0]
                )
                report = run_dry_run_handler(
                    engine,
                    mix_meta,
                    clips_for_mix,
                    pacing_kwargs,
                    dry_run_output=None,  # collect; write combined below
                    output_json=getattr(args, "output_json", None),
                    report_prefix="=== Mix ===\n",
                )
                reports.append(report)

            # Plan per track
            for idx, track_path in enumerate(individual_tracks, start=1):
                track_name = _safe_filename(track_path)
                track_input = AudioAnalysisInput(file_path=track_path)
                with log.status(f"Analyzing track {idx} audio…"):
                    track_meta = analyzer.analyze(track_input)

                # FEAT-030: Resolve per-track clip directory
                base_pacing = PacingConfig(**pacing_kwargs) if pacing_kwargs else PacingConfig()
                track_video_dir = _get_track_video_dir(
                    track_path, base_pacing, args.video_dir
                )
                clips_for_track = (
                    shared_clips
                    if args.shared_scan
                    else _scan_videos(engine, track_video_dir, broll_dir)[0]
                )

                # FEAT-031: Resolve per-track video style
                track_pacing_kwargs = {**pacing_kwargs, "prefix_offset": idx - 1}
                track_style = _get_track_video_style(track_path, base_pacing)
                if track_style != base_pacing.video_style:
                    track_pacing_kwargs["video_style"] = track_style

                report = run_dry_run_handler(
                    engine,
                    track_meta,
                    clips_for_track,
                    track_pacing_kwargs,
                    dry_run_output=None,  # collect; write combined below
                    output_json=getattr(args, "output_json", None)
                    if not reports
                    else None,
                    report_prefix=f"=== Track {idx}: {track_name} ===\n",
                )
                reports.append(report)

            from src.services.plan_report import write_plan_report  # noqa: WPS433

            write_plan_report(
                "\n\n".join(reports),
                getattr(args, "dry_run_output", None),
            )

            log.step("Dry-run complete — no videos rendered.")
            return

        # ----------------------------------------------------------
        # 5. Generate mix video
        # ----------------------------------------------------------
        if not args.skip_mix:
            log.phase("🎬 Generating Mix Video")
            mix_audio_input = AudioAnalysisInput(file_path=mix_path)
            with log.status("Analyzing mix audio…"):
                mix_meta = analyzer.analyze(mix_audio_input)
            log.detail(
                f"BPM={mix_meta.bpm:.1f}  peaks={len(mix_meta.peaks)}"
                f"  duration={mix_meta.duration:.1f}s"
            )

            if args.shared_scan:
                clips, broll = shared_clips, shared_broll
            else:
                with log.status("Scanning video library…"):
                    clips, broll = _scan_videos(engine, args.video_dir, broll_dir)

            mix_out = os.path.join(args.output_dir, "mix.mp4")
            with log.status("Rendering mix video…"):
                result = _generate_video(
                    engine,
                    mix_meta,
                    clips,
                    mix_out,
                    mix_path,
                    pacing_kwargs,
                    broll_clips=broll,
                )
            generated_files.append(result)
            log.success(f"Mix video: [bold]{result}[/bold]")

        # ----------------------------------------------------------
        # 6. Per-track: video + shorts
        # ----------------------------------------------------------
        for idx, track_path in enumerate(individual_tracks, start=1):
            track_name = _safe_filename(track_path)
            track_label = f"track_{idx:02d}_{track_name}"

            log.phase(f"🎸 Track {idx}/{len(individual_tracks)}: {track_name}")

            # Analyze this track's audio independently
            track_input = AudioAnalysisInput(file_path=track_path)
            with log.status("Analyzing track audio…"):
                track_meta = analyzer.analyze(track_input)
            log.detail(
                f"BPM={track_meta.bpm:.1f}  peaks={len(track_meta.peaks)}"
                f"  duration={track_meta.duration:.1f}s"
            )

            # FEAT-030: Resolve per-track clip directory (or fall back to global)
            base_pacing = PacingConfig(**pacing_kwargs) if pacing_kwargs else PacingConfig()
            track_video_dir = _get_track_video_dir(
                track_path, base_pacing, args.video_dir
            )

            # Scan (or reuse shared scan)
            if args.shared_scan:
                clips, broll = shared_clips, shared_broll
            else:
                with log.status("Scanning video library…"):
                    clips, broll = _scan_videos(engine, track_video_dir, broll_dir)

            # FEAT-017 + FEAT-031: Build per-track pacing config
            # - Rotate prefix clips per track for intro variety
            # - Override video_style if per-track style is configured
            track_pacing = {**pacing_kwargs, "prefix_offset": idx - 1}
            track_style = _get_track_video_style(track_path, base_pacing)
            if track_style != base_pacing.video_style:
                track_pacing["video_style"] = track_style

            # Generate horizontal video
            track_out = os.path.join(args.output_dir, f"{track_label}.mp4")
            with log.status("Rendering track video…"):
                result = _generate_video(
                    engine,
                    track_meta,
                    clips,
                    track_out,
                    track_path,
                    track_pacing,
                    broll_clips=broll,
                )
            generated_files.append(result)
            log.success(f"Track video: [bold]{result}[/bold]")

            # Generate shorts (FEAT-015)
            if args.shorts_count > 0:
                shorts_dir = os.path.join(args.output_dir, "shorts", f"track_{idx:02d}")
                with log.status(f"Rendering {args.shorts_count} short(s)…"):
                    shorts = generate_shorts_batch(
                        engine,
                        track_meta,
                        clips,
                        track_path,
                        shorts_dir,
                        args.shorts_count,
                        min_dur,
                        max_dur,
                        track_pacing,
                        smart_start=args.smart_start,
                        dynamic_flow=getattr(args, "dynamic_flow", False),
                        human_touch=getattr(args, "human_touch", False),
                        cliffhanger=getattr(args, "cliffhanger", False),
                    )
                generated_files.extend(shorts)
                log.success(
                    f"{len(shorts)} short(s) saved in [bold]{shorts_dir}[/bold]"
                )

        # ----------------------------------------------------------
        # 7. Summary
        # ----------------------------------------------------------
        elapsed = time.time() - t0
        log.summary(generated_files, elapsed)

        # Also write a plain-text summary file
        summary_path = os.path.join(args.output_dir, "pipeline_summary.txt")
        summary_lines = [
            f"Pipeline complete in {elapsed:.0f}s",
            f"Total files generated: {len(generated_files)}",
            "",
        ]
        for f in generated_files:
            summary_lines.append(f"  {f}")
        with open(summary_path, "w") as fh:
            fh.write("\n".join(summary_lines) + "\n")

        # FEAT-028: Emit structured JSON output
        if getattr(args, "output_json", None):
            from src.services.json_output import build_json_output, write_json_output

            data = build_json_output(
                mix_meta if not args.skip_mix else track_meta,
                strip_thumbnails(clips) if clips else [],
                None,
                PacingConfig(**pacing_kwargs),
            )
            data["generated_files"] = generated_files
            write_json_output(data, args.output_json)

    except FileNotFoundError as e:
        log.error(
            f"File or directory not found: {e}",
            hint="Check that --audio and --video-dir paths exist.",
        )
        sys.exit(1)
    except PermissionError as e:
        log.error(
            f"Permission denied: {e}",
            hint="Check file permissions on the output directory.",
        )
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        log.error(
            f"FFmpeg process failed (exit code {e.returncode})",
            hint="Ensure FFmpeg is installed: brew install ffmpeg",
        )
        if args.verbose:
            logger.debug("FFmpeg stderr:\n%s", e.stderr)
        sys.exit(1)
    except ValidationError as e:
        log.error(
            f"Invalid configuration:\n{e}",
            hint="Check --video-style, --audio-overlay, and other options.",
        )
        sys.exit(1)
    except KeyboardInterrupt:
        log.warn("Pipeline cancelled by user.")
        log.detail(f"Partial output may be in {args.output_dir}")
        sys.exit(130)
    except Exception as e:
        log.error(
            f"Unexpected error: {e}",
            hint="Run with --verbose for full traceback.",
        )
        if args.verbose:
            logger.exception("Full traceback:")
        sys.exit(1)


if __name__ == "__main__":
    main()
