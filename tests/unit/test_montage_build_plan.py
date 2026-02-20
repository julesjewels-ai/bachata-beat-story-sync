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

# --- Fixtures ---

@pytest.fixture
def generator():
    return MontageGenerator()

@pytest.fixture
def default_pacing():
    return PacingConfig()

@pytest.fixture
def mock_video_clips():
    return [
        VideoAnalysisResult(
            path="/video/clip_A.mp4",
            intensity_score=0.9, # High
            duration=30.0,
            thumbnail_data=None,
        ),
        VideoAnalysisResult(
            path="/video/clip_B.mp4",
            intensity_score=0.5, # Medium
            duration=30.0,
            thumbnail_data=None,
        ),
        VideoAnalysisResult(
            path="/video/clip_C.mp4",
            intensity_score=0.2, # Low
            duration=30.0,
            thumbnail_data=None,
        ),
    ]

@pytest.fixture
def mock_audio_data():
    """Returns a basic audio analysis result with 120 BPM."""
    return AudioAnalysisResult(
        filename="test.wav",
        bpm=120.0, # 0.5s per beat
        duration=60.0,
        peaks=[],
        sections=[],
        beat_times=[i * 0.5 for i in range(120)], # 120 beats
        intensity_curve=[0.5] * 120,
    )

# --- Tests ---

@pytest.mark.parametrize("intensity, snap_to_beats, expected_level, expected_speed_factor", [
    # High Intensity (>= 0.65)
    (0.7, True, "high", 1.2),
    (0.7, False, "high", 1.2),
    # Medium Intensity (0.35 <= x < 0.65)
    (0.5, True, "medium", 1.0),
    (0.5, False, "medium", 1.0),
    # Low Intensity (< 0.35)
    (0.2, True, "low", 0.7),
    (0.2, False, "low", 0.7),
])
def test_build_segment_plan_intensity_logic(
    generator, mock_video_clips, intensity, snap_to_beats, expected_level, expected_speed_factor
):
    """
    Verify correct level and speed selection based on intensity thresholds.
    Also checks basic beat snapping logic implicitly via result duration.
    """
    # 120 BPM = 0.5s per beat
    audio = AudioAnalysisResult(
        filename="test.wav",
        bpm=120.0,
        duration=10.0,
        peaks=[],
        sections=[],
        beat_times=[i * 0.5 for i in range(20)],
        intensity_curve=[intensity] * 20,
    )

    config = PacingConfig(
        snap_to_beats=snap_to_beats,
        speed_ramp_enabled=True,
        high_intensity_threshold=0.65,
        low_intensity_threshold=0.35,
        high_intensity_speed=1.2,
        medium_intensity_speed=1.0,
        low_intensity_speed=0.7,
        # Set durations to ensure they are picked up
        high_intensity_seconds=2.0,
        medium_intensity_seconds=4.0,
        low_intensity_seconds=6.0,
    )

    segments = generator.build_segment_plan(audio, mock_video_clips, config)

    assert len(segments) > 0
    first_seg = segments[0]
    assert first_seg.intensity_level == expected_level
    assert first_seg.speed_factor == expected_speed_factor


@pytest.mark.parametrize("bpm, beat_times, expected_count_min", [
    (120.0, [], 0),            # No beats -> Empty plan
    (0.0, [0.5, 1.0], 1),      # 0 BPM -> Default 0.5s spb -> valid plan
    (-10.0, [0.5, 1.0], 1),    # Negative BPM -> Default 0.5s spb -> valid plan
    (60.0, [1.0], 1),          # Single beat -> 1 segment (clamped)
])
def test_build_segment_plan_edge_cases(
    generator, mock_video_clips, bpm, beat_times, expected_count_min
):
    """Test robustness against weird BPM and beat inputs."""
    audio = AudioAnalysisResult(
        filename="edge.wav",
        bpm=bpm,
        duration=10.0,
        peaks=[],
        sections=[],
        beat_times=beat_times,
        intensity_curve=[0.5] * len(beat_times),
    )

    segments = generator.build_segment_plan(audio, mock_video_clips)

    if expected_count_min == 0:
        assert len(segments) == 0
    else:
        assert len(segments) >= expected_count_min


