"""Unit tests for segment-plan validation helpers."""

from src.core.models import SegmentPlan
from src.core.plan_validation import validate_segment_plan


def _seg(start: float, duration: float) -> SegmentPlan:
    return SegmentPlan(
        video_path="/videos/test.mp4",
        start_time=0.0,
        duration=duration,
        clip_duration=30.0,
        timeline_position=start,
        intensity_level="medium",
        speed_factor=1.0,
    )


def test_validate_segment_plan_accepts_contiguous_plan() -> None:
    result = validate_segment_plan(
        [_seg(0.0, 2.0), _seg(2.0, 2.0), _seg(4.0, 2.0)],
        expected_duration=6.0,
        min_clip_seconds=1.5,
    )
    assert result.is_valid
    assert result.issues == []
    assert result.alignment_status == "ok"
    assert result.duration_delta_seconds == 0.0
    assert result.absolute_delta_seconds == 0.0


def test_validate_segment_plan_detects_gap() -> None:
    result = validate_segment_plan(
        [_seg(0.0, 2.0), _seg(2.4, 2.0)],
        expected_duration=4.4,
        min_clip_seconds=1.5,
    )
    assert not result.is_valid
    assert any("Gap before segment 2" in msg for msg in result.issues)


def test_validate_segment_plan_detects_overlap() -> None:
    result = validate_segment_plan(
        [_seg(0.0, 2.0), _seg(1.7, 2.0)],
        expected_duration=3.7,
        min_clip_seconds=1.5,
    )
    assert not result.is_valid
    assert any("Overlap before segment 2" in msg for msg in result.issues)


def test_validate_segment_plan_detects_min_clip_violation() -> None:
    result = validate_segment_plan(
        [_seg(0.0, 1.2), _seg(1.2, 2.0)],
        expected_duration=3.2,
        min_clip_seconds=1.5,
    )
    assert not result.is_valid
    assert any("below min_clip_seconds" in msg for msg in result.issues)


def test_validate_segment_plan_detects_coverage_gap() -> None:
    result = validate_segment_plan(
        [_seg(0.0, 2.0), _seg(2.0, 2.0)],
        expected_duration=6.0,
        min_clip_seconds=1.5,
    )
    assert not result.is_valid
    assert any("under-covers target duration" in msg for msg in result.issues)
    assert result.alignment_status == "under"
    assert result.duration_delta_seconds < 0


def test_validate_segment_plan_detects_over_coverage() -> None:
    result = validate_segment_plan(
        [_seg(0.0, 2.0), _seg(2.0, 2.0), _seg(4.0, 2.5)],
        expected_duration=6.0,
        min_clip_seconds=1.5,
    )
    assert not result.is_valid
    assert any("over-covers target duration" in msg for msg in result.issues)
    assert result.alignment_status == "over"
    assert result.duration_delta_seconds > 0
