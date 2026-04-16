"""Unit tests for planner tail coverage helpers."""

from src.core.models import (
    AudioAnalysisResult,
    PacingConfig,
    SegmentDecision,
    SegmentPlan,
    VideoAnalysisResult,
)
from src.core.planner.tail_coverage import append_tail_segment


def _clip(path: str, duration: float = 10.0) -> VideoAnalysisResult:
    return VideoAnalysisResult(
        path=path,
        intensity_score=0.2,
        duration=duration,
        is_vertical=False,
        thumbnail_data=None,
    )


def _audio(duration: float = 10.0) -> AudioAnalysisResult:
    return AudioAnalysisResult(
        filename="track.wav",
        bpm=120.0,
        duration=duration,
        peaks=[],
        sections=[],
        beat_times=[0.0, 0.5, 1.0],
        intensity_curve=[0.5, 0.5, 0.5],
    )


def _seg(start: float, duration: float) -> SegmentPlan:
    return SegmentPlan(
        video_path="/videos/base.mp4",
        start_time=0.0,
        duration=duration,
        clip_duration=20.0,
        timeline_position=start,
        intensity_level="medium",
        speed_factor=1.0,
    )


def test_append_tail_segment_adds_tail_when_eligible() -> None:
    segments = [_seg(0.0, 8.0)]
    tail_clip = _clip("/videos/tail.mp4", duration=5.0)

    append_tail_segment(
        segments=segments,
        audio_data=_audio(duration=10.0),
        timeline_pos=8.0,
        config=PacingConfig(min_clip_seconds=1.5),
        pools={"high": [], "medium": [], "low": [tail_clip]},
        pool_indices={"high": 0, "medium": 0, "low": 0},
        sorted_clips=[tail_clip],
        pick_from_pool=lambda pools, indices, level: pools[level][0],
        find_section_label=lambda sections, t: None,
    )

    assert len(segments) == 2
    assert segments[-1].video_path == "/videos/tail.mp4"
    assert segments[-1].duration == 2.0
    assert segments[-1].timeline_position == 8.0


def test_append_tail_segment_skips_when_limited_mode_enabled() -> None:
    segments = [_seg(0.0, 8.0)]
    tail_clip = _clip("/videos/tail.mp4", duration=5.0)

    append_tail_segment(
        segments=segments,
        audio_data=_audio(duration=10.0),
        timeline_pos=8.0,
        config=PacingConfig(max_duration_seconds=10.0),
        pools={"high": [], "medium": [], "low": [tail_clip]},
        pool_indices={"high": 0, "medium": 0, "low": 0},
        sorted_clips=[tail_clip],
        pick_from_pool=lambda pools, indices, level: pools[level][0],
        find_section_label=lambda sections, t: None,
    )

    assert len(segments) == 1


def test_append_tail_segment_records_explain_decision() -> None:
    segments = [_seg(0.0, 8.0)]
    decisions: list[SegmentDecision] = []
    tail_clip = _clip("/videos/tail.mp4", duration=5.0)

    append_tail_segment(
        segments=segments,
        audio_data=_audio(duration=10.0),
        timeline_pos=8.0,
        config=PacingConfig(explain=True),
        pools={"high": [], "medium": [], "low": [tail_clip]},
        pool_indices={"high": 0, "medium": 0, "low": 0},
        sorted_clips=[tail_clip],
        pick_from_pool=lambda pools, indices, level: pools[level][0],
        find_section_label=lambda sections, t: "outro",
        record_decision=decisions.append,
    )

    assert len(segments) == 2
    assert len(decisions) == 1
    assert decisions[0].reason == "Tail coverage: audio after last beat"
