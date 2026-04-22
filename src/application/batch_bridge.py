from __future__ import annotations

import json
import os
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.cli_utils import detect_broll_dir, strip_thumbnails
from src.config.app_config import build_pacing_config
from src.core.app import BachataSyncEngine
from src.cli_utils import analyze_audio as _analyze_audio


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def load_batch(batch_path: str | os.PathLike[str]) -> dict[str, Any]:
    with Path(batch_path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_batch(batch_path: str | os.PathLike[str], batch: dict[str, Any]) -> None:
    path = Path(batch_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(batch, handle, ensure_ascii=False, indent=2)


def resolve_batch_paths(
    batch: dict[str, Any],
    batch_dir: str | os.PathLike[str],
) -> dict[str, Any]:
    root = Path(batch_dir)
    result = deepcopy(batch)
    for song in result.get("songs", []):
        audio = song.get("audio", {})
        video = song.get("video", {})

        for key in ("asset_path",):
            value = audio.get(key, "")
            if value and not os.path.isabs(value):
                audio[key] = str(root / value)

        for key in ("audio_path", "clips_path", "output_path"):
            value = video.get(key, "")
            if value and not os.path.isabs(value):
                video[key] = str(root / value)

    return result


def _song_by_id(batch: dict[str, Any], song_id: str) -> dict[str, Any]:
    for song in batch.get("songs", []):
        if song.get("song_id") == song_id:
            return song
    raise KeyError(f"song_id not found: {song_id}")


def _maybe_relpath(path_value: str, batch_dir: Path) -> str:
    if not path_value:
        return path_value
    try:
        candidate = Path(path_value)
        if candidate.is_absolute():
            return os.path.relpath(candidate, batch_dir)
    except Exception:
        return path_value
    return path_value


def _build_engine() -> BachataSyncEngine:
    return BachataSyncEngine()


def plan_song_from_batch(
    batch_path: str | os.PathLike[str],
    song_id: str,
    video_dir: str,
    config_overrides: dict | None = None,
    engine: BachataSyncEngine | None = None,
) -> list[dict[str, Any]]:
    batch = resolve_batch_paths(load_batch(batch_path), Path(batch_path).parent)
    song = _song_by_id(batch, song_id)
    audio_path = song.get("video", {}).get("audio_path") or song.get("audio", {}).get(
        "asset_path", ""
    )
    if not audio_path:
        raise ValueError(f"song {song_id} has no audio path")

    _resolved_audio, audio_meta = _analyze_audio(audio_path)
    local_engine = engine or _build_engine()

    resolved_broll = detect_broll_dir(video_dir, None)
    exclude_dirs = [resolved_broll] if resolved_broll else None
    clips = local_engine.scan_video_library(video_dir, exclude_dirs=exclude_dirs)
    clips = strip_thumbnails(clips)

    pacing = build_pacing_config(config_overrides or {})
    segments = local_engine.plan_story(audio_meta, clips, pacing=pacing)
    return [segment.model_dump() for segment in segments]


def render_song_from_batch(
    batch_path: str | os.PathLike[str],
    song_id: str,
    video_dir: str,
    output_path: str,
    config_overrides: dict | None = None,
    engine: BachataSyncEngine | None = None,
) -> dict[str, Any]:
    batch_file = Path(batch_path)
    raw_batch = load_batch(batch_file)
    batch = resolve_batch_paths(raw_batch, batch_file.parent)
    song = _song_by_id(batch, song_id)
    raw_song = _song_by_id(raw_batch, song_id)
    audio_path = song.get("video", {}).get("audio_path") or song.get("audio", {}).get(
        "asset_path", ""
    )
    if not audio_path:
        raise ValueError(f"song {song_id} has no audio path")

    _resolved_audio, audio_meta = _analyze_audio(audio_path)
    local_engine = engine or _build_engine()

    resolved_broll = detect_broll_dir(video_dir, None)
    exclude_dirs = [resolved_broll] if resolved_broll else None
    clips = local_engine.scan_video_library(video_dir, exclude_dirs=exclude_dirs)
    clips = strip_thumbnails(clips)

    broll_clips = None
    if resolved_broll:
        broll_clips = local_engine.scan_video_library(resolved_broll)

    pacing = build_pacing_config(config_overrides or {})
    result_path = local_engine.generate_story(
        audio_meta,
        clips,
        output_path,
        broll_clips=broll_clips,
        audio_path=audio_path,
        pacing=pacing,
    )

    raw_song.setdefault("video", {})
    raw_song["video"].update(
        {
            "status": "done",
            "audio_path": raw_song.get("audio", {}).get("asset_path", audio_path),
            "clips_path": _maybe_relpath(video_dir, batch_file.parent),
            "output_path": _maybe_relpath(result_path, batch_file.parent),
            "updated_at": utc_now(),
        }
    )
    raw_batch["updated_at"] = utc_now()
    save_batch(batch_file, raw_batch)
    return {"output_path": result_path, "batch": raw_batch}
