"""
Entry point for the Bachata Beat-Story Sync application.
"""

import argparse
import logging
import os
import sys

from pydantic import ValidationError
from src.core.app import BachataSyncEngine
from src.core.audio_analyzer import AudioAnalysisInput, AudioAnalyzer
from src.core.audio_mixer import resolve_audio_path
from src.core.models import PacingConfig
from src.core.video_analyzer import VideoAnalyzer
from src.services.persistence import CachedVideoAnalyzer, FileAnalysisRepository
from src.services.reporting import ExcelReportGenerator
from src.ui.console import RichProgressObserver


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bachata Beat-Story Sync: Automated Video Editor"
    )
    parser.add_argument(
        "--audio", type=str, required=True, help="Path to the input .wav Bachata track"
    )
    parser.add_argument(
        "--video-dir",
        type=str,
        required=True,
        help="Directory containing .mp4 video clips",
    )
    parser.add_argument(
        "--broll-dir",
        type=str,
        default=None,
        help="Optional directory containing B-roll clips"
        " (defaults to 'broll' inside video-dir if it exists)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="output_story.mp4",
        help="Path for the final output video",
    )
    parser.add_argument(
        "--export-report",
        type=str,
        help="Path to export the analysis report (e.g., report.xlsx)",
        default=None,
    )
    parser.add_argument(
        "--test-mode",
        action="store_true",
        default=False,
        help="Run in test mode (max 4 clips, 10 seconds of music)",
    )
    parser.add_argument(
        "--max-clips",
        type=int,
        default=None,
        help="Maximum number of clip segments (overrides test-mode default)",
    )
    parser.add_argument(
        "--max-duration",
        type=float,
        default=None,
        help="Maximum montage duration in seconds (overrides test-mode default)",
    )
    parser.add_argument(
        "--video-style",
        type=str,
        default=None,
        choices=["none", "bw", "vintage", "warm", "cool"],
        help="Color grading style: none, bw, vintage, warm, cool",
    )
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    args = parse_args()

    logger = logging.getLogger(__name__)
    logger.info("Starting Bachata Beat-Story Sync...")

    # Set up caching infrastructure
    repository = FileAnalysisRepository()
    video_analyzer = CachedVideoAnalyzer(
        analyzer=VideoAnalyzer(),
        repository=repository,
    )

    engine = BachataSyncEngine(video_analyzer=video_analyzer)
    audio_analyzer = AudioAnalyzer()

    try:
        audio_path = args.audio
        with RichProgressObserver() as mix_observer:
            audio_path = resolve_audio_path(audio_path, observer=mix_observer)

        # 1. Analyze Audio
        logger.info("Analyzing audio track: %s", audio_path)
        audio_input = AudioAnalysisInput(file_path=audio_path)
        audio_meta = audio_analyzer.analyze(audio_input)
        logger.info(
            "Detected BPM: %s | Emotional Peaks: %d",
            audio_meta.bpm,
            len(audio_meta.peaks),
        )

        # 2. Scan Videos
        logger.info("Scanning video library in: %s", args.video_dir)

        broll_dir = args.broll_dir
        if not broll_dir:
            auto_broll_path = os.path.join(args.video_dir, "broll")
            if os.path.exists(auto_broll_path) and os.path.isdir(auto_broll_path):
                broll_dir = auto_broll_path
                logger.info("Auto-detected B-roll folder: %s", broll_dir)

        # Build list of directories to exclude from the main video scan
        exclude_dirs = [broll_dir] if broll_dir else None

        # Use RichProgressObserver for visual feedback
        with RichProgressObserver() as observer:
            video_clips = engine.scan_video_library(
                args.video_dir, exclude_dirs=exclude_dirs, observer=observer
            )
        logger.info("Found %d suitable clips.", len(video_clips))

        broll_clips = None
        if broll_dir and os.path.exists(broll_dir):
            logger.info("Scanning B-roll library in: %s", broll_dir)
            with RichProgressObserver() as observer:
                broll_clips = engine.scan_video_library(broll_dir, observer=observer)
            logger.info("Found %d suitable B-roll clips.", len(broll_clips))

        # 3. Sync and Generate
        pacing = None
        max_clips = args.max_clips
        max_duration = args.max_duration
        if args.test_mode:
            max_clips = max_clips or 4
            max_duration = max_duration or 10.0

        # Build pacing overrides from CLI args
        pacing_kwargs: dict = {}
        if max_clips:
            pacing_kwargs["max_clips"] = max_clips
        if max_duration:
            pacing_kwargs["max_duration_seconds"] = max_duration
        if args.video_style:
            pacing_kwargs["video_style"] = args.video_style

        if pacing_kwargs:
            pacing = PacingConfig(**pacing_kwargs)
            logger.info(
                "Pacing overrides: %s",
                ", ".join(f"{k}={v}" for k, v in pacing_kwargs.items()),
            )
        logger.info("Syncing visual narrative to musical dynamics...")

        # Strip thumbnail data before montage — it's only needed for
        # the Excel report and would pin MBs of RAM during FFmpeg.
        montage_clips = [
            clip.model_copy(update={"thumbnail_data": None}) for clip in video_clips
        ]
        with RichProgressObserver() as observer:
            result_path = engine.generate_story(
                audio_meta,
                montage_clips,
                args.output,
                broll_clips=broll_clips,
                audio_path=audio_input.file_path,
                observer=observer,
                pacing=pacing,
            )
        del montage_clips  # free immediately
        logger.info("Process complete. Output saved to: %s", result_path)

        # 4. Generate Report
        if args.export_report:
            logger.info("Generating analysis report to %s...", args.export_report)
            report_gen = ExcelReportGenerator()
            report_gen.generate_report(audio_meta, video_clips, args.export_report)

    except ValidationError as e:
        logger.error("Input validation error: %s", e)
        sys.exit(1)
    except Exception as e:
        logger.error("An error occurred during processing: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
