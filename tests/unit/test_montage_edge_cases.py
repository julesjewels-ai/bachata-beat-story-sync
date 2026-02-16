"""
Edge case tests for MontageGenerator using parametrization.
Focuses on high-complexity branches in build_segment_plan.
"""
import pytest
from unittest.mock import MagicMock

from src.core.montage import MontageGenerator
from src.core.models import (
    AudioAnalysisResult,
    VideoAnalysisResult,
    PacingConfig,
)


@pytest.fixture
def generator() -> MontageGenerator:
    return MontageGenerator()


@pytest.fixture
def basic_audio() -> AudioAnalysisResult:
    return AudioAnalysisResult(
        filename="test.wav",
        bpm=120.0,
        duration=10.0,
        peaks=[],
        sections=["full_track"],
        beat_times=[i * 0.5 for i in range(20)],  # 20 beats
        intensity_curve=[0.5] * 20,
    )


@pytest.fixture
def basic_video() -> list[VideoAnalysisResult]:
    return [
        VideoAnalysisResult(
            path="/videos/clip.mp4",
            intensity_score=0.5,
            duration=30.0,
            thumbnail_data=None,
        )
    ]


@pytest.mark.parametrize(
    "bpm, expected_spb",
    [
        (120.0, 0.5),    # Standard
        (60.0, 1.0),     # Slow
        (0.0, 0.5),      # Invalid -> Default
        (-1.0, 0.5),     # Invalid -> Default
    ],
)
def test_bpm_variations(
    generator, basic_audio, basic_video, bpm, expected_spb
):
    """Verify segment duration calculation with various BPMs."""
    basic_audio.bpm = bpm
    # With 0.5 intensity (medium), target is 4.0s
    # If spb=0.5, beats = 4.0/0.5 = 8
    # If spb=1.0, beats = 4.0/1.0 = 4

    config = PacingConfig(medium_intensity_seconds=4.0)
    segments = generator.build_segment_plan(basic_audio, basic_video, config)

    assert len(segments) > 0
    first_seg = segments[0]

    # Calculate expected duration based on beats snapping
    # logic: target_beats = max(min_beats, round(4.0 / spb))
    # duration = target_beats * spb

    min_beats = max(1, round(config.min_clip_seconds / expected_spb))
    expected_beats = max(min_beats, round(4.0 / expected_spb))
    expected_duration = expected_beats * expected_spb

    assert first_seg.duration == pytest.approx(expected_duration)


@pytest.mark.parametrize(
    "intensity, expected_level",
    [
        (0.8, "high"),      # > 0.65
        (0.65, "high"),     # Boundary
        (0.64, "medium"),   # Just below high
        (0.35, "medium"),   # Boundary
        (0.34, "low"),      # Just below medium
        (0.1, "low"),       # Low
    ],
)
def test_intensity_thresholds(
    generator, basic_audio, basic_video, intensity, expected_level
):
    """Verify intensity levels are correctly assigned based on thresholds."""
    basic_audio.intensity_curve = [intensity] * 20
    segments = generator.build_segment_plan(basic_audio, basic_video)

    for seg in segments:
        assert seg.intensity_level == expected_level


@pytest.mark.parametrize(
    "snap_to_beats, target_seconds, spb, expected_duration",
    [
        (True, 2.4, 0.5, 2.5),   # Round 4.8 -> 5 beats * 0.5 = 2.5
        (False, 2.4, 0.5, 2.5),  # Ceil 4.8 -> 5 beats * 0.5 = 2.5
        (True, 2.2, 0.5, 2.0),   # Round 4.4 -> 4 beats * 0.5 = 2.0
        (False, 2.2, 0.5, 2.5),  # Ceil 4.4 -> 5 beats * 0.5 = 2.5
    ],
)
def test_snap_to_beats_logic(
    generator, basic_audio, basic_video, snap_to_beats, target_seconds, spb, expected_duration
):
    """Verify beat snapping logic (round vs ceil)."""
    basic_audio.bpm = 60.0 / spb
    basic_audio.beat_times = [i * spb for i in range(20)]

    # Force medium intensity
    basic_audio.intensity_curve = [0.5] * 20

    config = PacingConfig(
        medium_intensity_seconds=target_seconds,
        snap_to_beats=snap_to_beats,
        min_clip_seconds=0.1 # Low min to not interfere
    )

    segments = generator.build_segment_plan(basic_audio, basic_video, config)
    assert segments[0].duration == pytest.approx(expected_duration)


def test_clip_shorter_than_segment(generator, basic_audio):
    """If a clip is shorter than the calculated segment, clamp to clip duration."""
    short_clip = VideoAnalysisResult(
        path="/videos/short.mp4",
        intensity_score=0.5,
        duration=1.0,  # Very short clip
        thumbnail_data=None,
    )

    # Plan asks for ~4s (medium intensity)
    segments = generator.build_segment_plan(basic_audio, [short_clip])

    # Should clamp to 1.0s
    assert segments[0].duration == 1.0
    assert segments[0].video_path == "/videos/short.mp4"


def test_remaining_beats_too_few(generator, basic_audio, basic_video):
    """If remaining beats are fewer than target, use what's left."""
    # Only 2 beats left (1.0s)
    basic_audio.beat_times = [0.0, 0.5]
    basic_audio.intensity_curve = [0.5, 0.5]

    # Config asks for 4.0s (8 beats)
    config = PacingConfig(medium_intensity_seconds=4.0)

    segments = generator.build_segment_plan(basic_audio, basic_video, config)

    assert len(segments) == 1
    # Should use all remaining beats (2 * 0.5 = 1.0s)
    assert segments[0].duration == 1.0


def test_min_beats_enforcement(generator, basic_audio, basic_video):
    """Ensure min_beats is respected even if calculation yields fewer."""
    # BPM 120 -> spb 0.5
    # Target 0.1s -> 0.2 beats -> round to 0 beats (if not for min)

    config = PacingConfig(
        min_clip_seconds=1.0,  # Force at least 2 beats
        medium_intensity_seconds=0.1
    )

    segments = generator.build_segment_plan(basic_audio, basic_video, config)

    # Should be at least 1.0s
    assert segments[0].duration >= 1.0


def test_start_time_clamping(generator, basic_audio):
    """Ensure start_time doesn't go negative or exceed duration."""
    # Clip duration 5s
    clip = VideoAnalysisResult(
        path="/videos/clip.mp4", intensity_score=0.5, duration=5.0, thumbnail_data=None
    )

    # Segment duration 4s
    config = PacingConfig(medium_intensity_seconds=4.0, min_clip_seconds=0.1)

    segments = generator.build_segment_plan(basic_audio, [clip], config)
    assert segments[0].start_time == 0.0
