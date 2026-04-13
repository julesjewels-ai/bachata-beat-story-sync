"""MCP server entry point for bachata-beat-story-sync.

Exposes the video automation pipeline as MCP tools and resources so AI agents
(Claude Desktop, IDE extensions) can programmatically control audio analysis,
video scanning, montage planning, and rendering.

Usage:
    venv/bin/python mcp_server.py        # start server (stdio transport)
    mcp run mcp_server.py                # MCP inspector / interactive test

Add to Claude Desktop config (~/Library/Application Support/Claude/claude_desktop_config.json):
    See mcp_config.json at the project root.
"""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from src.config.app_config import build_pacing_config, load_app_config
from src.cli_utils import analyze_audio as _analyze_audio
from src.cli_utils import detect_broll_dir, strip_thumbnails
from src.core.app import BachataSyncEngine
from src.core.models import PacingConfig

# ---------------------------------------------------------------------------
# Server & shared state
# ---------------------------------------------------------------------------

mcp = FastMCP("bachata-sync")
engine = BachataSyncEngine()

# In-memory session state — reset on server restart (no persistence needed).
_state: dict[str, Any] = {
    "latest_audio": None,   # serialized AudioAnalysisResult dict
    "latest_videos": None,  # list of serialized VideoAnalysisResult dicts
    "config_overrides": {}, # user-applied PacingConfig overrides for this session
}


def _build_pacing(config_overrides: dict | None) -> PacingConfig:
    """Merge YAML base config + session overrides + call-level overrides."""
    merged = {**_state["config_overrides"], **(config_overrides or {})}
    return build_pacing_config(merged)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def analyze_audio(audio_path: str) -> dict:
    """Analyze an audio file and return beat/rhythm metadata.

    Args:
        audio_path: Absolute path to a .wav or .mp3 audio file.

    Returns:
        Dict with keys: filename, bpm, duration, peaks, sections,
        beat_times, intensity_curve.
    """
    _resolved, audio_meta = _analyze_audio(audio_path)
    result = audio_meta.model_dump()
    _state["latest_audio"] = result
    return result


@mcp.tool()
def scan_videos(video_dir: str, broll_dir: str | None = None) -> list[dict]:
    """Scan a directory for video clips and score their motion intensity.

    Args:
        video_dir: Absolute path to directory containing .mp4 clips.
        broll_dir: Optional absolute path to a B-roll subdirectory. If omitted,
            a 'broll/' subfolder inside video_dir is auto-detected.

    Returns:
        List of dicts with keys: path, intensity_score, duration, is_vertical,
        scene_changes, opening_intensity. (thumbnail_data is excluded.)
    """
    resolved_broll = detect_broll_dir(video_dir, broll_dir)
    exclude_dirs = [resolved_broll] if resolved_broll else None
    clips = engine.scan_video_library(video_dir, exclude_dirs=exclude_dirs)
    clips = strip_thumbnails(clips)
    result = [c.model_dump() for c in clips]
    _state["latest_videos"] = result
    return result


@mcp.tool()
def plan_montage(
    audio_path: str,
    video_dir: str,
    config_overrides: dict | None = None,
) -> list[dict]:
    """Plan a beat-synced clip sequence without rendering.

    Analyzes the audio and video library, then returns a segment timeline
    showing which clip plays at which time and for how long.

    Args:
        audio_path: Absolute path to a .wav or .mp3 audio file.
        video_dir: Absolute path to directory containing .mp4 clips.
        config_overrides: Optional dict of PacingConfig field overrides
            (e.g. {"video_style": "warm", "broll_interval_seconds": 10}).

    Returns:
        List of segment plan dicts with keys: video_path, start_time,
        duration, timeline_position, intensity_level, speed_factor,
        section_label.
    """
    _resolved, audio_meta = _analyze_audio(audio_path)
    _state["latest_audio"] = audio_meta.model_dump()

    resolved_broll = detect_broll_dir(video_dir, None)
    exclude_dirs = [resolved_broll] if resolved_broll else None
    clips = engine.scan_video_library(video_dir, exclude_dirs=exclude_dirs)
    clips = strip_thumbnails(clips)
    _state["latest_videos"] = [c.model_dump() for c in clips]

    pacing = _build_pacing(config_overrides)
    segments = engine.plan_story(audio_meta, clips, pacing=pacing)
    return [s.model_dump() for s in segments]


