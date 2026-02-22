"""
Comprehensive unit tests for MontageGenerator.build_segment_plan covering edge cases and complex branches.
"""
import math
import pytest
from typing import List, Optional

from src.core.montage import MontageGenerator
from src.core.models import (
    AudioAnalysisResult,
    VideoAnalysisResult,
    PacingConfig,
    MusicalSection,
    SegmentPlan,
)

# Constants for test data
TEST_BPM = 120.0
TEST_SPB = 60.0 / TEST_BPM  # 0.5 seconds per beat
TEST_CLIP_DURATION = 10.0


@pytest.fixture
def base_audio_result() -> AudioAnalysisResult:
    """Base AudioAnalysisResult fixture with 10 seconds of data."""
    duration = 10.0
    beat_count = int(duration / TEST_SPB)
    beat_times = [i * TEST_SPB for i in range(beat_count)]
    intensity_curve = [0.5] * beat_count  # Default medium intensity

    return AudioAnalysisResult(
        filename="test_audio.wav",
        duration=duration,
        bpm=TEST_BPM,
        beat_times=beat_times,
        intensity_curve=intensity_curve,
        sections=[],
        peaks=[],
    )


@pytest.fixture
def base_video_clips() -> List[VideoAnalysisResult]:
    """Base list of VideoAnalysisResult fixtures."""
    return [
        VideoAnalysisResult(
            path=f"/video/clip_{i}.mp4",
            duration=TEST_CLIP_DURATION,
            intensity_score=0.5 + (i * 0.1),  # Varying intensity
            thumbnail_data=None,
        )
        for i in range(3)
    ]


@pytest.fixture
def base_pacing_config() -> PacingConfig:
    """Base PacingConfig fixture with default values."""
    return PacingConfig()


@pytest.mark.parametrize(
    "intensity_values, expected_level, expected_speed_factor, ramp_enabled",
    [
        # Case 1: High intensity, speed ramp enabled -> high speed
        ([0.9], "high", 1.5, True), # Assuming default high_intensity_speed is 1.5 (checking defaults)
        # Case 2: Low intensity, speed ramp enabled -> low speed
        ([0.1], "low", 0.75, True), # Assuming default low_intensity_speed is 0.75
        # Case 3: Medium intensity, speed ramp enabled -> medium speed (usually 1.0)
        ([0.5], "medium", 1.0, True),
        # Case 4: High intensity, speed ramp DISABLED -> speed 1.0
        ([0.9], "high", 1.0, False),
        # Case 5: Low intensity, speed ramp DISABLED -> speed 1.0
        ([0.1], "low", 1.0, False),
    ],
)
def test_intensity_and_speed_logic(
    base_audio_result: AudioAnalysisResult,
    base_video_clips: List[VideoAnalysisResult],
    base_pacing_config: PacingConfig,
    intensity_values: List[float],
    expected_level: str,
    expected_speed_factor: float,
    ramp_enabled: bool,
):
    """Verify correct intensity level and speed factor assignment."""
    # Arrange
    base_audio_result.intensity_curve = intensity_values * len(base_audio_result.beat_times)
    # Ensure intensity curve length matches beat times for this test
    base_audio_result.beat_times = base_audio_result.beat_times[:len(intensity_values)]

    # Update config with specific speed settings if needed, here relying on defaults
    # But setting ramp_enabled explicitly
    config = base_pacing_config.model_copy(update={"speed_ramp_enabled": ramp_enabled})

    # We might need to check what the default speeds are in PacingConfig if the test fails
    # Let's assume standard defaults: high=1.5, low=0.75, medium=1.0 based on common patterns
    # or better, explicitly set them in the config for the test.
    config.high_intensity_speed = 1.5
    config.low_intensity_speed = 0.75
    config.medium_intensity_speed = 1.0

    generator = MontageGenerator()

    # Act
    plan = generator.build_segment_plan(base_audio_result, base_video_clips, config)

    # Assert
    assert len(plan) > 0
    for segment in plan:
        assert segment.intensity_level == expected_level
        assert segment.speed_factor == expected_speed_factor


