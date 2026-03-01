import pytest
from typing import Any
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
def video_clips() -> list[VideoAnalysisResult]:
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

@pytest.fixture
def broll_clips() -> list[VideoAnalysisResult]:
    return [
        VideoAnalysisResult(
            path="/videos/broll1.mp4",
            intensity_score=0.4,
            duration=30.0,
            thumbnail_data=None,
        ),
    ]

@pytest.fixture
def base_audio() -> AudioAnalysisResult:
    return AudioAnalysisResult(
        filename="test.wav",
        bpm=120.0,
        duration=60.0,
        peaks=[],
        sections=[],
        beat_times=[float(i) * 0.5 for i in range(120)],
        intensity_curve=[0.5] * 120,
    )

@pytest.mark.parametrize("scenario, config_kwargs, audio_kwargs, extra_clips_kwargs, validation_fn", [
    (
        "max_clips limit",
        {"max_clips": 5},
        {},
        {},
        lambda segments, config, audio: len(segments) == 5
    ),
    (
        "max_duration limit",
        {"max_duration_seconds": 25.0},
        {},
        {},
        lambda segments, config, audio: sum(seg.duration for seg in segments) == pytest.approx(25.0, 0.1)
    ),
    (
        "snap_to_beats true",
        {"snap_to_beats": True, "min_clip_seconds": 2.0, "medium_intensity_seconds": 2.0},
        {},
        {},
        lambda segments, config, audio: len(segments) > 0 and segments[0].duration == pytest.approx(2.0, 0.1)
    ),
    (
        "snap_to_beats false",
        {"snap_to_beats": False, "min_clip_seconds": 2.0, "medium_intensity_seconds": 2.0},
        {},
        {},
        lambda segments, config, audio: len(segments) > 0 and segments[0].duration == pytest.approx(2.0, 0.1)
    ),
    (
        "short intensity curve defaults to medium",
        {"min_clip_seconds": 1.0},
        {"duration": 10.0, "beat_times": [float(i) * 0.5 for i in range(10)], "intensity_curve": [0.8]},
        {},
        lambda segments, config, audio: "medium" in [seg.intensity_level for seg in segments]
    ),
    (
        "broll clips inserted but not first",
        {"broll_interval_seconds": 2.0, "broll_interval_variance": 0.0},
        {},
        {"broll_clips": True},
        lambda segments, config, audio: len(segments) > 0 and "/videos/broll1.mp4" not in segments[0].video_path and any("/videos/broll1.mp4" in seg.video_path for seg in segments)
    ),
    (
        "zero duration clips are ignored",
        {},
        {},
        {"zero_clip": True},
        lambda segments, config, audio: len(segments) == 0
    ),
    (
        "speed ramp and randomisation",
        {"accelerate_pacing": True, "speed_ramp_enabled": True, "randomize_speed_ramps": True, "min_clip_seconds": 0.1},
        {},
        {},
        lambda segments, config, audio: len(segments) > 0 and len(set(seg.speed_factor for seg in segments)) > 1
    ),
    (
        "zero bpm fallbacks to 0.5 spb",
        {},
        {"bpm": 0.0, "duration": 10.0, "beat_times": [float(i) * 0.5 for i in range(10)], "intensity_curve": [0.5] * 10},
        {},
        lambda segments, config, audio: len(segments) > 0
    )
])
def test_build_segment_plan_complex_boundaries(
    generator: MontageGenerator,
    base_audio: AudioAnalysisResult,
    video_clips: list[VideoAnalysisResult],
    broll_clips: list[VideoAnalysisResult],
    scenario: str,
    config_kwargs: dict[str, Any],
    audio_kwargs: dict[str, Any],
    extra_clips_kwargs: dict[str, Any],
    validation_fn: Any
) -> None:
    # Arrange
    config = PacingConfig(**config_kwargs)

    # Update audio with specific kwargs
    audio = base_audio.model_copy(update=audio_kwargs)

    # Handle extra clips
    kwargs_broll = broll_clips if extra_clips_kwargs.get("broll_clips") else None

    # Replace video clips if zero_clip is set
    v_clips = video_clips
    if extra_clips_kwargs.get("zero_clip"):
        v_clips = [
            VideoAnalysisResult(
                path="/videos/zero.mp4",
                intensity_score=0.5,
                duration=0.0,
                thumbnail_data=None,
            )
        ]

    # Act
    segments = generator.build_segment_plan(
        audio,
        v_clips,
        config,
        broll_clips=kwargs_broll
    )

    # Assert
    assert validation_fn(segments, config, audio) is True, f"Failed on scenario: {scenario}"
