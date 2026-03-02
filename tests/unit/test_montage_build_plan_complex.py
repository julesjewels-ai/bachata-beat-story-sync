import pytest
from typing import List, Callable, Any, Dict

from src.core.montage import MontageGenerator
from src.core.models import (
    AudioAnalysisResult,
    PacingConfig,
    VideoAnalysisResult,
    SegmentPlan,
)

@pytest.fixture
def generator() -> MontageGenerator:
    return MontageGenerator()

@pytest.fixture
def base_audio_data() -> AudioAnalysisResult:
    # 30 beats at 120 BPM -> 0.5s per beat, 15 seconds total duration
    beats = [float(i) * 0.5 for i in range(30)]
    return AudioAnalysisResult(
        filename="test_track.wav",
        bpm=120.0,
        duration=15.0,
        peaks=[],
        sections=[],
        beat_times=beats,
        intensity_curve=[0.5] * 30,
    )

@pytest.fixture
def base_video_clips() -> List[VideoAnalysisResult]:
    return [
        VideoAnalysisResult(
            path="/videos/clip1.mp4",
            intensity_score=0.8,
            duration=30.0,
            thumbnail_data=None,
        ),
        VideoAnalysisResult(
            path="/videos/clip2.mp4",
            intensity_score=0.3,
            duration=30.0,
            thumbnail_data=None,
        ),
    ]

@pytest.mark.parametrize("config_updates, clear_beats, clear_clips, validation_fn", [
    (
        {"max_clips": 2},
        False,
        False,
        lambda segments: assert_len(segments, 2)
    ),
    (
        {"max_duration_seconds": 3.0, "min_clip_seconds": 1.5},
        False,
        False,
        lambda segments: assert_total_duration(segments, 3.0)
    ),
    (
        {"max_duration_seconds": 5.0, "min_clip_seconds": 1.5, "medium_intensity_seconds": 4.0},
        False,
        False,
        lambda segments: (
            assert_total_duration(segments, 5.0) or
            assert_len(segments, 2) or
            assert_last_segment_trimmed(segments, 4.0)
        )
    ),
    (
        {},
        True,
        False,
        lambda segments: assert_len(segments, 0)
    ),
    (
        {},
        False,
        True,
        lambda segments: assert_len(segments, 0)
    ),
])
def test_build_segment_plan_complex(
    generator: MontageGenerator,
    base_audio_data: AudioAnalysisResult,
    base_video_clips: List[VideoAnalysisResult],
    config_updates: Dict[str, Any],
    clear_beats: bool,
    clear_clips: bool,
    validation_fn: Callable[[List[SegmentPlan]], Any],
) -> None:
    # Arrange
    pacing = PacingConfig(**config_updates)

    if clear_beats:
        base_audio_data.beat_times = []
        base_audio_data.intensity_curve = []

    clips = [] if clear_clips else base_video_clips

    # Act
    segments = generator.build_segment_plan(
        audio_data=base_audio_data,
        video_clips=clips,
        pacing=pacing
    )

    # Assert
    validation_fn(segments)

def assert_len(segments: List[SegmentPlan], expected: int) -> Any:
    assert len(segments) == expected, f"Expected {expected} segments, got {len(segments)}"

def assert_total_duration(segments: List[SegmentPlan], expected: float) -> Any:
    total_duration = sum(s.duration for s in segments)
    assert total_duration == expected, f"Expected total duration {expected}, got {total_duration}"

def assert_last_segment_trimmed(segments: List[SegmentPlan], original_min_duration: float) -> Any:
    assert len(segments) > 0, "Expected at least one segment"
    assert segments[-1].duration < original_min_duration, f"Expected last segment to be trimmed (duration < {original_min_duration}), got {segments[-1].duration}"