@pytest.mark.parametrize(
    "snap_to_beats, target_seconds, expected_duration_approx",
    [
        # Case 1: Snap to beats = True. 2.2s target / 0.5s spb = 4.4 beats -> rounds to 4 beats = 2.0s
        (True, 2.2, 2.0),
        # Case 2: Snap to beats = True. 2.3s target / 0.5s spb = 4.6 beats -> rounds to 5 beats = 2.5s
        (True, 2.3, 2.5),
        # Case 3: Snap to beats = False. 2.2s target / 0.5s spb = 4.4 beats -> ceiled to 5 beats = 2.5s?
        # Wait, the logic is: max(min_beats, math.ceil(target_seconds / spb))
        # So if snap_to_beats is False, it ALWAYS uses ceil.
        (False, 2.2, 2.5),
    ],
)
def test_duration_rounding_logic(
    base_audio_result: AudioAnalysisResult,
    base_video_clips: List[VideoAnalysisResult],
    base_pacing_config: PacingConfig,
    snap_to_beats: bool,
    target_seconds: float,
    expected_duration_approx: float,
):
    """Verify beat snapping logic."""
    # Arrange
    # Force medium intensity to trigger medium_intensity_seconds usage
    base_audio_result.intensity_curve = [0.5] * 20
    base_audio_result.beat_times = [i * 0.5 for i in range(20)]

    config = base_pacing_config.model_copy(update={
        "snap_to_beats": snap_to_beats,
        "medium_intensity_seconds": target_seconds,
        "min_clip_seconds": 0.1, # Low min to not interfere
    })

    generator = MontageGenerator()

    # Act
    plan = generator.build_segment_plan(base_audio_result, base_video_clips, config)

    # Assert
    assert len(plan) > 0
    # Check the first segment duration
    assert plan[0].duration == pytest.approx(expected_duration_approx)


@pytest.mark.parametrize(
    "max_clips, max_duration, expected_segment_count, expected_total_duration",
    [
        # Case 1: Max clips limit
        (2, None, 2, None),
        # Case 2: Max duration limit (shorter than audio)
        (None, 3.0, None, 3.0),
        # Case 3: No limits (should cover full audio)
        (None, None, None, 10.0), # base_audio is 10s
    ],
)
def test_limits_logic(
    base_audio_result: AudioAnalysisResult,
    base_video_clips: List[VideoAnalysisResult],
    base_pacing_config: PacingConfig,
    max_clips: Optional[int],
    max_duration: Optional[float],
    expected_segment_count: Optional[int],
    expected_total_duration: Optional[float],
):
    """Verify max_clips and max_duration limits."""
    # Arrange
    config = base_pacing_config.model_copy(update={
        "max_clips": max_clips,
        "max_duration_seconds": max_duration,
        "medium_intensity_seconds": 1.0, # Small segments to hit clip count easily
        "min_clip_seconds": 0.5,
    })

    generator = MontageGenerator()

    # Act
    plan = generator.build_segment_plan(base_audio_result, base_video_clips, config)

    # Assert
    if expected_segment_count is not None:
        assert len(plan) == expected_segment_count

    total_dur = sum(s.duration for s in plan)
    if expected_total_duration is not None:
        # Allow small margin for floating point
        assert total_dur <= expected_total_duration + 0.001
        # If max_duration is set, the total duration should be close to it
        # unless audio ran out first (which is 10s, larger than 3.0s test case)
        assert total_dur >= expected_total_duration - 1.0 # Loose lower bound


def test_intensity_curve_shorter_than_beats(
    base_audio_result: AudioAnalysisResult,
    base_video_clips: List[VideoAnalysisResult],
    base_pacing_config: PacingConfig,
):
    """Verify handling when intensity curve has fewer points than beat_times."""
    # Arrange
    base_audio_result.beat_times = [i * 0.5 for i in range(10)] # 10 beats
    base_audio_result.intensity_curve = [0.5] * 5 # Only 5 intensity points

    generator = MontageGenerator()

    # Act
    plan = generator.build_segment_plan(base_audio_result, base_video_clips, base_pacing_config)

    # Assert
    # Should not crash.
    # Code says: intensity = intensity_curve[beat_idx] if beat_idx < len(intensity_curve) else 0.5
    assert len(plan) > 0
    # Validate that we processed all beats (approx 5s total)
    total_dur = sum(s.duration for s in plan)
    assert total_dur == pytest.approx(5.0)


