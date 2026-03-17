"""
Batch Generator for YouTube Shorts.
"""

import argparse
import logging
import os
import sys

from pydantic import ValidationError

from src.cli_utils import (
    add_shorts_args,
    add_visual_args,
    build_pacing_kwargs,
    generate_shorts_batch,
    parse_duration,
)
from src.core.app import BachataSyncEngine
from src.core.audio_analyzer import AudioAnalysisInput, AudioAnalyzer
from src.core.audio_mixer import resolve_audio_path
from src.ui.console import RichProgressObserver

logger = logging.getLogger(__name__)





def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bachata Beat-Story Sync: Shorts Batch Generator"
    )
    parser.add_argument(
        "--audio",
        type=str,
        required=True,
        help="Path to the input .wav Bachata track (or directory to mix)",
    )
    parser.add_argument(
        "--video-dir",
        type=str,
        required=True,
        help="Directory containing .mp4 video clips",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output_shorts",
        help="Directory to save the generated shorts",
    )
    parser.add_argument(
        "--duration",
        type=str,
        default="60",
        help="Target duration in seconds (e.g. '60' or '10-15' for variance)",
    )
    parser.add_argument(
        "--count", type=int, default=1, help="Number of unique shorts to generate"
    )

    add_visual_args(parser)
    add_shorts_args(parser)

    return parser.parse_args()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    args = parse_args()

    min_dur, max_dur = parse_duration(args.duration)

    os.makedirs(args.output_dir, exist_ok=True)

    engine = BachataSyncEngine()
    audio_analyzer = AudioAnalyzer()

    try:
        audio_path = args.audio
        with RichProgressObserver() as mix_observer:
            audio_path = resolve_audio_path(audio_path, observer=mix_observer)

        # 1. Analyze Audio (Once)
        logger.info("Analyzing audio track: %s", audio_path)
        audio_input = AudioAnalysisInput(file_path=audio_path)
        audio_meta = audio_analyzer.analyze(audio_input)
        logger.info(
            "Detected BPM: %s | Emotional Peaks: %d",
            audio_meta.bpm,
            len(audio_meta.peaks),
        )

        # 2. Scan Videos (Once)
        logger.info("Scanning video library in: %s", args.video_dir)
        with RichProgressObserver() as observer:
            video_clips = engine.scan_video_library(args.video_dir, observer=observer)

        vertical_count = sum(1 for c in video_clips if c.is_vertical)
        logger.info(
            "Found %d suitable clips (%d vertical, %d horizontal).",
            len(video_clips),
            vertical_count,
            len(video_clips) - vertical_count,
        )

        # Free memory from thumbnails
        montage_clips = [
            clip.model_copy(update={"thumbnail_data": None}) for clip in video_clips
        ]

        # 3. Generate Shorts (delegate to shared function)
        pacing_kwargs = build_pacing_kwargs(args)
        results = generate_shorts_batch(
            engine,
            audio_meta,
            montage_clips,
            audio_path,
            args.output_dir,
            args.count,
            min_dur,
            max_dur,
            pacing_kwargs,
            smart_start=args.smart_start,
            dynamic_flow=args.dynamic_flow,
            human_touch=args.human_touch,
            cliffhanger=args.cliffhanger,
        )

        logger.info(
            "Batch generation complete! All %d shorts generated in %s",
            len(results),
            args.output_dir,
        )

    except ValidationError as e:
        logger.error("Input validation error: %s", e)
        sys.exit(1)
    except Exception as e:
        logger.error("An error occurred during processing: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
