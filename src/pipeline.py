"""
Full Pipeline Orchestrator — FEAT-014 / FEAT-015 / FEAT-016.

Single command to:
  1. Mix a folder of audio tracks into one combined WAV.
  2. Generate a horizontal music video for the mix.
  3. Generate a horizontal music video for each individual track.
  4. Generate N YouTube Shorts for each individual track.
"""

import argparse
import logging
import os
import random
import sys
import time
import uuid

from pydantic import ValidationError

from src.core.app import BachataSyncEngine
from src.core.audio_analyzer import AudioAnalysisInput, AudioAnalyzer
from src.core.audio_mixer import (
    SUPPORTED_AUDIO_EXTENSIONS,
    resolve_audio_path,
)
from src.core.models import PacingConfig
from src.ui.console import RichProgressObserver

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _discover_audio_files(folder_path: str) -> list[str]:
    """Return sorted list of audio files in *folder_path*, excluding cache."""
    files = []
    for name in os.listdir(folder_path):
        if name == "_mixed_audio.wav":
            continue
        if os.path.splitext(name)[1].lower() in SUPPORTED_AUDIO_EXTENSIONS:
            files.append(os.path.join(folder_path, name))
    return sorted(files)


def _parse_duration(duration_str: str) -> tuple[float, float]:
    """Parse '60' or '10-15' into (min, max) floats."""
    if "-" in duration_str:
        parts = duration_str.split("-")
        if len(parts) == 2:
            try:
                return float(parts[0].strip()), float(parts[1].strip())
            except ValueError:
                pass
    try:
        val = float(duration_str.strip())
        return val, val
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid duration format: '{duration_str}'."
            " Use '60' or '10-15'."
        ) from None


def _build_pacing_kwargs(args: argparse.Namespace) -> dict:
    """Build the shared pacing kwargs dict from CLI args."""
    kwargs: dict = {}
    if args.test_mode:
        kwargs["max_clips"] = 4
        kwargs["max_duration_seconds"] = 10.0
    if args.video_style:
        kwargs["video_style"] = args.video_style
    if args.audio_overlay:
        kwargs["audio_overlay"] = args.audio_overlay
    if args.audio_overlay_opacity is not None:
        kwargs["audio_overlay_opacity"] = args.audio_overlay_opacity
    if args.audio_overlay_position:
        kwargs["audio_overlay_position"] = args.audio_overlay_position
    return kwargs


def _detect_broll_dir(
    video_dir: str, explicit_broll_dir: str | None
) -> str | None:
    """Auto-detect B-roll subfolder, matching main.py behaviour."""
    if explicit_broll_dir:
        return explicit_broll_dir
    auto = os.path.join(video_dir, "broll")
    if os.path.isdir(auto):
        logger.info("Auto-detected B-roll folder: %s", auto)
        return auto
    return None


def _scan_videos(
    engine: BachataSyncEngine,
    video_dir: str,
    broll_dir: str | None,
) -> tuple[list, list | None]:
    """Scan main clips and optional B-roll, stripping thumbnails."""
    exclude = [broll_dir] if broll_dir else None
    with RichProgressObserver() as obs:
        clips = engine.scan_video_library(
            video_dir, exclude_dirs=exclude, observer=obs
        )
    logger.info("Found %d main clips.", len(clips))

    broll = None
    if broll_dir and os.path.isdir(broll_dir):
        with RichProgressObserver() as obs:
            broll = engine.scan_video_library(broll_dir, observer=obs)
        logger.info("Found %d B-roll clips.", len(broll))

    # Strip thumbnails to reduce memory (matches main.py pattern)
    clips = [c.model_copy(update={"thumbnail_data": None}) for c in clips]
    if broll:
        broll = [c.model_copy(update={"thumbnail_data": None}) for c in broll]

    return clips, broll


def _safe_filename(path: str) -> str:
    """Derive a filesystem-safe name from an audio file path."""
    stem = os.path.splitext(os.path.basename(path))[0]
    return stem.replace(" ", "_")


# ------------------------------------------------------------------
# Core Generation Helpers
# ------------------------------------------------------------------

def _generate_video(
    engine: BachataSyncEngine,
    audio_meta,
    clips: list,
    output_path: str,
    audio_path: str,
    pacing_kwargs: dict,
    broll_clips: list | None = None,
) -> str:
    """Generate a single horizontal music video."""
    pacing = PacingConfig(**pacing_kwargs) if pacing_kwargs else None
    with RichProgressObserver() as obs:
        return engine.generate_story(
            audio_meta,
            clips,
            output_path,
            broll_clips=broll_clips,
            audio_path=audio_path,
            observer=obs,
            pacing=pacing,
        )


