"""
Unit tests for the structured JSON output service (FEAT-028).
"""

import json
import os
from typing import Any, cast


from src.core.models import (
    AudioAnalysisResult,
    PacingConfig,
    SegmentPlan,
    VideoAnalysisResult,
)
from src.services.json_output import build_json_output, write_json_output

# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


def _audio(**overrides) -> AudioAnalysisResult:
    defaults = {
        "filename": "test_song.wav",
        "bpm": 128.0,
        "duration": 60.0,
        "peaks": [0.5, 0.8, 0.3],
        "beat_times": [i * 0.47 for i in range(128)],
        "intensity_curve": [],
    }
    defaults.update(overrides)
    return AudioAnalysisResult(**cast(dict[str, Any], defaults))


def _segment(idx: int, **overrides) -> SegmentPlan:
    defaults = {
        "video_path": f"/clips/clip_{idx}.mp4",
        "start_time": 0.0,
        "duration": 2.5,
        "timeline_position": idx * 2.5,
        "intensity_level": "medium",
        "speed_factor": 1.0,
        "section_label": "verse",
    }
    defaults.update(overrides)
    return SegmentPlan(**cast(dict[str, Any], defaults))


def _clip(name: str, **overrides) -> VideoAnalysisResult:
    defaults = {
        "path": f"/clips/{name}",
        "intensity_score": 0.5,
        "duration": 10.0,
        "is_vertical": False,
        "thumbnail_data": b"\x00\x01\x02",
    }
    defaults.update(overrides)
    return VideoAnalysisResult(**cast(dict[str, Any], defaults))


def _pacing(**overrides) -> PacingConfig:
    defaults: dict = {}
    defaults.update(overrides)
    return PacingConfig(**cast(dict[str, Any], defaults))


# ------------------------------------------------------------------
# Tests: build_json_output
# ------------------------------------------------------------------


class TestBuildJsonOutput:
    """Tests for the ``build_json_output`` assembler."""

    def test_required_keys(self):
        """Output dict must contain the expected top-level keys."""
        data = build_json_output(_audio(), [_clip("a.mp4")], [_segment(0)], _pacing())
        assert "version" in data
        assert "timestamp" in data
        assert "audio" in data
        assert "clips" in data
        assert "segment_plan" in data
        assert "config" in data

    def test_version_field(self):
        """Version field must match the supplied or default value."""
        data = build_json_output(_audio(), [], None, _pacing(), version="42.0")
        assert data["version"] == "42.0"

    def test_thumbnail_excluded(self):
        """Binary thumbnail_data must be stripped from clips."""
        clip = _clip("a.mp4", thumbnail_data=b"\xff\xd8\xff")
        data = build_json_output(_audio(), [clip], None, _pacing())
        for c in data["clips"]:
            assert "thumbnail_data" not in c

    def test_peaks_excluded(self):
        """Bulky peaks list must be stripped from audio."""
        data = build_json_output(_audio(peaks=[0.1, 0.2, 0.3]), [], None, _pacing())
        assert "peaks" not in data["audio"]

    def test_segment_plan_none(self):
        """Segment plan should be None when no segments are passed."""
        data = build_json_output(_audio(), [], None, _pacing())
        assert data["segment_plan"] is None

    def test_segment_plan_populated(self):
        """Segment plan should contain serialised segments."""
        segments = [_segment(0), _segment(1)]
        data = build_json_output(_audio(), [], segments, _pacing())
        assert len(data["segment_plan"]) == 2
        assert data["segment_plan"][0]["video_path"] == "/clips/clip_0.mp4"

    def test_output_path_included(self):
        """output_path field should appear when provided."""
        data = build_json_output(
            _audio(), [], None, _pacing(), output_path="/out/video.mp4"
        )
        assert data["output_path"] == "/out/video.mp4"

    def test_output_path_absent(self):
        """output_path should not appear when not provided."""
        data = build_json_output(_audio(), [], None, _pacing())
        assert "output_path" not in data

    def test_config_only_non_default(self):
        """Config dict should only contain non-default pacing values."""
        data = build_json_output(
            _audio(), [], None, _pacing(high_intensity_seconds=8.0)
        )
        assert "high_intensity_seconds" in data["config"]

    def test_json_round_trip(self):
        """The output must survive a JSON serialize → deserialize round-trip."""
        data = build_json_output(_audio(), [_clip("b.mp4")], [_segment(0)], _pacing())
        payload = json.dumps(data, default=str)
        restored = json.loads(payload)
        assert restored["version"] == data["version"]


# ------------------------------------------------------------------
# Tests: write_json_output
# ------------------------------------------------------------------


class TestWriteJsonOutput:
    """Tests for the ``write_json_output`` writer."""

    def test_write_to_file(self, tmp_path):
        """Should create a valid JSON file at the given path."""
        outfile = str(tmp_path / "result.json")
        data = build_json_output(_audio(), [], None, _pacing())
        write_json_output(data, outfile)

        assert os.path.isfile(outfile)
        with open(outfile) as f:
            loaded = json.load(f)
        assert loaded["version"] == data["version"]

    def test_write_to_stdout(self, capsys):
        """Should print valid JSON to stdout when target is '-'."""
        data = build_json_output(_audio(), [], None, _pacing())
        write_json_output(data, "-")

        captured = capsys.readouterr().out
        loaded = json.loads(captured)
        assert loaded["version"] == data["version"]

    def test_write_none_is_noop(self, tmp_path):
        """Target=None should be a no-op."""
        data = build_json_output(_audio(), [], None, _pacing())
        write_json_output(data, None)  # Should not raise

    def test_creates_parent_dirs(self, tmp_path):
        """Should auto-create parent directories when writing to file."""
        nested = str(tmp_path / "sub" / "dir" / "out.json")
        data = build_json_output(_audio(), [], None, _pacing())
        write_json_output(data, nested)
        assert os.path.isfile(nested)
