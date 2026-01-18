"""
Entry point for the Bachata Beat-Story Sync application.
"""
import argparse
import sys
import logging
from src.core.app import BachataSyncEngine, AudioAnalysisInput
from src.services.reporting import ExcelReportGenerator
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
        help="Path to export the Excel analysis report (e.g. report.xlsx)"
    )
    parser.add_argument(
        "--version", 
        action="version", 
        version="%(prog)s 0.1.0"
    )
    return parser.parse_args()

def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    args = parse_args()

    logger = logging.getLogger(__name__)
    logger.info("Starting Bachata Beat-Story Sync...")

    engine = BachataSyncEngine()

    try:
        # 1. Analyze Audio
        logger.info(f"Analyzing audio track: {args.audio}")
        audio_input = AudioAnalysisInput(file_path=args.audio)
        audio_meta = engine.analyze_audio(audio_input)
        logger.info(f"Detected BPM: {audio_meta.bpm} | Emotional Peaks: {len(audio_meta.peaks)}")

        # 2. Scan Videos
        logger.info(f"Scanning video library in: {args.video_dir}")
        video_clips = engine.scan_video_library(args.video_dir)
        logger.info(f"Found {len(video_clips)} suitable clips.")

        # Report Generation Feature
        if args.export_report:
            logger.info(f"Generating analysis report: {args.export_report}")
            report_service = ExcelReportGenerator()
            report_service.generate_report(audio_meta, video_clips, args.export_report)
            logger.info("Report generated successfully.")

        # 3. Sync and Generate
        logger.info("Syncing visual narrative to musical dynamics...")
        result_path = engine.generate_story(audio_meta, video_clips, args.output)
        logger.info(f"Process complete. Output saved to: {result_path}")
    except ValidationError as e:
        logger.error(f"Input validation error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"An error occurred during processing: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()