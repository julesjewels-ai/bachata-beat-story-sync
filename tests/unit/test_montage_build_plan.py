"""
Unit tests for MontageGenerator.build_segment_plan (Parametrized).

These tests target specific complex branches:
- max_duration_seconds limits (lines 139, 173)
- intensity_curve index out of bounds (line 146)
- clip_variety_enabled with max_start > 0 (lines 181-182)
"""
import pytest
from typing import List, Optional
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
def mock_clips() -> List[VideoAnalysisResult]:
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


@pytest.mark.parametrize(
    "beat_times, intensity_curve, max_duration, expected_segments_count, expected_last_duration",
    [
        # Case 1: No limit (control)
        ([0.5, 1.0, 1.5, 2.0], [0.5, 0.5, 0.5, 0.5], None, 4, 0.5),
        # Case 2: Exact limit match (2.0s)
        ([0.5, 1.0, 1.5, 2.0], [0.5, 0.5, 0.5, 0.5], 2.0, 4, 0.5),
        # Case 3: Limit hit mid-segment (trim last segment)
        # 4 beats = 2.0s total. Limit 1.8s. Last segment starts at 1.5s, duration 0.5s -> trimmed to 0.3s
        ([0.5, 1.0, 1.5, 2.0], [0.5, 0.5, 0.5, 0.5], 1.8, 4, 0.3),
        # Case 4: Limit hit exactly at segment boundary (stop early)
        # Limit 1.0s. Should stop after 2 segments (0.5s each).
        ([0.5, 1.0, 1.5, 2.0], [0.5, 0.5, 0.5, 0.5], 1.0, 2, 0.5),
         # Case 5: Limit hit before any segment completes (trim first segment)
        ([0.5, 1.0], [0.5, 0.5], 0.2, 1, 0.2),
    ],
)
def test_build_plan_duration_limits(
    generator: MontageGenerator,
    mock_clips: List[VideoAnalysisResult],
    beat_times: List[float],
    intensity_curve: List[float],
    max_duration: Optional[float],
    expected_segments_count: int,
    expected_last_duration: float,
) -> None:
    """
    Tests max_duration_seconds logic (lines 139, 173).
    Ensures segments are trimmed or loop breaks when limit is reached.
    """
    # Force 1 beat per segment for simplicity (min_clip_seconds=0.1)
    config = PacingConfig(
        max_duration_seconds=max_duration,
        min_clip_seconds=0.1,  # Allow very short clips
        snap_to_beats=True,
        medium_intensity_seconds=0.5, # 1 beat at 120 BPM (0.5s)
    )

    audio = AudioAnalysisResult(
        filename="test.wav",
        bpm=120.0, # 0.5s per beat
        duration=10.0,
        peaks=[],
        sections=[],
        beat_times=beat_times,
        intensity_curve=intensity_curve,
    )

    segments = generator.build_segment_plan(audio, mock_clips, config)

    assert len(segments) == expected_segments_count
    if segments:
        assert abs(segments[-1].duration - expected_last_duration) < 0.001

        # Verify total duration does not exceed limit (if set)
        total_dur = segments[-1].timeline_position + segments[-1].duration
        if max_duration:
            assert total_dur <= max_duration + 0.001


@pytest.mark.parametrize(
    "beat_count, intensity_count",
    [
        (10, 5),   # More beats than intensity values
        (10, 0),   # No intensity values at all
        (5, 5),    # Equal length (control)
    ],
)
def test_build_plan_intensity_mismatch(
    generator: MontageGenerator,
    mock_clips: List[VideoAnalysisResult],
    beat_count: int,
    intensity_count: int,
) -> None:
    """
    Tests intensity_curve index out of bounds (line 146).
    Should default to 0.5 intensity if index is out of range.
    """
    beat_times = [float(i) * 0.5 for i in range(beat_count)]
    intensity_curve = [0.8] * intensity_count

    audio = AudioAnalysisResult(
        filename="mismatch.wav",
        bpm=120.0,
        duration=10.0,
        peaks=[],
        sections=[],
        beat_times=beat_times,
        intensity_curve=intensity_curve,
    )

    # Use default config
    segments = generator.build_segment_plan(audio, mock_clips)

    assert len(segments) > 0

    # Specifically check the intensity level of segments corresponding to missing data
    # If index >= len(intensity_curve), it defaults to 0.5 (medium)
    if beat_count > intensity_count:
        current_beat = 0
        for seg in segments:
            start_beat = current_beat
            duration_beats = round(seg.duration / 0.5)
            end_beat = current_beat + duration_beats

            if start_beat >= intensity_count:
                 assert seg.intensity_level == "medium", (
                     f"Segment starting at beat {start_beat} should be medium (default)"
                 )

            current_beat = end_beat


