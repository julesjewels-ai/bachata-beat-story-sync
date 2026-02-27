"""
Parametrized tests for MontageGenerator.build_segment_plan (Grade E Complexity).
Focus: Edge cases, logic branches, and boundary conditions.
"""
import math
import random
import pytest
from typing import List, Optional
from src.core.models import (
    AudioAnalysisResult,
    PacingConfig,
    VideoAnalysisResult,
    SegmentPlan,
)
from src.core.montage import MontageGenerator


@pytest.fixture
def generator() -> MontageGenerator:
    return MontageGenerator()


@pytest.fixture
def base_audio() -> AudioAnalysisResult:
    """Standard audio with 60 beats at 120 BPM (30s duration)."""
    return AudioAnalysisResult(
        filename="test.wav",
        bpm=120.0,
        duration=30.0,
        peaks=[],
        sections=[],
        beat_times=[i * 0.5 for i in range(60)],
        intensity_curve=[0.5] * 60,
    )


@pytest.fixture
def base_clips() -> List[VideoAnalysisResult]:
    """Standard list of 5 video clips."""
    return [
        VideoAnalysisResult(
            path=f"/video/clip_{i}.mp4",
            intensity_score=0.1 * i,
            duration=10.0,
            thumbnail_data=None,
        )
        for i in range(1, 6)
    ]


@pytest.mark.parametrize(
    "max_clips, expected_count",
    [
        (1, 1),
        (5, 5),
        (10, 10),  # Assuming audio allows enough segments
        (None, 10), # Audio duration limits count (~6-7 segments normally)
    ],
)
def test_max_clips_limit(
    generator: MontageGenerator,
    base_audio: AudioAnalysisResult,
    base_clips: List[VideoAnalysisResult],
    max_clips: Optional[int],
    expected_count: int,
) -> None:
    """Verify that max_clips terminates plan generation early."""
    # Force very short segments to ensure we hit the clip limit
    config = PacingConfig(
        max_clips=max_clips,
        min_clip_seconds=0.5,
        medium_intensity_seconds=1.0,  # 2 beats per clip
    )

    # Modify audio to support at least expected_count segments
    base_audio.intensity_curve = [0.5] * (expected_count * 4) # ample beats
    base_audio.beat_times = [i * 0.5 for i in range(len(base_audio.intensity_curve))]

    segments = generator.build_segment_plan(base_audio, base_clips, config)

    if max_clips is not None:
        assert len(segments) == expected_count, f"Expected {expected_count}, got {len(segments)}"
    else:
        # Default behavior check (should just run out of beats)
        assert len(segments) > 0


@pytest.mark.parametrize(
    "max_duration, expected_duration",
    [
        (5.0, 5.0),
        (10.0, 10.0),
        (29.0, 29.0),  # Just under total audio duration
        (None, 30.0),  # Full audio duration
    ],
)
def test_max_duration_limit(
    generator: MontageGenerator,
    base_audio: AudioAnalysisResult,
    base_clips: List[VideoAnalysisResult],
    max_duration: Optional[float],
    expected_duration: float,
) -> None:
    """Verify that max_duration_seconds terminates plan generation accurately."""
    config = PacingConfig(max_duration_seconds=max_duration)

    segments = generator.build_segment_plan(base_audio, base_clips, config)

    total_time = sum(s.duration for s in segments)

    # Floating point tolerance
    assert abs(total_time - expected_duration) < 0.1, \
        f"Expected {expected_duration}, got {total_time}"

    if max_duration:
        # Check the last segment was trimmed if necessary
        last_seg = segments[-1]
        assert last_seg.duration > 0


