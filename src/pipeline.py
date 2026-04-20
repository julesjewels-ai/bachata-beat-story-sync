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

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
from functools import partial
from typing import TYPE_CHECKING

from pydantic import ValidationError

from src.application.pipeline_helpers import (
    discover_audio_files as _discover_audio_files,
)
from src.application.pipeline_helpers import (
    extract_track_metadata as _extract_track_metadata,
)
from src.application.pipeline_helpers import get_track_video_dir as _get_track_video_dir
from src.application.pipeline_helpers import (
    get_track_video_style as _get_track_video_style,
)
from src.application.pipeline_helpers import safe_filename as _safe_filename
from src.application.pipeline_phases import (
    PipelinePhaseSupport,
    generate_compilation_phase,
    generate_mix_video_phase,
    process_individual_tracks,
    run_dry_run_phase,
    write_summary,
)
from src.application.pipeline_workflow import (
    PipelineWorkflow,
    PipelineWorkflowDependencies,
)
from src.cli_utils import (
    add_shorts_args,
    add_visual_args,
    strip_thumbnails,
)

if TYPE_CHECKING:
    from src.core.models import VideoAnalysisResult

from src.core.app import BachataSyncEngine
from src.ui.console import PipelineLogger, RichProgressObserver

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _scan_videos(
    engine: BachataSyncEngine,
    video_dir: str,
    broll_dir: str | None,
) -> tuple[list[VideoAnalysisResult], list[VideoAnalysisResult] | None]:
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
# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------


def _build_workflow_dependencies() -> PipelineWorkflowDependencies:
    """Build dependency bundle for the application-layer pipeline workflow."""
    phase_support = PipelinePhaseSupport(
        scan_videos=_scan_videos,
        safe_filename=_safe_filename,
        get_track_video_dir=_get_track_video_dir,
        get_track_video_style=_get_track_video_style,
        extract_track_metadata=_extract_track_metadata,
    )
    return PipelineWorkflowDependencies(
        discover_audio_files=_discover_audio_files,
        extract_track_metadata=_extract_track_metadata,
        scan_videos=_scan_videos,
        run_dry_run_phase=partial(run_dry_run_phase, phase_support),
        generate_mix_video_phase=partial(generate_mix_video_phase, phase_support),
        process_individual_tracks=partial(process_individual_tracks, phase_support),
        generate_compilation_phase=generate_compilation_phase,
        write_summary=write_summary,
    )


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
        "--compilation",
        action="store_true",
        help=(
            "Generate a compilation video by concatenating all "
            "individual track videos"
        ),
    )
    parser.add_argument(
        "--no-compilation",
        action="store_true",
        help="Skip compilation video generation (overrides config)",
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
    log_stream = sys.stderr if getattr(args, "output_json", None) == "-" else None
    log_level = logging.DEBUG if args.verbose else logging.WARNING
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Configure standard logging (for internal debug messages only)
    logging.basicConfig(
        level=log_level,
        format=log_format,
        stream=log_stream,
    )

    log = PipelineLogger(quiet=args.quiet)
    workflow = PipelineWorkflow(_build_workflow_dependencies())

    try:
        workflow.run(args, log)

    except NotADirectoryError:
        log.error(
            f"--audio must be a directory of audio tracks, got: {args.audio}",
            hint="Check that the path exists and is a directory.",
        )
        sys.exit(1)
    except FileNotFoundError as e:
        log.error(
            f"File or directory not found: {e}",
            hint="Check that --audio and --video-dir paths exist and contain media.",
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