@pytest.mark.parametrize(
    "clip_variety, clip_duration, expected_start_nonzero",
    [
        (True, 30.0, True),   # Enabled, long clip -> should vary
        (False, 30.0, False), # Disabled -> always 0
        (True, 0.5, False),   # Enabled, short clip (== segment duration) -> 0
    ],
)
def test_build_plan_clip_variety_logic(
    generator: MontageGenerator,
    clip_variety: bool,
    clip_duration: float,
    expected_start_nonzero: bool,
) -> None:
    """
    Tests clip_variety_enabled logic (lines 181-182).
    Ensures start_time is calculated only when enabled and possible.
    """
    config = PacingConfig(
        clip_variety_enabled=clip_variety,
        min_clip_seconds=0.5,
        medium_intensity_seconds=0.5,
    )

    # 1 beat, 0.5s duration
    audio = AudioAnalysisResult(
        filename="test.wav",
        bpm=120.0,
        duration=10.0,
        peaks=[],
        sections=[],
        beat_times=[0.0, 0.5], # 2 beats
        intensity_curve=[0.5, 0.5],
    )

    clips = [
        VideoAnalysisResult(
            path="/videos/clip1.mp4",
            intensity_score=0.5,
            duration=clip_duration,
            thumbnail_data=None,
        )
    ]

    segments = generator.build_segment_plan(audio, clips, config)

    assert len(segments) > 0
    first_seg = segments[0]

    if expected_start_nonzero:
        # Check that it varies (is non-zero) and is within bounds
        max_start = clip_duration - first_seg.duration
        assert first_seg.start_time > 0.0, "Start time should be non-zero when variety is enabled"
        assert first_seg.start_time <= max_start
    else:
        assert first_seg.start_time == 0.0


def test_build_plan_max_clips(
    generator: MontageGenerator,
    mock_clips: List[VideoAnalysisResult]
) -> None:
    """
    Tests max_clips limit (lines 138-139).
    """
    config = PacingConfig(
        max_clips=2,
        min_clip_seconds=0.5,
        snap_to_beats=True,
        medium_intensity_seconds=0.5  # 1 beat per segment
    )

    # Audio with enough beats for 4 segments
    audio = AudioAnalysisResult(
        filename="test.wav",
        bpm=120.0,
        duration=10.0,
        peaks=[],
        sections=[],
        beat_times=[0.0, 0.5, 1.0, 1.5], # 4 beats
        intensity_curve=[0.5] * 4,
    )

    # 1 beat per segment (0.5s)
    segments = generator.build_segment_plan(audio, mock_clips, config)

    assert len(segments) == 2


def test_build_plan_no_snap_to_beats(
    generator: MontageGenerator,
    mock_clips: List[VideoAnalysisResult]
) -> None:
    """
    Tests snap_to_beats=False (lines 172-173).
    """
    config = PacingConfig(
        snap_to_beats=False,
        min_clip_seconds=0.5,
        medium_intensity_seconds=0.75 # 1.5 beats
    )

    audio = AudioAnalysisResult(
        filename="test.wav",
        bpm=120.0, # spb = 0.5
        duration=10.0,
        peaks=[],
        sections=[],
        beat_times=[0.0, 0.5, 1.0, 1.5],
        intensity_curve=[0.5] * 4,
    )

    # With snap_to_beats=False, target_beats = ceil(0.75 / 0.5) = ceil(1.5) = 2.
    # With snap_to_beats=True, target_beats = round(1.5) = 2.

    config.medium_intensity_seconds = 0.6
    segments = generator.build_segment_plan(audio, mock_clips, config)

    # Should result in 2 beats per segment (1.0s) because ceil(0.6/0.5) = 2
    assert segments[0].duration == 1.0


@pytest.mark.parametrize("intensity_val, expected_level", [
    (0.9, "high"),
    (0.1, "low"),
])
def test_build_plan_intensity_thresholds(
    generator: MontageGenerator,
    mock_clips: List[VideoAnalysisResult],
    intensity_val: float,
    expected_level: str
) -> None:
    """
    Tests high/low intensity branches (lines 156-163).
    """
    config = PacingConfig() # Defaults: high >= 0.65, low < 0.35

    audio = AudioAnalysisResult(
        filename="test.wav",
        bpm=120.0,
        duration=10.0,
        peaks=[],
        sections=[],
        beat_times=[0.0],
        intensity_curve=[intensity_val],
    )

    segments = generator.build_segment_plan(audio, mock_clips, config)
    assert len(segments) == 1
    assert segments[0].intensity_level == expected_level


def test_build_plan_empty_inputs(
    generator: MontageGenerator,
    mock_clips: List[VideoAnalysisResult]
) -> None:
    """
    Tests empty input edge cases (lines 107, 113).
    """
    audio = AudioAnalysisResult(
        filename="test.wav",
        bpm=120.0,
        duration=10.0,
        peaks=[],
        sections=[],
        beat_times=[], # Empty beats
        intensity_curve=[],
    )

    # Empty clips
    assert generator.build_segment_plan(audio, []) == []

    # Empty beats
    assert generator.build_segment_plan(audio, mock_clips) == []
