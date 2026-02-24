
import pytest
from typing import List, Callable, Any

from src.core.montage import MontageGenerator
from src.core.models import (
    AudioAnalysisResult,
    VideoAnalysisResult,
    PacingConfig,
    SegmentPlan,
)


@pytest.fixture
def generator() -> MontageGenerator:
    """Fixture for MontageGenerator."""
    return MontageGenerator()


@pytest.fixture
def base_audio() -> AudioAnalysisResult:
    """Fixture for a standard AudioAnalysisResult."""
    # 120 BPM => 0.5s per beat
    # Duration 30s => 60 beats
    bpm = 120.0
    duration = 30.0
    beat_count = int(duration * (bpm / 60.0))
    beat_times = [i * (60.0 / bpm) for i in range(beat_count)]

    # Alternating intensity: Low, Medium, High, Low, Medium, High...
    # Low (<0.35), Medium (0.35-0.65), High (>=0.65)
    intensity_curve = []
    for i in range(beat_count):
        if i % 3 == 0:
            intensity_curve.append(0.2)  # Low
        elif i % 3 == 1:
            intensity_curve.append(0.5)  # Medium
        else:
            intensity_curve.append(0.8)  # High

    return AudioAnalysisResult(
        filename="test_audio.wav",
        bpm=bpm,
        duration=duration,
        peaks=[],
        sections=[],
        beat_times=beat_times,
        intensity_curve=intensity_curve,
    )


@pytest.fixture
def mixed_clips() -> List[VideoAnalysisResult]:
    """Fixture for video clips with mixed orientation and intensity."""
    return [
        VideoAnalysisResult(
            path="/videos/h_high.mp4",
            intensity_score=0.9,
            duration=10.0,
            is_vertical=False,
            thumbnail_data=None,
        ),
        VideoAnalysisResult(
            path="/videos/v_high.mp4",
            intensity_score=0.9,
            duration=10.0,
            is_vertical=True,  # Vertical!
            thumbnail_data=None,
        ),
        VideoAnalysisResult(
            path="/videos/h_low.mp4",
            intensity_score=0.2,
            duration=10.0,
            is_vertical=False,
            thumbnail_data=None,
        ),
        VideoAnalysisResult(
            path="/videos/v_low.mp4",
            intensity_score=0.2,
            duration=10.0,
            is_vertical=True,  # Vertical!
            thumbnail_data=None,
        ),
    ]


def _assert_max_clips(segments: List[SegmentPlan], audio: Any, config: Any) -> bool:
    return len(segments) == 2


def _assert_max_duration(segments: List[SegmentPlan], audio: Any, config: Any) -> bool:
    total_dur = sum(s.duration for s in segments)
    # Check total duration is within limit + epsilon
    is_within_limit = total_dur <= 5.0 + 0.001
    # Check last segment was trimmed (original duration was likely longer)
    # At 120 BPM, default segments are > 1s.
    last_seg_trimmed = segments[-1].duration < 10.0
    return is_within_limit and last_seg_trimmed


def _assert_accelerate_pacing(segments: List[SegmentPlan], audio: Any, config: Any) -> bool:
    # Compare two segments with same intensity level but different times.
    # Find all 'medium' segments.
    mediums = [s for s in segments if s.intensity_level == 'medium']
    if len(mediums) < 2:
        return False
    # With acceleration, the later one should be shorter.
    return mediums[0].duration > mediums[-1].duration


def _assert_randomize_speed(segments: List[SegmentPlan], audio: Any, config: Any) -> bool:
    # Check if any segment has a speed factor that is NOT exactly 1.5, 1.0, or 0.9
    # This implies randomization happened.
    # The default speeds are modified by uniform(0.9, 1.1)
    return any(
        abs(s.speed_factor - 1.5) > 0.0001 and
        abs(s.speed_factor - 1.0) > 0.0001 and
        abs(s.speed_factor - 0.9) > 0.0001
        for s in segments
    )


