"""
Entry point for the Bachata Beat-Story Sync application.
"""
import argparse
import sys
import logging
from src.core.app import BachataSyncEngine
from src.core.audio_analyzer import AudioAnalyzer, AudioAnalysisInput
from src.core.models import PacingConfig
from src.services.reporting import ExcelReportGenerator
from src.ui.console import RichProgressObserver
from pydantic import ValidationError
import os
from src.core.audio_mixer import AudioMixer, SUPPORTED_AUDIO_EXTENSIONS as MIX_EXTS

from src.core.audio_mixer import AudioMixer, SUPPORTED_AUDIO_EXTENSIONS as MIX_EXTS


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
        "--export-edl",
        type=str,
        help="Path to export the montage as an EDL timeline (e.g., project.edl)",
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

    engine = BachataSyncEngine()
    audio_analyzer = AudioAnalyzer()

    try:
        audio_path = args.audio
        if os.path.isdir(audio_path):
            valid_files = [
                f for f in os.listdir(audio_path) 
                if os.path.isfile(os.path.join(audio_path, f)) 
                and any(f.lower().endswith(ext.lower()) for ext in MIX_EXTS)
                and f != "_mixed_audio.wav"
            ]
            
            if len(valid_files) > 1:
                logger.info("Multiple audio files detected. Mixing tracks...")
                mixed_output = os.path.join(audio_path, "_mixed_audio.wav")
                mixer = AudioMixer()
                with RichProgressObserver() as mix_observer:
                    audio_path = mixer.mix_audio_folder(audio_path, mixed_output, observer=mix_observer)
                logger.info("Mixed audio saved to: %s", audio_path)

        # 1. Analyze Audio
        logger.info("Analyzing audio track: %s", audio_path)
        audio_input = AudioAnalysisInput(file_path=audio_path)
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

        # 1. Create Plan
        plan = engine.create_plan(audio_meta, montage_clips, pacing=pacing)
        logger.info("Generated segment plan with %d segments.", len(plan))

        # 2. Export EDL (if requested)
        if args.export_edl:
            logger.info("Exporting EDL to %s...", args.export_edl)
            from src.services.export.edl import EdlTimelineExporter
            exporter = EdlTimelineExporter()
            exporter.export(plan, args.export_edl)
            logger.info("EDL export complete.")

        # 3. Render
        with RichProgressObserver() as observer:
            result_path = engine.render_story_from_plan(
                plan, args.output,
                audio_path=audio_input.file_path,
                observer=observer,
                pacing=pacing
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
