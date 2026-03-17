from collections.abc import Callable
from typing import Any

import pytest
from src.core.models import (
    AudioAnalysisResult,
    PacingConfig,
    SegmentPlan,
    VideoAnalysisResult,
)
from src.core.montage import MontageGenerator


@pytest.fixture
def generator() -> MontageGenerator:
    return MontageGenerator()


@pytest.fixture
def audio_data() -> AudioAnalysisResult:
    return AudioAnalysisResult(
        filename="test.wav",
        bpm=120.0,
        duration=10.0,
        peaks=[],
        sections=[],
        beat_times=[float(i) * 0.5 for i in range(20)],
        intensity_curve=[0.5] * 20,
    )


@pytest.fixture
def video_clips() -> list[VideoAnalysisResult]:
    return [
        VideoAnalysisResult(
            path=f"/videos/clip{i}.mp4",
            intensity_score=0.5,
            duration=5.0,
            thumbnail_data=None,
        )
        for i in range(3)
    ]


@pytest.fixture
def broll_clips() -> list[VideoAnalysisResult]:
    return [
        VideoAnalysisResult(
            path=f"/videos/broll{i}.mp4",
            intensity_score=0.5,
            duration=5.0,
            thumbnail_data=None,
        )
        for i in range(2)
    ]


def _validate_first_clip_not_broll(segments: list[SegmentPlan]) -> Any:
    assert len(segments) > 0, "Expected at least one segment"
    assert "broll" not in segments[0].video_path, "First clip should not be B-Roll"
    assert len(segments) > 1, "Expected at least two segments"
    assert "broll" in segments[1].video_path, "Second clip should be B-Roll"


def _validate_empty_segments(segments: list[SegmentPlan]) -> Any:
    assert len(segments) == 0, "Expected empty segments list"


def _validate_only_one_broll_at_end(segments: list[SegmentPlan]) -> Any:
    assert len(segments) > 2, "Expected multiple segments"
    assert "broll" not in segments[0].video_path, "First segment must not be broll"
    assert "broll" in segments[-1].video_path, "Last segment must be broll"


def _validate_max_duration_limits(segments: list[SegmentPlan]) -> Any:
    assert len(segments) > 0, "Expected segments"
    assert sum(s.duration for s in segments) <= 3.0, "Exceeded max duration limit"
    assert segments[-1].timeline_position + segments[-1].duration <= 3.0, (
        "Timeline pos exceeded"
    )


def _validate_no_clips_empty(segments: list[SegmentPlan]) -> Any:
    assert len(segments) == 0, "Segments should be empty if no video clips passed"


@pytest.mark.parametrize(
    "config_kwargs, validation_fn, broll_enabled, modify_clips",
    [
        # Case 1: First clip is not B-roll, but second is (timeline_pos > 0.0)
        (
            {
                "broll_interval_seconds": 0.0,
                "broll_interval_variance": 0.0,
                "min_clip_seconds": 0.1,
            },
            _validate_first_clip_not_broll,
            True,
            None,
        ),
        # Case 2: Actual duration <= 0 (e.g. clip duration very small, skipped entirely)
        (
            {"min_clip_seconds": 0.5},
            _validate_empty_segments,
            False,
            lambda clips: [
                VideoAnalysisResult(
                    path=c.path,
                    intensity_score=c.intensity_score,
                    duration=0.0,
                    thumbnail_data=None,
                )
                for c in clips
            ],
        ),
        # Case 3: Verify broll occurs correctly later in the timeline
        (
            {
                "broll_interval_seconds": 2.0,
                "broll_interval_variance": 0.0,
                "min_clip_seconds": 0.5,
            },
            _validate_only_one_broll_at_end,
            True,
            None,
        ),
        # Case 4: Max duration hits limit gracefully
        (
            {"max_duration_seconds": 3.0, "min_clip_seconds": 0.1},
            _validate_max_duration_limits,
            False,
            None,
        ),
        # Case 5: Passing empty clip lists returns early
        (
            {},
            _validate_no_clips_empty,
            False,
            lambda clips: [],
        ),
    ],
)
def test_build_segment_plan_complex_edge_cases(
    generator: MontageGenerator,
    audio_data: AudioAnalysisResult,
    video_clips: list[VideoAnalysisResult],
    broll_clips: list[VideoAnalysisResult],
    config_kwargs: dict[str, Any],
    validation_fn: Callable[[list[SegmentPlan]], Any],
    broll_enabled: bool,
    modify_clips: Callable[[list[VideoAnalysisResult]], list[VideoAnalysisResult]]
    | None,
) -> None:
    # Arrange
    config = PacingConfig(**config_kwargs)

    if modify_clips:
        video_clips = modify_clips(video_clips)

    broll = broll_clips if broll_enabled else None

    # Act
    segments = generator.build_segment_plan(
        audio_data, video_clips, pacing=config, broll_clips=broll
    )

    # Assert
    validation_fn(segments)
