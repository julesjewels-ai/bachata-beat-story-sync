from __future__ import annotations

import json
from pathlib import Path

from src.application import batch_bridge


class DummyMeta:
    def model_dump(self) -> dict:
        return {"filename": "song.mp3", "bpm": 120.0, "duration": 60.0}


class DummyClip:
    def __init__(self, path: str) -> None:
        self.path = path

    def model_dump(self) -> dict:
        return {"path": self.path, "intensity_score": 0.5, "duration": 5.0}

    def model_copy(self, update=None):
        data = self.model_dump()
        if update:
            data.update(update)
        copied = DummyClip(self.path)
        copied.__dict__.update(data)
        return copied


class DummySegment:
    def __init__(self, video_path: str) -> None:
        self.video_path = video_path

    def model_dump(self) -> dict:
        return {
            "video_path": self.video_path,
            "start_time": 0.0,
            "duration": 1.0,
            "timeline_position": 0.0,
            "intensity_level": "medium",
            "speed_factor": 1.0,
            "section_label": "intro",
        }


class DummyEngine:
    def scan_video_library(self, directory, exclude_dirs=None):
        return [DummyClip(str(Path(directory) / "clip.mp4"))]

    def plan_story(self, audio_meta, clips, pacing=None):
        return [DummySegment(clips[0].path)]

    def generate_story(
        self,
        audio_meta,
        clips,
        output_path,
        broll_clips=None,
        audio_path=None,
        pacing=None,
    ):
        Path(output_path).write_text("video", encoding="utf-8")
        return output_path


def test_plan_song_from_batch(monkeypatch, tmp_path: Path) -> None:
    batch_path = tmp_path / "batch.json"
    batch = {
        "batch_id": "batch-1",
        "songs": [
            {
                "song_id": "song-1",
                "audio": {"asset_path": "audio/song.mp3"},
                "video": {"audio_path": "", "clips_path": "", "output_path": ""},
            }
        ],
    }
    batch_path.write_text(json.dumps(batch), encoding="utf-8")
    monkeypatch.setattr(batch_bridge, "_analyze_audio", lambda path: (path, DummyMeta()))

    segments = batch_bridge.plan_song_from_batch(
        batch_path=batch_path,
        song_id="song-1",
        video_dir=str(tmp_path / "clips"),
        engine=DummyEngine(),
    )

    assert segments[0]["video_path"].endswith("clip.mp4")


def test_render_song_from_batch_updates_json(monkeypatch, tmp_path: Path) -> None:
    batch_path = tmp_path / "batch.json"
    batch = {
        "batch_id": "batch-1",
        "updated_at": "",
        "songs": [
            {
                "song_id": "song-1",
                "audio": {"asset_path": "audio/song.mp3"},
                "video": {"audio_path": "", "clips_path": "", "output_path": ""},
            }
        ],
    }
    batch_path.write_text(json.dumps(batch), encoding="utf-8")
    monkeypatch.setattr(batch_bridge, "_analyze_audio", lambda path: (path, DummyMeta()))

    result = batch_bridge.render_song_from_batch(
        batch_path=batch_path,
        song_id="song-1",
        video_dir=str(tmp_path / "clips"),
        output_path=str(tmp_path / "out.mp4"),
        engine=DummyEngine(),
    )

    assert result["output_path"].endswith("out.mp4")
    saved = json.loads(batch_path.read_text(encoding="utf-8"))
    assert saved["songs"][0]["video"]["status"] == "done"
    assert saved["songs"][0]["video"]["output_path"].endswith("out.mp4")