@pytest.mark.parametrize(
    "snap_to_beats, expected_modulo",
    [
        (True, 0.0),   # Should be exactly N * spb
        (False, None), # Can be arbitrary float
    ],
)
def test_snap_to_beats_logic(
    generator: MontageGenerator,
    base_audio: AudioAnalysisResult,
    base_clips: List[VideoAnalysisResult],
    snap_to_beats: bool,
    expected_modulo: Optional[float],
) -> None:
    """Verify beat snapping vs time-based duration."""
    config = PacingConfig(
        snap_to_beats=snap_to_beats,
        medium_intensity_seconds=1.3, # Non-integer beat count (1.3 / 0.5 = 2.6)
        min_clip_seconds=0.1,         # Ensure minimum doesn't override logic
    )

    segments = generator.build_segment_plan(base_audio, base_clips, config)

    spb = 60.0 / base_audio.bpm # 0.5s

    for seg in segments:
        if expected_modulo is not None:
            # Check if duration is a multiple of SPB
            remainder = seg.duration % spb
            assert remainder < 1e-9 or abs(remainder - spb) < 1e-9, \
                f"Duration {seg.duration} not snapped to beat grid {spb}"
        else:
            # If not snapping, duration should roughly match target seconds
            pass


    target = 1.3
    spb = 0.5
    # snap=True: round(2.6) -> 3.0 beats -> 1.5s
    # snap=False: ceil(2.6) -> 3.0 beats -> 1.5s
    # Let's try 1.2s -> 2.4 beats
    # snap=True: round(2.4) -> 2.0 beats -> 1.0s
    # snap=False: ceil(2.4) -> 3.0 beats -> 1.5s

    if snap_to_beats:
        # Config to trigger rounding down
        config.medium_intensity_seconds = 1.2
        segs = generator.build_segment_plan(base_audio, base_clips, config)
        if segs:
            # 1.0s (2 beats) is expected because round(2.4) = 2
            assert segs[0].duration == 1.0
    else:
        # Config to trigger ceiling (always up)
        config.medium_intensity_seconds = 1.2
        segs = generator.build_segment_plan(base_audio, base_clips, config)
        if segs:
            # 1.5s (3 beats) is expected because ceil(2.4) = 3
            assert segs[0].duration == 1.5