def test_section_label_assignment(
    base_audio_result: AudioAnalysisResult,
    base_video_clips: List[VideoAnalysisResult],
    base_pacing_config: PacingConfig,
):
    """Verify correct section label assignment based on time."""
    # Arrange
    # Define sections: Intro (0-2s), Chorus (2-5s)
    sections = [
        MusicalSection(label="Intro", start_time=0.0, end_time=2.0, avg_intensity=0.5),
        MusicalSection(label="Chorus", start_time=2.0, end_time=5.0, avg_intensity=0.8),
    ]
    base_audio_result.sections = sections
    base_audio_result.beat_times = [i * 0.5 for i in range(10)] # 5s total
    base_audio_result.intensity_curve = [0.5] * 10

    # Configure segments to be small (0.5s) to resolve sections finely
    config = base_pacing_config.model_copy(update={
        "medium_intensity_seconds": 0.5,
        "min_clip_seconds": 0.5,
    })

    generator = MontageGenerator()

    # Act
    plan = generator.build_segment_plan(base_audio_result, base_video_clips, config)

    # Assert
    assert len(plan) > 0
    # Check labels
    for seg in plan:
        if seg.timeline_position < 2.0:
            assert seg.section_label == "Intro"
        elif 2.0 <= seg.timeline_position < 5.0:
            assert seg.section_label == "Chorus"
        else:
            assert seg.section_label is None


def test_clip_variety_with_short_clips(
    base_audio_result: AudioAnalysisResult,
    base_pacing_config: PacingConfig,
):
    """Verify behavior when clip duration is shorter than required segment duration."""
    # Arrange
    short_clip = VideoAnalysisResult(
        path="/video/short.mp4",
        duration=1.0, # Very short
        intensity_score=0.5,
        thumbnail_data=None,
    )

    # Require 2.0s segments
    config = base_pacing_config.model_copy(update={
        "medium_intensity_seconds": 2.0,
        "min_clip_seconds": 2.0,
        "clip_variety_enabled": True,
    })

    generator = MontageGenerator()

    # Act
    plan = generator.build_segment_plan(base_audio_result, [short_clip], config)

    # Assert
    assert len(plan) > 0
    for seg in plan:
        # Duration should be clamped to clip duration
        assert seg.duration <= 1.0
        # Start time should be 0.0 because max_start <= 0
        assert seg.start_time == 0.0


def test_empty_inputs(
    base_pacing_config: PacingConfig,
):
    """Verify empty inputs return empty plan immediately."""
    generator = MontageGenerator()
    audio = AudioAnalysisResult(
        filename="empty.wav", duration=0.0, bpm=0.0,
        beat_times=[], intensity_curve=[], sections=[], peaks=[]
    )

    assert generator.build_segment_plan(audio, [], base_pacing_config) == []

    # With clips but no beats
    clips = [VideoAnalysisResult(path="v.mp4", duration=10.0, intensity_score=0.5, thumbnail_data=None)]
    assert generator.build_segment_plan(audio, clips, base_pacing_config) == []


def test_zero_duration_clip_ignored(
    base_audio_result: AudioAnalysisResult,
    base_pacing_config: PacingConfig,
):
    """Verify that clips with zero duration are skipped (actual_duration <= 0 branch)."""
    # Arrange
    zero_clip = VideoAnalysisResult(
        path="/video/zero.mp4",
        duration=0.0,
        intensity_score=0.5,
        thumbnail_data=None,
    )

    generator = MontageGenerator()

    # Act
    # This should result in NO segments added for this clip
    plan = generator.build_segment_plan(base_audio_result, [zero_clip], base_pacing_config)

    # Assert
    assert len(plan) == 0
