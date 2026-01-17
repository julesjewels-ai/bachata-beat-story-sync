"""
Entry point for the Bachata Beat-Story Sync application.
"""
import argparse
import sys
import logging
from src.core.app import BachataSyncEngine, AudioAnalysisInput
from src.core.models import SimulationRequest
from src.interfaces.console_ui import ConsoleUI
from pydantic import ValidationError

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bachata Beat-Story Sync: Automated Video Editor"
    )
    parser.add_argument(
        "--audio", 
        type=str, 
        help="Path to the input .wav Bachata track"
    )
    parser.add_argument(
        "--video-dir", 
        type=str, 
        help="Directory containing .mp4 video clips"
    )
    parser.add_argument(
        "--output", 
        type=str, 
        default="output_story.mp4",
        help="Path for the final output video"
    )
    parser.add_argument(
        "--simulation",
        action="store_true",
        help="Run in simulation mode"
    )
    parser.add_argument(
        "--version", 
        action="version", 
        version="%(prog)s 0.1.0"
    )
    return parser.parse_args()

def main() -> None:
    logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
    args = parse_args()

    ui = ConsoleUI()
    ui.display_welcome()

    engine = BachataSyncEngine()

    if args.simulation or not (args.audio and args.video_dir):
        if not args.simulation:
             ui.console.print("[yellow]No input files provided. Defaulting to simulation mode.[/yellow]")

        try:
            # Create a request model
            sim_request = SimulationRequest(
                track_name="Bachata Demo Track",
                duration=120,
                clip_count=10
            )

            with ui.create_progress_tracker() as progress:
                # Pass the progress update method as a callback
                results = engine.run_simulation(
                    sim_request,
                    on_progress=progress.update
                )

            ui.show_success("Simulation completed successfully!")
            ui.display_results(results)

        except ValidationError as e:
            ui.show_error(f"Validation error: {e}")
            sys.exit(1)
        except Exception as e:
            ui.show_error(f"Simulation failed: {e}")
            sys.exit(1)

    elif args.audio and args.video_dir:
        try:
            # 1. Analyze Audio
            ui.console.print(f"Analyzing audio track: [bold]{args.audio}[/bold]")
            audio_input = AudioAnalysisInput(file_path=args.audio)
            audio_meta = engine.analyze_audio(audio_input)
            ui.console.print(f"Detected BPM: [cyan]{audio_meta.get('bpm')}[/cyan] | Emotional Peaks: [cyan]{len(audio_meta.get('peaks', []))}[/cyan]")

            # 2. Scan Videos
            ui.console.print(f"Scanning video library in: [bold]{args.video_dir}[/bold]")
            video_clips = engine.scan_video_library(args.video_dir)
            ui.console.print(f"Found {len(video_clips)} suitable clips.")

            # 3. Sync and Generate
            ui.console.print("Syncing visual narrative to musical dynamics...")
            result_path = engine.generate_story(audio_meta, video_clips, args.output)
            ui.show_success(f"Process complete. Output saved to: {result_path}")
        except ValidationError as e:
            ui.show_error(f"Input validation error: {e}")
            sys.exit(1)
        except Exception as e:
            ui.show_error(f"An error occurred during processing: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()