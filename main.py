"""
Entry point for the Bachata Beat-Story Sync application.
"""
import argparse
import sys
import logging
from src.core.app import BachataSyncEngine
from src.core.audio_analyzer import AudioAnalyzer
from src.core.video_analyzer import VideoAnalyzer
from src.core.models import AudioAnalysisInput
from src.services.reporting import ExcelReportGenerator
from src.services.caching import JsonFileCache
from src.services.caching.analyzers import CachedVideoAnalyzer
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

    # Initialize Caching Layer
    cache = JsonFileCache(".video_analysis_cache.json")
    cached_analyzer = CachedVideoAnalyzer(VideoAnalyzer(), cache)

    engine = BachataSyncEngine(video_analyzer=cached_analyzer)
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
        observer = RichProgressObserver()
        video_clips = engine.scan_video_library(
            args.video_dir, observer=observer
        )
        logger.info("Found %d suitable clips.", len(video_clips))

        # 3. Sync and Generate
        logger.info("Syncing visual narrative to musical dynamics...")
        result_path = engine.generate_story(
            audio_meta, video_clips, args.output,
            audio_path=args.audio
        )
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