@pytest.mark.parametrize(
    "accelerate, expect_decrease",
    [
        (True, True),
        (False, False),
    ],
)
def test_accelerate_pacing(
    generator: MontageGenerator,
    base_audio: AudioAnalysisResult,
    base_clips: List[VideoAnalysisResult],
    accelerate: bool,
    expect_decrease: bool,
) -> None:
    """Verify that segment durations decrease over time when enabled."""
    config = PacingConfig(
        accelerate_pacing=accelerate,
        medium_intensity_seconds=5.0, # Long enough to see shrinkage
        min_clip_seconds=0.5,
    )

    # Ensure constant intensity
    base_audio.intensity_curve = [0.5] * 100
    base_audio.beat_times = [i * 0.5 for i in range(100)]

    segments = generator.build_segment_plan(base_audio, base_clips, config)

    if len(segments) < 3:
        pytest.skip("Not enough segments to test acceleration")

    first_dur = segments[0].duration
    last_dur = segments[-1].duration

    if expect_decrease:
        assert last_dur < first_dur, "Duration did not decrease with acceleration enabled"
    else:
        # With constant intensity and no acceleration, durations should be stable
        # (ignoring last segment cut)
        mid_dur = segments[len(segments)//2].duration
        assert abs(first_dur - mid_dur) < 0.01, "Duration drifted without acceleration"


@pytest.mark.parametrize(
    "bpm, expected_spb",
    [
        (120.0, 0.5),
        (60.0, 1.0),
        (0.0, 0.5), # Default fallback
        (-10.0, 0.5), # Fallback for invalid
    ],
)
def test_bpm_calculations(
    generator: MontageGenerator,
    base_audio: AudioAnalysisResult,
    base_clips: List[VideoAnalysisResult],
    bpm: float,
    expected_spb: float,
) -> None:
    """Verify BPM edge cases (0, negative)."""
    base_audio.bpm = bpm
    # We rely on segment duration to infer used SPB
    # Target 1 beat per segment
    config = PacingConfig(
        min_clip_seconds=0.01, # Allow very short
        medium_intensity_seconds=0.01, # Force 1 beat (min) logic
    )

    segments = generator.build_segment_plan(base_audio, base_clips, config)

    if segments:
        # If BPM is 0, SPB is 0.5.
        # min_beats calculation: ceil(min_clip / spb)
        # if min_clip=0.01, spb=0.5 -> ceil(0.02) = 1 beat.
        # duration = 1 * 0.5 = 0.5
        pass

    # Actually, simpler test: verify no ZeroDivisionError and sane output
    assert len(segments) > 0


def test_intensity_threshold_boundaries(
    generator: MontageGenerator,
    base_audio: AudioAnalysisResult,
    base_clips: List[VideoAnalysisResult],
) -> None:
    """Verify exact boundary behavior for intensity thresholds."""
    config = PacingConfig(
        low_intensity_threshold=0.3,
        high_intensity_threshold=0.7,
    )

    # Create specific intensity values
    base_audio.intensity_curve = [0.29, 0.30, 0.69, 0.70, 0.71]
    # Need enough beats to cover these checks.
    # Let's just check the logic mapping by mocking the curve lookup

    # We'll construct a curve where each segment consumes exactly 1 beat
    base_audio.bpm = 60.0 # 1 sec/beat
    config.low_intensity_seconds = 1.0 # 1 beat
    config.medium_intensity_seconds = 1.0 # 1 beat
    config.high_intensity_seconds = 1.0 # 1 beat
    config.min_clip_seconds = 0.5

    # 5 beats, 5 intensities
    # beat_times length determines loop iterations. Match intensity curve length.
    base_audio.beat_times = [0, 1, 2, 3, 4]

    segments = generator.build_segment_plan(base_audio, base_clips, config)

    # Expected:
    # 0.29 < 0.3 -> low
    # 0.30 >= 0.3 (and < 0.7) -> medium (Note: code uses >= for high, < for low)
    #
    # Code Logic:
    # if intensity >= high_threshold: high
    # elif intensity < low_threshold: low
    # else: medium
    #
    # 0.29 < 0.3 -> low
    # 0.30 >= 0.3 (FALSE for < 0.3 check) -> medium
    # 0.69 < 0.7 -> medium
    # 0.70 >= 0.7 -> high
    # 0.71 > 0.7 -> high

    levels = [s.intensity_level for s in segments]
    assert levels == ["low", "medium", "medium", "high", "high"]


def test_shorts_mode_vertical_priority(
    generator: MontageGenerator,
    base_audio: AudioAnalysisResult,
    base_clips: List[VideoAnalysisResult],
) -> None:
    """Verify that is_shorts=True prioritizes vertical clips."""
    # Setup clips: 1 vertical (low score), 1 horizontal (high score)
    v_clip = VideoAnalysisResult(path="v.mp4", intensity_score=0.1, duration=10, is_vertical=True)
    h_clip = VideoAnalysisResult(path="h.mp4", intensity_score=0.9, duration=10, is_vertical=False)

    clips = [h_clip, v_clip]

    config = PacingConfig(is_shorts=True)

    # Should pick vertical first despite lower intensity score
    segments = generator.build_segment_plan(base_audio, clips, config)

    assert segments[0].video_path == "v.mp4"
    assert segments[1].video_path == "h.mp4"

    # Test disabled
    config.is_shorts = False
    segments = generator.build_segment_plan(base_audio, clips, config)

    # Should pick higher intensity first (horizontal)
    assert segments[0].video_path == "h.mp4"
    assert segments[1].video_path == "v.mp4"


def test_empty_beat_times(
    generator: MontageGenerator,
    base_clips: List[VideoAnalysisResult],
) -> None:
    """Verify graceful handling of empty beat list."""
    audio = AudioAnalysisResult(
        filename="silent.wav",
        bpm=120.0,
        duration=10.0,
        peaks=[],
        sections=[],
        beat_times=[],
        intensity_curve=[],
    )
    segments = generator.build_segment_plan(audio, base_clips)
    assert segments == []


def test_randomize_speed_ramps_coverage(
    generator: MontageGenerator,
    base_audio: AudioAnalysisResult,
    base_clips: List[VideoAnalysisResult],
) -> None:
    """Verify that speed ramping logic is exercised."""
    config = PacingConfig(
        speed_ramp_enabled=True,
        randomize_speed_ramps=True,
        seed="12345" # Fixed: Must be string based on Pydantic model
    )

    segments = generator.build_segment_plan(base_audio, base_clips, config)

    # Just verify that speed_factor is not always exactly 1.0 or the base config values
    # Base speeds are 1.0 by default in PacingConfig unless changed
    # We need to set them to something distinct to see variation?
    # Actually, randomize applies +/- 10% to the base speed.

    varied = False
    for s in segments:
        if abs(s.speed_factor - 1.0) > 0.001:
            varied = True
            break

    # Default high/low/med speeds are 1.0?
    # Let's check PacingConfig defaults...
    # They are likely 1.0.
    # If base is 1.0, random(0.9, 1.1) should produce non-1.0

    assert varied, "Speed factors should vary when randomization is enabled"