def _generate_shorts(
    engine: BachataSyncEngine,
    audio_meta,
    clips: list,
    audio_path: str,
    output_dir: str,
    count: int,
    min_dur: float,
    max_dur: float,
    pacing_kwargs: dict,
) -> list[str]:
    """Generate *count* shorts into *output_dir*, returning paths."""
    os.makedirs(output_dir, exist_ok=True)
    generated: list[str] = []

    for i in range(count):
        target_duration = random.uniform(min_dur, max_dur)
        run_seed = str(uuid.uuid4())

        shorts_kwargs = {
            **pacing_kwargs,
            "is_shorts": True,
            "seed": run_seed,
            "max_duration_seconds": target_duration,
        }
        # Remove full-video-only keys that conflict with shorts
        shorts_kwargs.pop("max_clips", None)

        pacing = PacingConfig(**shorts_kwargs)
        out_path = os.path.join(output_dir, f"short_{i + 1:03d}.mp4")

        logger.info(
            "  Generating short %d/%d (%.0fs)...", i + 1, count, target_duration
        )
        with RichProgressObserver() as obs:
            result = engine.generate_story(
                audio_meta,
                clips,
                out_path,
                audio_path=audio_path,
                observer=obs,
                pacing=pacing,
            )
        generated.append(result)

    return generated


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bachata Beat-Story Sync: Full Pipeline"
    )
    parser.add_argument(
        "--audio", required=True,
        help="Folder containing audio tracks to mix",
    )
    parser.add_argument(
        "--video-dir", required=True,
        help="Directory containing .mp4 video clips",
    )
    parser.add_argument(
        "--broll-dir", default=None,
        help="Optional B-roll directory (auto-detects broll/ inside video-dir)",
    )
    parser.add_argument(
        "--output-dir", default="output_pipeline",
        help="Root output directory (default: output_pipeline)",
    )
    parser.add_argument(
        "--skip-mix", action="store_true",
        help="Skip generation of the combined mix video",
    )
    parser.add_argument(
        "--shorts-count", type=int, default=1,
        help="Number of shorts per track (0 to skip shorts)",
    )
    parser.add_argument(
        "--shorts-duration", type=str, default="60",
        help="Target short duration in seconds (e.g. '60' or '10-15')",
    )
    parser.add_argument(
        "--shared-scan", action="store_true",
        help="Scan video library once and reuse for all tracks (faster, less variety)",
    )
    parser.add_argument(
        "--test-mode", action="store_true",
        help="Quick iteration (max 4 clips, 10s of music per video)",
    )
    parser.add_argument(
        "--video-style", default=None,
        choices=["none", "bw", "vintage", "warm", "cool"],
        help="Color grading style",
    )
    parser.add_argument(
        "--audio-overlay", default=None,
        choices=["none", "waveform", "bars"],
        help="Music-synced visualizer overlay",
    )
    parser.add_argument(
        "--audio-overlay-opacity", type=float, default=None,
        help="Visualizer opacity (0.0-1.0)",
    )
    parser.add_argument(
        "--audio-overlay-position", default=None,
        choices=["left", "center", "right"],
        help="Visualizer position",
    )
    return parser.parse_args()


# ------------------------------------------------------------------
# Main Pipeline
# ------------------------------------------------------------------

