"""
Batch Generator for YouTube Shorts.
"""
import argparse
import logging
import os
import sys
import uuid
import random
from typing import Tuple

from pydantic import ValidationError

from src.core.app import BachataSyncEngine
from src.core.audio_analyzer import AudioAnalyzer, AudioAnalysisInput
from src.core.models import PacingConfig
from src.core.video_analyzer import VideoAnalyzer
from src.services.persistence import FileAnalysisRepository, CachedVideoAnalyzer
from src.ui.console import RichProgressObserver
from src.core.audio_mixer import AudioMixer, SUPPORTED_AUDIO_EXTENSIONS as MIX_EXTS

logger = logging.getLogger(__name__)


def parse_duration(duration_str: str) -> Tuple[float, float]:
    """Parses duration string like '60' or '10-15' into min and max floats."""
    if "-" in duration_str:
        parts = duration_str.split("-")
        if len(parts) == 2:
            try:
                min_d = float(parts[0].strip())
                max_d = float(parts[1].strip())
                return min_d, max_d
            except ValueError:
                pass
    try:
        val = float(duration_str.strip())
        return val, val
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid duration format: '{duration_str}'. Use '60' or '10-15'."
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bachata Beat-Story Sync: Shorts Batch Generator"
    )
    parser.add_argument(
        "--audio",
        type=str,
        required=True,
        help="Path to the input .wav Bachata track (or directory to mix)"
    )
    parser.add_argument(
        "--video-dir",
        type=str,
        required=True,
        help="Directory containing .mp4 video clips"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output_shorts",
        help="Directory to save the generated shorts"
    )
    parser.add_argument(
        "--duration",
        type=str,
        default="60",
        help="Target duration in seconds (e.g. '60' or '10-15' for variance)"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="Number of unique shorts to generate"
    )
    
    # New Human Touch parameters
    parser.add_argument(
        "--dynamic-flow",
        action="store_true",
        help="Accelerate pacing (shorter clips) towards the end"
    )
    parser.add_argument(
        "--human-touch",
        action="store_true",
        help="Apply small random variances to speed ramps"
    )
    parser.add_argument(
        "--cliffhanger",
        action="store_true",
        help="End abruptly for a cliffhanger effect"
    )

    return parser.parse_args()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    args = parse_args()

    min_dur, max_dur = parse_duration(args.duration)
    
    os.makedirs(args.output_dir, exist_ok=True)

    # Dependency Injection
    analysis_repo = FileAnalysisRepository()
    base_analyzer = VideoAnalyzer()
    cached_analyzer = CachedVideoAnalyzer(base_analyzer, analysis_repo)
    engine = BachataSyncEngine(video_analyzer=cached_analyzer)

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

        # 1. Analyze Audio (Once)
        logger.info("Analyzing audio track: %s", audio_path)
        audio_input = AudioAnalysisInput(file_path=audio_path)
        audio_meta = audio_analyzer.analyze(audio_input)
        logger.info(
            "Detected BPM: %s | Emotional Peaks: %d",
            audio_meta.bpm, len(audio_meta.peaks)
        )

        # 2. Scan Videos (Once)
        logger.info("Scanning video library in: %s", args.video_dir)
        with RichProgressObserver() as observer:
            video_clips = engine.scan_video_library(
                args.video_dir, observer=observer
            )
        
        vertical_count = sum(1 for c in video_clips if c.is_vertical)
        logger.info(
            "Found %d suitable clips (%d vertical, %d horizontal).", 
            len(video_clips), vertical_count, len(video_clips) - vertical_count
        )
        
        # Free memory from thumbnails
        montage_clips = [
            clip.model_copy(update={"thumbnail_data": None})
            for clip in video_clips
        ]

        # 3. Generate Shorts Sequence
        logger.info("Generating %d shorts...", args.count)
        
        for i in range(args.count):
            logger.info("=== Starting short %d of %d ===", i + 1, args.count)
            
            # Determine target duration for this specific run
            target_duration = random.uniform(min_dur, max_dur)
            run_seed = str(uuid.uuid4())
            
            pacing = PacingConfig(
                is_shorts=True,
                seed=run_seed,
                max_duration_seconds=target_duration,
                accelerate_pacing=args.dynamic_flow,
                randomize_speed_ramps=args.human_touch,
                abrupt_ending=args.cliffhanger
            )
            
            out_filename = f"short_{i + 1:03d}.mp4"
            out_path = os.path.join(args.output_dir, out_filename)
            
            with RichProgressObserver() as observer:
                result_path = engine.generate_story(
                    audio_meta, montage_clips, out_path,
                    audio_path=audio_input.file_path, observer=observer, pacing=pacing,
                )
            
            logger.info("Short %d saved to: %s", i + 1, result_path)

        logger.info("Batch generation complete! All %d shorts generated in %s", args.count, args.output_dir)

    except ValidationError as e:
        logger.error("Input validation error: %s", e)
        sys.exit(1)
    except Exception as e:
        logger.error("An error occurred during processing: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