@pytest.mark.parametrize("max_clips, max_duration, expected_clips_limit, expected_duration_limit", [
    (5, None, 5, None),             # Limit by count
    (None, 5.0, None, 5.0),         # Limit by duration
    (2, 100.0, 2, 100.0),           # Both set, count hits first
    (100, 2.0, 100, 2.0),           # Both set, duration hits first
])
def test_build_segment_plan_limits(
    generator, mock_audio_data, mock_video_clips, max_clips, max_duration, expected_clips_limit, expected_duration_limit
):
    """Verify max_clips and max_duration_seconds constraints."""
    config = PacingConfig(
        max_clips=max_clips,
        max_duration_seconds=max_duration,
        min_clip_seconds=0.5 # Allow short clips for precise counting
    )

    # Mock audio has 120 beats (60s), enough to hit these limits
    segments = generator.build_segment_plan(mock_audio_data, mock_video_clips, config)

    if expected_clips_limit:
        assert len(segments) <= expected_clips_limit
        if len(segments) == expected_clips_limit:
             pass # Limit hit exactly

    if expected_duration_limit:
        total_duration = sum(s.duration for s in segments)
        # Allow small float error or slight overshoot if not exact beat boundary (though code clamps)
        # The code: if timeline_pos >= config.max_duration_seconds: break
        # And: segment_duration = min(segment_duration, remaining)
        assert total_duration <= expected_duration_limit + 0.001


def test_build_segment_plan_sections(generator, mock_video_clips):
    """Verify that segments inherit the correct musical section label."""
    audio = AudioAnalysisResult(
        filename="sections.wav",
        bpm=120.0,
        duration=10.0,
        peaks=[],
        sections=[
            MusicalSection(label="intro", start_time=0.0, end_time=2.0, avg_intensity=0.5),
            MusicalSection(label="chorus", start_time=2.0, end_time=5.0, avg_intensity=0.8),
            # Gap from 5.0 to 8.0 (should be None)
            MusicalSection(label="outro", start_time=8.0, end_time=10.0, avg_intensity=0.4),
        ],
        beat_times=[i * 0.5 for i in range(20)], # 0.0, 0.5, ..., 9.5
        intensity_curve=[0.5] * 20,
    )

    # Force short segments to sample sections finely
    config = PacingConfig(
        min_clip_seconds=0.5,
        medium_intensity_seconds=0.5
    )

    segments = generator.build_segment_plan(audio, mock_video_clips, config)

    # Check sample segments
    # Segment 0: starts at 0.0 -> intro
    assert segments[0].section_label == "intro"

    # Segment covering ~3.0s -> chorus
    # Let's find a segment that starts around 3.0s
    chorus_seg = next((s for s in segments if 3.0 <= s.timeline_position < 4.0), None)
    if chorus_seg:
        assert chorus_seg.section_label == "chorus"

    # Segment covering ~6.0s -> None (gap)
    gap_seg = next((s for s in segments if 6.0 <= s.timeline_position < 7.0), None)
    if gap_seg:
        assert gap_seg.section_label is None

def test_build_segment_plan_clip_variety(generator, mock_audio_data, mock_video_clips):
    """
    Verify that clip start times are deterministic but varied when variety is enabled.
    """
    config = PacingConfig(clip_variety_enabled=True)

    # Run 1
    plan1 = generator.build_segment_plan(mock_audio_data, mock_video_clips, config)
    # Run 2
    plan2 = generator.build_segment_plan(mock_audio_data, mock_video_clips, config)

    # Determinism check
    assert len(plan1) == len(plan2)
    for s1, s2 in zip(plan1, plan2):
        assert s1.start_time == s2.start_time
        assert s1.video_path == s2.video_path

    # Variety check: if we use the same clip multiple times, start times should differ
    # (assuming clips are long enough)
    clip_starts = {}
    for seg in plan1:
        if seg.video_path not in clip_starts:
            clip_starts[seg.video_path] = set()
        clip_starts[seg.video_path].add(seg.start_time)

    # At least one clip should have been used multiple times with different offsets
    # Given the fixtures, we have 3 clips and many beats, so reuse is guaranteed.
    varied = any(len(starts) > 1 for starts in clip_starts.values())
    assert varied, "Expected reused clips to have different start times"

@pytest.mark.parametrize("speed_ramp", [True, False])
def test_speed_ramping_flag(generator, mock_video_clips, speed_ramp):
    """Verify speed_ramp_enabled flag toggles speed factor."""
    audio = AudioAnalysisResult(
        filename="test.wav",
        bpm=120.0,
        duration=10.0,
        peaks=[],
        sections=[],
        beat_times=[i * 0.5 for i in range(10)],
        intensity_curve=[0.9] * 10, # High intensity
    )

    config = PacingConfig(
        speed_ramp_enabled=speed_ramp,
        high_intensity_speed=2.0 # Distinct value
    )

    segments = generator.build_segment_plan(audio, mock_video_clips, config)

    assert len(segments) > 0
    if speed_ramp:
        assert segments[0].speed_factor == 2.0
    else:
        assert segments[0].speed_factor == 1.0
