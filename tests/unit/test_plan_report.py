"""
Unit tests for the dry-run plan report formatter (FEAT-026).
"""

import os

from src.core.models import (
    AudioAnalysisResult,
    PacingConfig,
    SegmentPlan,
    VideoAnalysisResult,
)
from src.services.plan_report import format_plan_report, write_plan_report

# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


def _audio(**overrides) -> AudioAnalysisResult:
    defaults = {
        "filename": "test_song.wav",
        "bpm": 128.0,
        "duration": 60.0,
        "peaks": [],
        "beat_times": [i * 0.47 for i in range(128)],
        "intensity_curve": [],
    }
    defaults.update(overrides)
    return AudioAnalysisResult(**defaults)


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
    return SegmentPlan(**defaults)


def _clip(name: str, **overrides) -> VideoAnalysisResult:
    defaults = {
        "path": f"/clips/{name}",
        "intensity_score": 0.5,
        "duration": 10.0,
        "is_vertical": False,
    }
    defaults.update(overrides)
    return VideoAnalysisResult(**defaults)


def _pacing(**overrides) -> PacingConfig:
    defaults = {"dry_run": True}
    defaults.update(overrides)
    return PacingConfig(**defaults)


# ------------------------------------------------------------------
# format_plan_report
# ------------------------------------------------------------------


class TestFormatPlanReport:
    def test_header_present(self):
        report = format_plan_report(_audio(), [], [], _pacing())
        assert report.startswith("DRY RUN")

    def test_footer_present(self):
        report = format_plan_report(_audio(), [], [], _pacing())
        assert "Run without --dry-run to render." in report

    def test_audio_summary(self):
        report = format_plan_report(
            _audio(bpm=128.0, duration=222.0, filename="song.wav"),
            [],
            [],
            _pacing(),
        )
        assert "song.wav" in report
        assert "128 BPM" in report

    def test_beat_count(self):
        audio = _audio(beat_times=[0.0, 0.5, 1.0])
        report = format_plan_report(audio, [], [], _pacing())
        assert "3 beats" in report

    def test_clip_stats(self):
        clips = [_clip("a.mp4"), _clip("b.mp4"), _clip("c.mp4")]
        segments = [
            _segment(0, video_path="/clips/a.mp4"),
            _segment(1, video_path="/clips/b.mp4"),
        ]
        report = format_plan_report(_audio(), segments, clips, _pacing())
        assert "3 analyzed" in report
        assert "2 used" in report
        assert "1 unused" in report

    def test_segment_table_rows(self):
        segments = [_segment(0), _segment(1)]
        report = format_plan_report(_audio(), segments, [], _pacing())
        assert "#001" in report
        assert "#002" in report
        assert "clip_0.mp4" in report
        assert "clip_1.mp4" in report

    def test_estimated_output_duration(self):
        segments = [
            _segment(0, timeline_position=0.0, duration=3.0),
            _segment(1, timeline_position=3.0, duration=2.0),
        ]
        report = format_plan_report(_audio(), segments, [], _pacing())
        # 3.0 + 2.0 = 5.0s → 00:05.0
        assert "00:05.0" in report

    def test_empty_plan(self):
        report = format_plan_report(_audio(), [], [], _pacing())
        assert "0 segments" in report
        assert "no segments" in report

    def test_config_summary(self):
        pacing = _pacing(video_style="warm", max_clips=10)
        report = format_plan_report(_audio(), [], [], pacing)
        assert "video_style=warm" in report
        assert "max_clips=10" in report

    def test_speed_factor_shown(self):
        segments = [_segment(0, speed_factor=1.3)]
        report = format_plan_report(_audio(), segments, [], _pacing())
        assert "1.3x" in report


# ------------------------------------------------------------------
# write_plan_report
# ------------------------------------------------------------------


class TestWritePlanReport:
    def test_write_to_file(self, tmp_path):
        out = str(tmp_path / "plan.txt")
        write_plan_report("hello world", output_path=out)
        assert os.path.exists(out)
        with open(out) as f:
            assert f.read().strip() == "hello world"

    def test_write_creates_directories(self, tmp_path):
        out = str(tmp_path / "sub" / "dir" / "plan.txt")
        write_plan_report("nested", output_path=out)
        assert os.path.exists(out)

    def test_stdout_mode(self, capsys):
        write_plan_report("stdout test")
        captured = capsys.readouterr()
        assert "stdout test" in captured.out
