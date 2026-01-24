"""
Entry point for the Bachata Beat-Story Sync application.
"""
import argparse
import sys
import logging
from src.core.app import BachataSyncEngine, AudioAnalysisInput
from src.services.reporting import ExcelReportGenerator
from src.ui.console import RichConsole
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
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    args = parse_args()

    logger = logging.getLogger(__name__)
    console = RichConsole()
    console.print("Starting Bachata Beat-Story Sync...", style="bold green")

    engine = BachataSyncEngine()

    try:
        # 1. Analyze Audio
        console.print(f"Analyzing audio track: {args.audio}", style="cyan")
        audio_input = AudioAnalysisInput(file_path=args.audio)
        audio_meta = engine.analyze_audio(audio_input)
        console.print(f"Detected BPM: {audio_meta.bpm} | Emotional Peaks: {len(audio_meta.peaks)}", style="blue")

        # 2. Scan Videos
        console.print(f"Scanning video library in: {args.video_dir}", style="cyan")
        video_clips = engine.scan_video_library(args.video_dir, observer=console)
        console.print(f"Found {len(video_clips)} suitable clips.", style="green")

        # 3. Sync and Generate
        console.print("Syncing visual narrative to musical dynamics...", style="cyan")
        result_path = engine.generate_story(audio_meta, video_clips, args.output)
        console.print(f"Process complete. Output saved to: {result_path}", style="bold green")

        # 4. Generate Report
        if args.export_report:
            console.print(f"Generating analysis report to {args.export_report}...", style="cyan")
            report_gen = ExcelReportGenerator()
            report_gen.generate_report(audio_meta, video_clips, args.export_report)

    except ValidationError as e:
        logger.error(f"Input validation error: {e}")
        console.print(f"Input validation error: {e}", style="bold red")
        sys.exit(1)
    except Exception as e:
        logger.error(f"An error occurred during processing: {e}")
        console.print(f"An error occurred during processing: {e}", style="bold red")
        console.stop() # Ensure progress bar is cleaned up
        sys.exit(1)

if __name__ == "__main__":
    main()