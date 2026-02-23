"""
Edge case tests for MontageGenerator.build_segment_plan.

Focuses on:
- PacingConfig limits (max_clips, max_duration_seconds)
- beat snapping (snap_to_beats=False)
- Audio data irregularities (bpm=0, missing intensity points)
"""
import pytest
import math
from src.core.montage import MontageGenerator
from src.core.models import (
    AudioAnalysisResult,
    PacingConfig,
    VideoAnalysisResult,
)

@pytest.fixture
def base_audio():
    """Audio data with 16 beats at 120 BPM (0.5s per beat)."""
    return AudioAnalysisResult(
        filename="test.wav",
        bpm=120.0,
        duration=8.0,
        peaks=[],
        sections=[],
        beat_times=[float(i) * 0.5 for i in range(16)],
        intensity_curve=[0.5] * 16,
    )

@pytest.fixture
def base_clips():
    return [
        VideoAnalysisResult(
            path="/videos/clip1.mp4",
            intensity_score=0.5,
            duration=10.0,
            thumbnail_data=None,
        ),
    ]

@pytest.mark.parametrize("scenario, config_kwargs, audio_kwargs, expected_check", [
    (
        "snap_false_ceil",
        {"snap_to_beats": False, "medium_intensity_seconds": 1.7},
        {},
        # 1.7s / 0.5s = 3.4 beats.
        # snap=True -> round(3.4) = 3 beats = 1.5s
        # snap=False -> ceil(3.4) = 4 beats = 2.0s
        lambda s, a: s[0].duration == 2.0
    ),
    (
        "snap_true_round",
        {"snap_to_beats": True, "medium_intensity_seconds": 1.7},
        {},
        # 1.7s / 0.5s = 3.4 beats. round(3.4) = 3 beats = 1.5s
        lambda s, a: s[0].duration == 1.5
    ),
    (
        "max_clips",
        {"max_clips": 2},
        {},
        lambda s, a: len(s) == 2
    ),
    (
        "max_duration_break",
        {"max_duration_seconds": 2.5},
        {},
        # 2.5s is exactly 5 beats.
        # Default min_clip_seconds=1.5 (3 beats).
        # Seg 1: 3 beats (1.5s). Remaining: 1.0s.
        # Seg 2: 1.0s (2 beats) -> Wait, min_beats is 3.
        # But max_duration logic trims it.
        # Let's see:
        # Seg 1: target=1.5s. timeline=1.5s.
        # Seg 2: target=1.5s. timeline=3.0s > 2.5s.
        # loop break check is: timeline_pos >= max_duration.
        # At start of loop 2: timeline_pos=1.5 < 2.5. Continue.
        # trim logic: remaining = 2.5 - 1.5 = 1.0. segment_duration = min(1.5, 1.0) = 1.0.
        # Append seg 2 (1.0s). timeline_pos=2.5.
        # At start of loop 3: timeline_pos=2.5 >= 2.5. Break.
        # Total duration = 2.5.
        lambda s, a: abs(sum(seg.duration for seg in s) - 2.5) < 0.01
    ),
    (
        "max_duration_trim",
        {"max_duration_seconds": 3.1},
        {},
        # Seg 1: 1.5s.
        # Seg 2: 1.5s. Total 3.0s.
        # Loop 3: timeline=3.0 < 3.1.
        # Remaining 0.1s.
        # Seg 3: min(1.5, 0.1) = 0.1s.
        # Total 3.1s.
        lambda s, a: abs(sum(seg.duration for seg in s) - 3.1) < 0.01
    ),
    (
        "zero_bpm",
        {},
        {"bpm": 0.0},
        # spb defaults to 0.5. Behave as normal 120bpm.
        lambda s, a: len(s) > 0 and s[0].duration >= 1.5
    ),
    (
        "missing_intensity",
        {},
        {"intensity_curve": [0.5] * 2}, # Only 2 points, but 16 beats
        # Beat 3 (index 2) should use default intensity 0.5
        lambda s, a: len(s) > 1 and s[-1].intensity_level == "medium"
    ),
])
def test_build_segment_plan_edge_cases(
    base_audio, base_clips, scenario, config_kwargs, audio_kwargs, expected_check
):
    # Arrange
    generator = MontageGenerator()

    # Modify audio if needed
    if audio_kwargs:
        audio_data = base_audio.model_copy(update=audio_kwargs)
    else:
        audio_data = base_audio

    # Create config
    config = PacingConfig(**config_kwargs)

    # Act
    segments = generator.build_segment_plan(audio_data, base_clips, config)

    # Assert
    assert expected_check(segments, audio_data), f"Failed scenario: {scenario}"