@mcp.tool()
def render_montage(
    audio_path: str,
    video_dir: str,
    output_path: str,
    config_overrides: dict | None = None,
) -> dict:
    """Render a beat-synced video montage to disk.

    Analyzes the audio and video library, sequences clips to match the
    musical dynamics, and runs FFmpeg to produce the output file.

    Args:
        audio_path: Absolute path to a .wav or .mp3 audio file.
        video_dir: Absolute path to directory containing .mp4 clips.
        output_path: Absolute path for the output .mp4 file.
        config_overrides: Optional dict of PacingConfig field overrides
            (e.g. {"video_style": "golden", "pacing_drift_zoom": true}).

    Returns:
        Dict with keys: output_path (str), status ("success").
    """
    resolved_audio, audio_meta = _analyze_audio(audio_path)
    _state["latest_audio"] = audio_meta.model_dump()

    resolved_broll = detect_broll_dir(video_dir, None)
    exclude_dirs = [resolved_broll] if resolved_broll else None
    clips = engine.scan_video_library(video_dir, exclude_dirs=exclude_dirs)

    broll_clips = None
    if resolved_broll:
        broll_clips = engine.scan_video_library(resolved_broll)

    clips = strip_thumbnails(clips)
    _state["latest_videos"] = [c.model_dump() for c in clips]

    pacing = _build_pacing(config_overrides)
    result_path = engine.generate_story(
        audio_meta,
        clips,
        output_path,
        broll_clips=broll_clips,
        audio_path=resolved_audio,
        pacing=pacing,
    )
    return {"output_path": result_path, "status": "success"}


@mcp.tool()
def get_config() -> dict:
    """Return the current PacingConfig (YAML base merged with session overrides).

    Returns:
        Dict of all PacingConfig fields and their current values.
    """
    base = load_app_config().pacing.model_dump()
    return {**base, **_state["config_overrides"]}


@mcp.tool()
def update_config(overrides: dict) -> dict:
    """Apply PacingConfig overrides for this session (does not write to disk).

    Merges the supplied overrides into the session state. Pass only the fields
    you want to change — other fields keep their current values.

    Args:
        overrides: Dict of PacingConfig field names to new values.
            Example: {"video_style": "bw", "broll_interval_seconds": 10.0}

    Returns:
        The full merged config dict after applying the overrides.
    """
    base = load_app_config().pacing.model_dump()
    candidate = {**base, **_state["config_overrides"], **overrides}
    # Validate by constructing a PacingConfig — raises ValidationError on bad input.
    PacingConfig(**candidate)
    _state["config_overrides"].update(overrides)
    return candidate


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------

@mcp.resource("resource://config/pacing", mime_type="application/json")
def config_pacing() -> str:
    """Current pacing configuration (montage_config.yaml + session overrides)."""
    base = load_app_config().pacing.model_dump()
    merged = {**base, **_state["config_overrides"]}
    return json.dumps(merged, indent=2)


@mcp.resource("resource://analysis/latest", mime_type="application/json")
def analysis_latest() -> str:
    """Most recent audio and video analysis results from this session."""
    if _state["latest_audio"] is None and _state["latest_videos"] is None:
        return json.dumps({
            "message": "No analysis has been run yet. Call analyze_audio or scan_videos first."
        })
    return json.dumps(
        {
            "audio": _state["latest_audio"],
            "videos": _state["latest_videos"],
        },
        indent=2,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
