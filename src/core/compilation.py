"""
Compilation video generation — concatenate individual track videos with transitions
and generate chapter markers for YouTube navigation (FEAT-049).
"""

from __future__ import annotations

import json
import logging
import os
import tempfile

from src.core.ffmpeg_renderer import get_video_duration
from src.core.ffmpeg_utils import get_h264_encoder_args, run_ffmpeg
from src.core.models import CompilationConfig

logger = logging.getLogger(__name__)


def _safe_filename(path: str) -> str:
    """Derive a filesystem-safe name from an audio file path."""
    stem = os.path.splitext(os.path.basename(path))[0]
    return stem.replace(" ", "_")


def _concat_copy(video_files: list[str], output_path: str) -> None:
    """Fast stream-copy concatenation with no transitions."""
    lines = [f"file '{os.path.abspath(f)}'" for f in video_files]
    demuxer_content = "\n".join(lines) + "\n"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        demuxer_path = f.name
        f.write(demuxer_content)

    try:
        cmd = [
            "ffmpeg", "-f", "concat", "-safe", "0",
            "-i", demuxer_path,
            "-c", "copy", "-y",
            output_path,
        ]
        run_ffmpeg(cmd, "compilation concat")
    finally:
        if os.path.exists(demuxer_path):
            os.unlink(demuxer_path)


def _bake_fades(
    input_path: str,
    output_path: str,
    duration: float,
    fade_duration: float,
    fade_in: bool,
    fade_out: bool,
) -> None:
    """
    Re-encode a track video with audio/video fades at the start and/or end.

    Preserves full duration — fades are applied in-place, not by trimming.
    """
    video_filters = []
    audio_filters = []

    if fade_in:
        video_filters.append(f"fade=t=in:st=0:d={fade_duration:.3f}")
        audio_filters.append(f"afade=t=in:st=0:d={fade_duration:.3f}")

    if fade_out:
        fade_start = max(0.0, duration - fade_duration)
        video_filters.append(f"fade=t=out:st={fade_start:.3f}:d={fade_duration:.3f}")
        audio_filters.append(f"afade=t=out:st={fade_start:.3f}:d={fade_duration:.3f}")

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vf", ",".join(video_filters),
        "-af", ",".join(audio_filters),
        *get_h264_encoder_args(),
        "-c:a", "aac", "-b:a", "192k",
        output_path,
    ]
    run_ffmpeg(cmd, f"bake fades into {os.path.basename(input_path)}")


def _apply_transitions_with_audio(
    video_files: list[str],
    output_path: str,
    transition_duration: float,
    temp_dir: str,
) -> None:
    """
    Concatenate track videos with non-overlapping fades at each boundary.

    Every track plays in full — no audio or video is cut. Each track gets:
      - fade-in on its leading ``transition_duration`` seconds (except the first)
      - fade-out on its trailing ``transition_duration`` seconds (except the last)

    Then all processed tracks are concatenated with stream copy. Total duration
    equals the exact sum of the input track durations.
    """
    faded_files: list[str] = []
    for i, video_file in enumerate(video_files):
        duration = get_video_duration(video_file)
        faded_path = os.path.join(temp_dir, f"faded_{i:04d}.mp4")
        _bake_fades(
            input_path=video_file,
            output_path=faded_path,
            duration=duration,
            fade_duration=transition_duration,
            fade_in=i > 0,
            fade_out=i < len(video_files) - 1,
        )
        faded_files.append(faded_path)

    _concat_copy(faded_files, output_path)


def generate_compilation(
    track_videos: list[str],
    track_audio_files: list[str],
    output_path: str,
    config: CompilationConfig,
) -> str:
    """
    Generate a compilation video by concatenating individual track videos
    with transitions and generate chapter markers.

    When transition_type is 'fade' or 'crossfade', applies xfade (video) +
    acrossfade (audio) at each track boundary. When 'none', uses fast stream copy.

    Args:
        track_videos: List of video file paths for each track (in order)
        track_audio_files: List of corresponding audio file paths (for metadata)
        output_path: Absolute path to output compilation video
        config: CompilationConfig with transition settings

    Returns:
        Path to the generated compilation video

    Raises:
        FileNotFoundError: If any input video is missing
        RuntimeError: If FFmpeg fails
    """
    if not track_videos:
        raise ValueError("No track videos provided for compilation")

    for video in track_videos:
        if not os.path.isfile(video):
            raise FileNotFoundError(f"Track video not found: {video}")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    logger.info(
        "Generating compilation from %d track video(s) with %s transition (%.2fs)",
        len(track_videos),
        config.transition_type,
        config.transition_duration,
    )

    use_transitions = (
        config.transition_type != "none"
        and len(track_videos) > 1
        and config.transition_duration > 0
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        if use_transitions:
            _apply_transitions_with_audio(
                track_videos,
                output_path,
                config.transition_duration,
                temp_dir,
            )
        else:
            _concat_copy(track_videos, output_path)

    logger.info("Compilation video generated: %s", output_path)

    if config.include_chapter_markers:
        chapters_path = output_path.replace(".mp4", "_chapters.json")
        _generate_chapter_markers(track_videos, track_audio_files, chapters_path)
        logger.info("Chapter markers saved: %s", chapters_path)

    return output_path


def _generate_chapter_markers(
    track_videos: list[str],
    track_audio_files: list[str],
    output_path: str,
) -> None:
    """
    Generate chapter markers JSON with timestamps and track names.

    Fades are baked in-place (no overlap), so each track's start time is simply
    the cumulative sum of prior track durations.
    """
    chapters = []
    current_time = 0.0

    for video_path, audio_path in zip(track_videos, track_audio_files):
        track_name = _safe_filename(audio_path)
        duration = get_video_duration(video_path)

        chapters.append(
            {
                "title": track_name,
                "start_time": current_time,
                "start_time_formatted": _format_timestamp(current_time),
            }
        )

        current_time += duration

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

    youtube_path = output_path.replace(".json", ".txt")
    with open(youtube_path, "w") as f:
        lines = [
            f"{chapter['start_time_formatted']} - {chapter['title']}"
            for chapter in chapters
        ]
        f.write("\n".join(lines) + "\n")


def _format_timestamp(seconds: float) -> str:
    """Convert seconds to MM:SS or HH:MM:SS format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"
