"""
Entry point for the Bachata Beat-Story Sync application.
"""
import argparse
import sys
import logging
from src.core.app import BachataSyncEngine
from src.core.audio_analyzer import AudioAnalyzer, AudioAnalysisInput
from src.core.models import PacingConfig, DiagnosticStatus
from src.services.reporting import ExcelReportGenerator
from src.services.diagnostics import (
    SystemDiagnosticManager, FFmpegCheck, DiskSpaceCheck
)
from src.ui.console import RichProgressObserver
from pydantic import ValidationError


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
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0"
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    args = parse_args()

    logger = logging.getLogger(__name__)
    logger.info("Starting Bachata Beat-Story Sync...")

    # --- System Diagnostics ---
    logger.info("Running pre-flight diagnostics...")
    diag_manager = SystemDiagnosticManager()
    diag_manager.register_check(FFmpegCheck())
    diag_manager.register_check(
        DiskSpaceCheck(min_gb=1.0, paths=[".", args.video_dir])
    )

    results = diag_manager.run_diagnostics()
    failed_checks = [r for r in results if r.status == DiagnosticStatus.FAIL]

    if failed_checks:
        logger.critical("System diagnostics FAILED. Please fix the following issues:")
        for r in failed_checks:
            logger.error("FAIL [%s]: %s (%s)", r.check_name, r.message, r.details)
        sys.exit(1)

    # Log warnings but proceed
    warn_checks = [r for r in results if r.status == DiagnosticStatus.WARN]
    for r in warn_checks:
        logger.warning("WARN [%s]: %s", r.check_name, r.message)

    logger.info("System diagnostics passed.")
    # --------------------------

    engine = BachataSyncEngine()
    audio_analyzer = AudioAnalyzer()

    try:
        # 1. Analyze Audio
        logger.info("Analyzing audio track: %s", args.audio)
        audio_input = AudioAnalysisInput(file_path=args.audio)
        audio_meta = audio_analyzer.analyze(audio_input)
        logger.info(
            "Detected BPM: %s | Emotional Peaks: %d",
            audio_meta.bpm, len(audio_meta.peaks)
        )

        # 2. Scan Videos
        logger.info("Scanning video library in: %s", args.video_dir)
        # Use RichProgressObserver for visual feedback
        with RichProgressObserver() as observer:
            video_clips = engine.scan_video_library(
                args.video_dir, observer=observer
            )
        logger.info("Found %d suitable clips.", len(video_clips))

        # 3. Sync and Generate
        pacing = None
        max_clips = args.max_clips
        max_duration = args.max_duration
        if args.test_mode:
            max_clips = max_clips or 4
            max_duration = max_duration or 10.0
        if max_clips or max_duration:
            pacing = PacingConfig(
                max_clips=max_clips,
                max_duration_seconds=max_duration,
            )
            logger.info(
                "Pacing limits: max_clips=%s, max_duration=%ss",
                max_clips or "unlimited",
                max_duration or "unlimited",
            )
        logger.info("Syncing visual narrative to musical dynamics...")

        # Strip thumbnail data before montage — it's only needed for
        # the Excel report and would pin MBs of RAM during FFmpeg.
        montage_clips = [
            clip.model_copy(update={"thumbnail_data": None})
            for clip in video_clips
        ]
        result_path = engine.generate_story(
            audio_meta, montage_clips, args.output,
            audio_path=args.audio, pacing=pacing,
        )
        del montage_clips  # free immediately
        logger.info("Process complete. Output saved to: %s", result_path)

        # 4. Generate Report
        if args.export_report:
            logger.info(
                "Generating analysis report to %s...",
                args.export_report
            )
            report_gen = ExcelReportGenerator()
            report_gen.generate_report(
                audio_meta, video_clips, args.export_report
            )

    except ValidationError as e:
        logger.error("Input validation error: %s", e)
        sys.exit(1)
    except Exception as e:
        logger.error("An error occurred during processing: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