def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    args = parse_args()
    t0 = time.time()

    audio_dir = args.audio
    if not os.path.isdir(audio_dir):
        logger.error("--audio must be a directory of audio tracks, got: %s", audio_dir)
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)

    # Parse shorts duration
    min_dur, max_dur = _parse_duration(args.shorts_duration)

    # Shared pacing kwargs across all renders
    pacing_kwargs = _build_pacing_kwargs(args)

    engine = BachataSyncEngine()
    analyzer = AudioAnalyzer()
    generated_files: list[str] = []

    try:
        # ----------------------------------------------------------
        # 1. Discover individual audio files
        # ----------------------------------------------------------
        individual_tracks = _discover_audio_files(audio_dir)
        if not individual_tracks:
            logger.error("No supported audio files found in %s", audio_dir)
            sys.exit(1)
        logger.info(
            "Discovered %d audio tracks in %s",
            len(individual_tracks), audio_dir,
        )

        # ----------------------------------------------------------
        # 2. Mix tracks (via existing resolve_audio_path caching)
        # ----------------------------------------------------------
        logger.info("=== Step 1: Mixing audio tracks ===")
        with RichProgressObserver() as obs:
            mix_path = resolve_audio_path(audio_dir, observer=obs)
        logger.info("Mix audio ready: %s", mix_path)

        # ----------------------------------------------------------
        # 3. Detect B-roll
        # ----------------------------------------------------------
        broll_dir = _detect_broll_dir(args.video_dir, args.broll_dir)

        # ----------------------------------------------------------
        # 4. Shared scan (if enabled)
        # ----------------------------------------------------------
        shared_clips = None
        shared_broll = None
        if args.shared_scan:
            logger.info("=== Shared scan: scanning video library once ===")
            shared_clips, shared_broll = _scan_videos(
                engine, args.video_dir, broll_dir
            )

        # ----------------------------------------------------------
        # 5. Generate mix video
        # ----------------------------------------------------------
        if not args.skip_mix:
            logger.info("=== Step 2: Generating mix video ===")
            mix_audio_input = AudioAnalysisInput(file_path=mix_path)
            mix_meta = analyzer.analyze(mix_audio_input)
            logger.info(
                "Mix: BPM=%.1f, peaks=%d, duration=%.1fs",
                mix_meta.bpm, len(mix_meta.peaks), mix_meta.duration,
            )

            if args.shared_scan:
                clips, broll = shared_clips, shared_broll
            else:
                clips, broll = _scan_videos(engine, args.video_dir, broll_dir)

            mix_out = os.path.join(args.output_dir, "mix.mp4")
            result = _generate_video(
                engine, mix_meta, clips, mix_out,
                mix_path, pacing_kwargs, broll_clips=broll,
            )
            generated_files.append(result)
            logger.info("Mix video saved: %s", result)

        # ----------------------------------------------------------
        # 6. Per-track: video + shorts
        # ----------------------------------------------------------
        for idx, track_path in enumerate(individual_tracks, start=1):
            track_name = _safe_filename(track_path)
            track_label = f"track_{idx:02d}_{track_name}"
            logger.info(
                "=== Track %d/%d: %s ===",
                idx, len(individual_tracks), track_name,
            )

            # Analyze this track's audio independently
            track_input = AudioAnalysisInput(file_path=track_path)
            track_meta = analyzer.analyze(track_input)
            logger.info(
                "  BPM=%.1f, peaks=%d, duration=%.1fs",
                track_meta.bpm, len(track_meta.peaks), track_meta.duration,
            )

            # Scan (or reuse shared scan)
            if args.shared_scan:
                clips, broll = shared_clips, shared_broll
            else:
                clips, broll = _scan_videos(engine, args.video_dir, broll_dir)

            # Generate horizontal video
            track_out = os.path.join(args.output_dir, f"{track_label}.mp4")
            result = _generate_video(
                engine, track_meta, clips, track_out,
                track_path, pacing_kwargs, broll_clips=broll,
            )
            generated_files.append(result)
            logger.info("  Track video saved: %s", result)

            # Generate shorts (FEAT-015)
            if args.shorts_count > 0:
                shorts_dir = os.path.join(
                    args.output_dir, "shorts", f"track_{idx:02d}"
                )
                shorts = _generate_shorts(
                    engine, track_meta, clips, track_path,
                    shorts_dir, args.shorts_count,
                    min_dur, max_dur, pacing_kwargs,
                )
                generated_files.extend(shorts)
                logger.info(
                    "  %d shorts saved in %s", len(shorts), shorts_dir
                )

        # ----------------------------------------------------------
        # 7. Summary
        # ----------------------------------------------------------
        elapsed = time.time() - t0
        summary_lines = [
            f"Pipeline complete in {elapsed:.0f}s",
            f"Total files generated: {len(generated_files)}",
            "",
        ]
        for f in generated_files:
            summary_lines.append(f"  {f}")

        summary_text = "\n".join(summary_lines)
        logger.info("\n%s", summary_text)

        summary_path = os.path.join(args.output_dir, "pipeline_summary.txt")
        with open(summary_path, "w") as fh:
            fh.write(summary_text + "\n")

    except ValidationError as e:
        logger.error("Input validation error: %s", e)
        sys.exit(1)
    except Exception as e:
        logger.error("Pipeline failed: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
