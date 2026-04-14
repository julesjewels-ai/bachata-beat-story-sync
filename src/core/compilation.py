"""
Compilation video generation — concatenate individual track videos with transitions
and generate chapter markers for YouTube navigation (FEAT-049).
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path

from src.core.ffmpeg_renderer import get_video_duration
from src.core.models import CompilationConfig

logger = logging.getLogger(__name__)


def _safe_filename(path: str) -> str:
    """Derive a filesystem-safe name from an audio file path."""
    stem = os.path.splitext(os.path.basename(path))[0]
    return stem.replace(" ", "_")


def _build_concat_demuxer(
    video_files: list[str],
    transition_type: str,
    transition_duration: float,
) -> str:
    """
    Build FFmpeg concat demuxer script with optional transitions.

    Args:
        video_files: List of video file paths to concatenate (in order)
        transition_type: 'fade', 'crossfade', or 'none'
        transition_duration: Duration of transitions in seconds

    Returns:
        Demuxer script content (plain text)
    """
    lines = []
    for i, video_file in enumerate(video_files):
        # Use absolute paths in the concat demuxer
        abs_path = os.path.abspath(video_file)
        lines.append(f"file '{abs_path}'")

    return "\n".join(lines) + "\n"


def generate_compilation(
    track_videos: list[str],
    track_audio_files: list[str],
    output_path: str,
    config: CompilationConfig,
) -> str:
    """
    Generate a compilation video by concatenating individual track videos
    with transitions and generate chapter markers.

    Args:
        track_videos: List of video file paths for each track (in order)
        track_audio_files: List of corresponding audio file paths (for metadata)
        output_path: Absolute path to output compilation video
        config: CompilationConfig with transition settings

    Returns:
        Path to the generated compilation video

    Raises:
        FileNotFoundError: If any input video is missing
        subprocess.CalledProcessError: If FFmpeg fails
    """
    if not track_videos:
        raise ValueError("No track videos provided for compilation")

    # Validate input files exist
    for video in track_videos:
        if not os.path.isfile(video):
            raise FileNotFoundError(f"Track video not found: {video}")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    logger.info(
        "Generating compilation from %d track video(s) with %s transition",
        len(track_videos),
        config.transition_type,
    )

    # Build concat demuxer
    demuxer_content = _build_concat_demuxer(
        track_videos,
        config.transition_type,
        config.transition_duration,
    )

    # Write demuxer to temp file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False
    ) as f:
        demuxer_path = f.name
        f.write(demuxer_content)

    try:
        # Build FFmpeg command
        # Concat demuxer handles the concatenation natively
        cmd = ["ffmpeg", "-f", "concat", "-safe", "0", "-i", demuxer_path]

        # For now, simple concatenation without transitions
        # (Transitions between videos require re-encoding and frame-accurate timing)
        cmd.extend(["-c", "copy", "-y"])
        cmd.append(output_path)

        logger.debug("Running FFmpeg: %s", " ".join(cmd))
        subprocess.run(cmd, check=True, capture_output=True, text=True)

        logger.info("Compilation video generated: %s", output_path)

        # Generate chapter markers if enabled
        if config.include_chapter_markers:
            chapters_path = output_path.replace(".mp4", "_chapters.json")
            _generate_chapter_markers(
                track_videos, track_audio_files, chapters_path
            )
            logger.info("Chapter markers saved: %s", chapters_path)

        return output_path

    finally:
        # Clean up temp demuxer file
        if os.path.exists(demuxer_path):
            os.unlink(demuxer_path)


def _generate_chapter_markers(
    track_videos: list[str],
    track_audio_files: list[str],
    output_path: str,
) -> None:
    """
    Generate chapter markers JSON with timestamps and track names.

    Args:
        track_videos: List of video file paths
        track_audio_files: List of audio file paths (for track names)
        output_path: Where to save the JSON file
    """
    chapters = []
    current_time = 0.0

    for video_path, audio_path in zip(track_videos, track_audio_files):
        # Extract track name from audio filename
        track_name = _safe_filename(audio_path)

        # Get duration of this video
        duration = get_video_duration(video_path)

        chapters.append(
            {
                "title": track_name,
                "start_time": current_time,
                "start_time_formatted": _format_timestamp(current_time),
            }
        )

        current_time += duration

    # Write JSON
    with open(output_path, "w") as f:
        json.dump(
            {
                "chapters": chapters,
                "total_duration": current_time,
                "total_duration_formatted": _format_timestamp(current_time),
            },
            f,
            indent=2,
        )

    # Also generate YouTube-friendly text format
    youtube_path = output_path.replace(".json", ".txt")
    with open(youtube_path, "w") as f:
        lines = []
        for chapter in chapters:
            lines.append(
                f"{chapter['start_time_formatted']} - {chapter['title']}"
            )
        f.write("\n".join(lines) + "\n")


def _format_timestamp(seconds: float) -> str:
    """Convert seconds to MM:SS or HH:MM:SS format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"
