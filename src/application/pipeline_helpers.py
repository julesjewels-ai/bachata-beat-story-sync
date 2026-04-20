"""Shared helper functions for the full pipeline entry point."""

from __future__ import annotations

import logging
import os
import re

from src.config.app_config import PipelineConfig
from src.core.audio_mixer import SUPPORTED_AUDIO_EXTENSIONS

logger = logging.getLogger(__name__)

VALID_VIDEO_STYLES = {"none", "bw", "vintage", "warm", "cool", "golden"}


def discover_audio_files(folder_path: str) -> list[str]:
    """Return sorted list of audio files in *folder_path*, excluding cache."""
    files = []
    for name in os.listdir(folder_path):
        if name == "_mixed_audio.wav":
            continue
        if os.path.splitext(name)[1].lower() in SUPPORTED_AUDIO_EXTENSIONS:
            files.append(os.path.join(folder_path, name))
    return sorted(files)


def safe_filename(path: str) -> str:
    """Derive a filesystem-safe name from an audio file path."""
    return os.path.splitext(os.path.basename(path))[0]


def get_track_video_dir(
    track_path: str,
    pipeline_config: PipelineConfig,
    global_video_dir: str,
) -> str:
    """Resolve the video clip directory for a track."""
    track_filename = os.path.basename(track_path)
    per_track_clips = pipeline_config.track_clips or {}

    if track_filename in per_track_clips:
        per_track_dir = per_track_clips[track_filename]
        if not os.path.isdir(per_track_dir):
            raise FileNotFoundError(
                f"Per-track clip folder not found for {track_filename}: {per_track_dir}"
            )
        logger.info(
            "Using per-track clip folder for %s: %s",
            track_filename,
            per_track_dir,
        )
        return per_track_dir

    logger.info(
        "No per-track clip folder configured for %s, using global: %s",
        track_filename,
        global_video_dir,
    )
    return global_video_dir


def get_track_video_style(
    track_path: str,
    pipeline_config: PipelineConfig,
    default_style: str,
) -> str:
    """Resolve the video style filter for a track."""
    track_filename = os.path.basename(track_path)
    per_track_styles = pipeline_config.track_styles or {}

    if track_filename in per_track_styles:
        style = per_track_styles[track_filename]
        if style not in VALID_VIDEO_STYLES:
            raise ValueError(
                f"Invalid per-track style for {track_filename}: {style}. "
                f"Valid options: {', '.join(sorted(VALID_VIDEO_STYLES))}"
            )
        logger.info(
            "Using per-track video style for %s: %s",
            track_filename,
            style,
        )
        return style

    logger.info(
        "No per-track style configured for %s, using global: %s",
        track_filename,
        default_style,
    )
    return default_style


def extract_track_metadata(
    track_path: str,
    pipeline_config: PipelineConfig,
) -> tuple[str, str]:
    """Extract artist and title for a track using the configured fallback chain."""
    track_filename = os.path.basename(track_path)
    track_stem = os.path.splitext(track_filename)[0]

    meta_path = os.path.splitext(track_path)[0] + ".meta.txt"
    if os.path.isfile(meta_path):
        try:
            with open(meta_path, encoding="utf-8") as fh:
                lines = [line.strip() for line in fh.readlines() if line.strip()]
            if len(lines) >= 2:
                artist = re.sub(r"^\d+\s+", "", lines[0]).strip()
                title = re.sub(r"^\d+\s+", "", lines[1]).strip()
                logger.info("Track metadata loaded from sidecar: %s", meta_path)
                return (artist, title)
        except OSError:
            logger.warning("Could not read metadata sidecar: %s", meta_path)

    per_track_metadata = pipeline_config.per_track_metadata or {}
    if track_filename in per_track_metadata:
        meta = per_track_metadata[track_filename]
        artist = meta.get("artist", "").strip()
        title = meta.get("title", "").strip()
        if artist or title:
            logger.info(
                "Track metadata from config for %s: %s — %s",
                track_filename,
                artist,
                title,
            )
            return (artist, title)

    if " - " in track_stem:
        artist, title = (part.strip() for part in track_stem.split(" - ", 1))
        logger.info("Track metadata extracted from filename: %s — %s", artist, title)
        return (artist, title)

    logger.debug("No metadata found for %s, will use empty strings", track_filename)
    return ("", "")
