"""Unit tests for the shared single-track application workflow."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.application.story_workflow import build_story_pacing, run_story_workflow
from src.core.models import (
    AudioAnalysisResult,
    PacingConfig,
    SegmentPlan,
    VideoAnalysisResult,
)


def _make_audio_result() -> AudioAnalysisResult:
    return AudioAnalysisResult(
        filename="track.wav",
        bpm=128.0,
        duration=60.0,
        peaks=[5.0, 15.0],
        sections=[],
        beat_times=[0.5, 1.0, 1.5],
        intensity_curve=[0.2, 0.5, 0.8],
    )


def _make_clip(path: str, *, thumbnail_data: bytes | None = b"png") -> VideoAnalysisResult:
    return VideoAnalysisResult(
        path=path,
        intensity_score=0.5,
        duration=8.0,
        is_vertical=False,
        thumbnail_data=thumbnail_data,
        scene_changes=[],
        opening_intensity=0.3,
    )


def _make_segment(path: str) -> SegmentPlan:
    return SegmentPlan(
        video_path=path,
        start_time=0.0,
        duration=4.0,
        timeline_position=0.0,
        intensity_level="medium",
        speed_factor=1.0,
        section_label="intro",
    )


class _Observer:
    def on_progress(self, current: int, total: int, message: str = "") -> None:
        self.last_progress = (current, total, message)


class _ManagedObserver(_Observer):
    def __init__(self, marker: list[str], label: str) -> None:
        self._marker = marker
        self._label = label

    def __enter__(self) -> _ManagedObserver:
        self._marker.append(f"enter:{self._label}")
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self._marker.append(f"exit:{self._label}")


def test_build_story_pacing_merges_runtime_overrides(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.application.story_workflow.build_pacing_config",
        lambda overrides=None: PacingConfig(
            video_style=(overrides or {}).get("video_style", "bw"),
            max_clips=3,
            max_duration_seconds=(overrides or {}).get("max_duration_seconds"),
        ),
    )

    pacing = build_story_pacing({"video_style": "warm", "max_duration_seconds": 30.0})

    assert pacing.video_style == "warm"
    assert pacing.max_clips == 3
    assert pacing.max_duration_seconds == 30.0


def test_run_story_workflow_returns_plan_report_for_dry_run(
    monkeypatch, tmp_path
) -> None:
    audio_meta = _make_audio_result()
    clip = _make_clip("/videos/clip.mp4")
    broll_clip = _make_clip("/videos/broll/bg.mp4")
    segment = _make_segment(clip.path)
    broll_dir = tmp_path / "broll"
    broll_dir.mkdir()

    monkeypatch.setattr(
        "src.application.story_workflow.analyze_audio",
        lambda path: ("resolved.wav", audio_meta),
    )
    monkeypatch.setattr(
        "src.application.story_workflow.detect_broll_dir",
        lambda video_dir, explicit: str(broll_dir),
    )
    monkeypatch.setattr(
        "src.application.story_workflow.build_pacing_config",
        lambda overrides=None: PacingConfig(dry_run=True),
    )
    monkeypatch.setattr(
        "src.application.story_workflow.format_plan_report",
        lambda audio, segments, clips, pacing: "PLAN REPORT",
    )

    engine = MagicMock()
    engine.scan_video_library.side_effect = [[clip], [broll_clip]]
    engine.plan_story.return_value = [segment]

    result = run_story_workflow(
        "input.wav",
        "/videos",
        "output.mp4",
        broll_dir=str(broll_dir),
        engine=engine,
    )

    assert result.plan_report == "PLAN REPORT"
    assert result.output_path is None
    assert result.segments == [segment]
    assert result.video_clips == [clip]
    assert result.broll_clips == [broll_clip]
    assert result.montage_clips[0].thumbnail_data is None
    engine.generate_story.assert_not_called()


def test_run_story_workflow_renders_with_observer_factories(monkeypatch) -> None:
    audio_meta = _make_audio_result()
    clip = _make_clip("/videos/clip.mp4")
    observer_events: list[str] = []

    monkeypatch.setattr(
        "src.application.story_workflow.analyze_audio",
        lambda path: ("resolved.wav", audio_meta),
    )
    monkeypatch.setattr(
        "src.application.story_workflow.detect_broll_dir",
        lambda video_dir, explicit: None,
    )
    monkeypatch.setattr(
        "src.application.story_workflow.build_pacing_config",
        lambda overrides=None: PacingConfig(
            video_style=(overrides or {}).get("video_style", "golden")
        ),
    )

    engine = MagicMock()
    engine.scan_video_library.return_value = [clip]
    engine.generate_story.return_value = "rendered.mp4"

    result = run_story_workflow(
        "input.wav",
        "/videos",
        "output.mp4",
        pacing_overrides={"video_style": "warm"},
        engine=engine,
        scan_observer_factory=lambda: _ManagedObserver(observer_events, "scan"),
        render_observer_factory=lambda: _ManagedObserver(observer_events, "render"),
    )

    assert result.plan_report is None
    assert result.output_path == "rendered.mp4"
    assert result.pacing.video_style == "warm"
    assert observer_events == [
        "enter:scan",
        "exit:scan",
        "enter:render",
        "exit:render",
    ]
    engine.generate_story.assert_called_once()
