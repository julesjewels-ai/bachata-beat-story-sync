"""
Entry point for the Bachata Beat-Story Sync application.
"""
import argparse
import logging
import sys

from pydantic import ValidationError
from src.application.story_workflow import run_story_workflow
from src.cli_utils import add_visual_args, build_pacing_kwargs
from src.services.json_output import build_json_output, write_json_output
from src.services.plan_report import write_plan_report
from src.services.reporting import ExcelReportGenerator
from src.ui.console import RichProgressObserver


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bachata Beat-Story Sync: Automated Video Editor"
    )
    parser.add_argument(
        "--audio",
        type=str,
        required=True,
        help="Path to the input .wav Bachata track"
    )
    parser.add_argument(
        "--video-dir",
        type=str,
        required=True,
        help="Directory containing .mp4 video clips"
    )
    parser.add_argument(
        "--broll-dir",
        type=str,
        default=None,
        help="Optional directory containing B-roll clips"
        " (defaults to 'broll' inside video-dir if it exists)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="output_story.mp4",
        help="Path for the final output video"
    )
    parser.add_argument(
        "--export-report",
        type=str,
        help="Path to export the analysis report (e.g., report.xlsx)",
        default=None
    )
    parser.add_argument(
        "--test-mode",
        action="store_true",
        default=False,
        help="Run in test mode (max 4 clips, 10 seconds of music)"
    )
    parser.add_argument(
        "--max-clips",
        type=int,
        default=None,
        help="Maximum number of clip segments (overrides test-mode default)"
    )
    parser.add_argument(
        "--max-duration",
        type=float,
        default=None,
        help="Maximum montage duration in seconds (overrides test-mode default)"
    )
    add_visual_args(parser)
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # FEAT-028: Route logs to stderr when JSON goes to stdout
    log_stream = {}
    if getattr(args, "output_json", None) == "-":
        log_stream["stream"] = sys.stderr

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        **log_stream,
    )

    logger = logging.getLogger(__name__)
    logger.info("Starting Bachata Beat-Story Sync...")

    try:
        pacing_kwargs = build_pacing_kwargs(args)

        max_clips = args.max_clips
        max_duration = args.max_duration
        if args.test_mode:
            max_clips = max_clips or 4
            max_duration = max_duration or 10.0
        if max_clips:
            pacing_kwargs["max_clips"] = max_clips
        if max_duration:
            pacing_kwargs["max_duration_seconds"] = max_duration

        if pacing_kwargs:
            logger.info(
                "Pacing overrides: %s",
                ", ".join(f"{k}={v}" for k, v in pacing_kwargs.items()),
            )
        logger.info("Syncing visual narrative to musical dynamics...")

        result = run_story_workflow(
            args.audio,
            args.video_dir,
            args.output,
            broll_dir=args.broll_dir,
            pacing_overrides=pacing_kwargs,
            scan_observer_factory=RichProgressObserver,
            render_observer_factory=RichProgressObserver,
        )

        if result.plan_report is not None:
            write_plan_report(result.plan_report, getattr(args, "dry_run_output", None))

            if getattr(args, "output_json", None):
                data = build_json_output(
                    result.audio_meta,
                    result.video_clips,
                    result.segments,
                    result.pacing,
                )
                write_json_output(data, args.output_json)
            return

        if getattr(args, "output_json", None):
            data = build_json_output(
                result.audio_meta,
                result.video_clips,
                None,
                result.pacing,
                result.output_path,
            )
            write_json_output(data, args.output_json)

        if args.export_report and result.output_path is not None:
            logger.info(
                "Generating analysis report to %s...",
                args.export_report
            )
            report_gen = ExcelReportGenerator()
            report_gen.generate_report(
                result.audio_meta, result.video_clips, args.export_report
            )

    except ValidationError as e:
        logger.error("Input validation error: %s", e)
        sys.exit(1)
    except Exception as e:
        logger.error("An error occurred during processing: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