class TestMontageBuildPlanExtended:
    """Extended tests for MontageGenerator.build_segment_plan covering edge cases."""

    def test_is_shorts_prioritizes_vertical_clips(
        self, generator: MontageGenerator, base_audio: AudioAnalysisResult, mixed_clips: List[VideoAnalysisResult]
    ) -> None:
        """
        Verify that when is_shorts=True, vertical clips are prioritized.

        The sorting key is (c.is_vertical, c.intensity_score), descending.
        So:
        1. Vertical, High Intensity
        2. Vertical, Low Intensity
        3. Horizontal, High Intensity
        4. Horizontal, Low Intensity
        """
        config = PacingConfig(is_shorts=True)

        # We need enough beats to use all clips at least once to verify order
        # With default pacing, segments are ~2-6s.
        # We just need to check the order of clips assigned.

        segments = generator.build_segment_plan(base_audio, mixed_clips, config)

        # Extract the unique video paths used in order of first appearance
        used_paths = []
        seen = set()
        for seg in segments:
            if seg.video_path not in seen:
                seen.add(seg.video_path)
                used_paths.append(seg.video_path)

        # Expected order based on sorting:
        expected_order = [
            "/videos/v_high.mp4",  # Vertical, High (0.9)
            "/videos/v_low.mp4",   # Vertical, Low (0.2)
            "/videos/h_high.mp4",  # Horizontal, High (0.9)
            "/videos/h_low.mp4",   # Horizontal, Low (0.2)
        ]

        # Check the first N unique clips match the expected order
        # Note: Depending on segment count, we might not see all clips,
        # but the first ones should be the vertical ones.
        assert len(used_paths) >= 2, "Should have used at least 2 unique clips"
        assert used_paths[0] == expected_order[0]
        assert used_paths[1] == expected_order[1]

    @pytest.mark.parametrize("scenario, config_overrides, assertion_callback", [
        ("Max Clips Limit", {"max_clips": 2}, _assert_max_clips),
        ("Max Duration Limit", {"max_duration_seconds": 5.0}, _assert_max_duration),
        ("Accelerate Pacing", {"accelerate_pacing": True, "min_clip_seconds": 0.5}, _assert_accelerate_pacing),
        (
            "Randomize Speed Ramps",
            {"randomize_speed_ramps": True, "speed_ramp_enabled": True, "high_intensity_speed": 1.5},
            _assert_randomize_speed
        ),
    ])
    def test_build_segment_plan_scenarios(
        self,
        generator: MontageGenerator,
        base_audio: AudioAnalysisResult,
        mixed_clips: List[VideoAnalysisResult],
        scenario: str,
        config_overrides: dict,
        assertion_callback: Callable[[List[SegmentPlan], Any, Any], bool],
    ) -> None:
        """Parametrized test for various PacingConfig scenarios."""
        config = PacingConfig(**config_overrides)
        segments = generator.build_segment_plan(base_audio, mixed_clips, config)

        assert assertion_callback(segments, base_audio, config), f"Failed scenario: {scenario}"

    def test_snap_to_beats_false(
        self, generator: MontageGenerator, base_audio: AudioAnalysisResult, mixed_clips: List[VideoAnalysisResult]
    ) -> None:
        """
        Test snap_to_beats=False.

        When False, target_beats = max(min_beats, math.ceil(target_seconds / spb)).
        When True (default), target_beats = max(min_beats, round(target_seconds / spb)).

        We need a case where round() and ceil() differ.
        BPM=120, SPB=0.5.
        Let target_seconds = 2.1.
        2.1 / 0.5 = 4.2.
        round(4.2) = 4.
        ceil(4.2) = 5.
        """
        # Override config to hit the edge case
        config = PacingConfig(
            snap_to_beats=False,
            high_intensity_seconds=2.1, # 4.2 beats
            min_clip_seconds=0.5
        )

        # Force high intensity audio
        audio = base_audio.model_copy()
        audio.intensity_curve = [0.9] * len(audio.beat_times) # All high

        segments = generator.build_segment_plan(audio, mixed_clips, config)

        # Check the first segment duration
        # With snap_to_beats=False: ceil(2.1/0.5) = 5 beats. 5 * 0.5 = 2.5s.
        # With snap_to_beats=True: round(2.1/0.5) = 4 beats. 4 * 0.5 = 2.0s.

        first_segment = segments[0]
        expected_duration = 5 * (60.0 / 120.0) # 2.5

        assert abs(first_segment.duration - expected_duration) < 0.001, (
            f"Expected duration {expected_duration}, got {first_segment.duration}"
        )
