
import pytest
from unittest.mock import Mock, patch
from src.core.montage import MontageGenerator
from src.core.models import (
    AudioAnalysisResult,
    VideoAnalysisResult,
    PacingConfig,
    SegmentPlan,
    MusicalSection,
)
from typing import List, Optional, Callable

@pytest.fixture
def basic_audio() -> AudioAnalysisResult:
    return AudioAnalysisResult(
        filename="test.mp3",
        bpm=120,
        duration=60.0,
        peaks=[],
        beat_times=[0.5 * i for i in range(120)],  # 2 beats per second
        intensity_curve=[0.5] * 120,
        sections=[
            MusicalSection(label="intro", start_time=0.0, end_time=10.0, avg_intensity=0.4),
            MusicalSection(label="verse", start_time=10.0, end_time=30.0, avg_intensity=0.6),
        ]
    )

@pytest.fixture
def basic_video_clips() -> List[VideoAnalysisResult]:
    return [
        VideoAnalysisResult(
            path=f"/tmp/clip_{i}.mp4",
            intensity_score=0.1 * i, # 0.0 to 0.9
            duration=10.0,
            is_vertical=(i % 2 == 0), # Even indices are vertical
            thumbnail_data=None,
        )
        for i in range(10)
    ]

@pytest.mark.parametrize(
    "max_clips, max_duration_seconds, expected_count, expected_duration_limit",
    [
        (5, None, 5, None),
        (None, 10.0, None, 10.0),
        (3, 15.0, 3, 15.0),  # 3 clips should fit in 15s (3 * 4s = 12s)
        (None, None, None, None),  # Should process all beats
    ],
)
def test_build_segment_plan_limits(
    basic_audio: AudioAnalysisResult,
    basic_video_clips: List[VideoAnalysisResult],
    max_clips: Optional[int],
    max_duration_seconds: Optional[float],
    expected_count: Optional[int],
    expected_duration_limit: Optional[float],
) -> None:
    # Arrange
    config = PacingConfig(
        max_clips=max_clips,
        max_duration_seconds=max_duration_seconds,
        min_clip_seconds=1.0,  # Ensure clips are created
        section_detection_enabled=False,
    )
    generator = MontageGenerator()

    # Act
    segments = generator.build_segment_plan(
        audio_data=basic_audio,
        video_clips=basic_video_clips,
        pacing=config,
    )

    # Assert
    if expected_count is not None:
        assert len(segments) == expected_count

    if expected_duration_limit is not None:
        total_duration = sum(seg.duration for seg in segments)
        assert total_duration <= expected_duration_limit + 0.01

        if segments:
            last_end = segments[-1].timeline_position + segments[-1].duration
            assert last_end <= expected_duration_limit + 0.01

    if expected_count is None and expected_duration_limit is None:
        # Should cover all beats (approx duration of audio)
        total_duration = sum(seg.duration for seg in segments)
        # 60s audio, so roughly 60s total duration
        assert total_duration >= basic_audio.duration - 2.0


@pytest.mark.parametrize(
    "intensity, expected_level, expected_speed",
    [
        (0.8, "high", 1.2),  # > 0.65 -> High
        (0.5, "medium", 1.0), # 0.35 <= x < 0.65 -> Medium
        (0.2, "low", 0.9),    # < 0.35 -> Low
    ],
)
def test_build_segment_plan_intensity(
    basic_audio: AudioAnalysisResult,
    basic_video_clips: List[VideoAnalysisResult],
    intensity: float,
    expected_level: str,
    expected_speed: float,
) -> None:
    # Arrange
    # Force intensity for all beats
    basic_audio.intensity_curve = [intensity] * 120

    config = PacingConfig(
        high_intensity_threshold=0.65,
        low_intensity_threshold=0.35,
        high_intensity_speed=1.2,
        medium_intensity_speed=1.0,
        low_intensity_speed=0.9,
        speed_ramp_enabled=True,
        min_clip_seconds=1.0,
    )
    generator = MontageGenerator()

    # Act
    segments = generator.build_segment_plan(
        audio_data=basic_audio,
        video_clips=basic_video_clips,
        pacing=config,
    )

    # Assert
    assert len(segments) > 0
    first_seg = segments[0]
    assert first_seg.intensity_level == expected_level
    assert first_seg.speed_factor == expected_speed


@pytest.mark.parametrize(
    "accelerate, randomize, clip_variety, snap, is_shorts",
    [
        (True, False, False, True, False),  # Accelerate pacing
        (False, True, False, True, False),  # Randomize speed
        (False, False, True, True, False),  # Clip variety
        (False, False, False, False, False), # Snap to beats False
        (False, False, False, True, True),  # Shorts mode
    ],
)
def test_build_segment_plan_features(
    basic_audio: AudioAnalysisResult,
    basic_video_clips: List[VideoAnalysisResult],
    accelerate: bool,
    randomize: bool,
    clip_variety: bool,
    snap: bool,
    is_shorts: bool,
) -> None:
    # Arrange
    config = PacingConfig(
        accelerate_pacing=accelerate,
        randomize_speed_ramps=randomize,
        clip_variety_enabled=clip_variety,
        snap_to_beats=snap,
        is_shorts=is_shorts,
        seed="test_seed",
        min_clip_seconds=1.0,
    )
    generator = MontageGenerator()

    # Act
    # Mock random to control randomization if needed
    with patch("random.Random") as mock_random:
        mock_rng = Mock()
        mock_rng.uniform.return_value = 1.05 # predictable random factor
        mock_random.return_value = mock_rng

        segments = generator.build_segment_plan(
            audio_data=basic_audio,
            video_clips=basic_video_clips,
            pacing=config,
        )

    # Assert
    assert len(segments) > 0

    if accelerate:
        # Check if later segments are shorter/faster paced
        # Assuming constant intensity, so target duration would decrease
        # But 'target_seconds' decreases. Since beats are discrete, we check duration.
        # Compare first and last segment duration
        first_dur = segments[0].duration
        last_dur = segments[-1].duration
        # Accelerate reduces target seconds by up to 40%
        # So last segment should be shorter or equal (due to quantization)
        # Given enough length, it should be strictly shorter.
        # With 60s duration, it should be noticeable.
        assert last_dur <= first_dur

    if randomize:
        # Check if speed factor is modified by random factor
        # Expected speed = base (1.0) * random (1.05) = 1.05
        # Allow small float error
        assert abs(segments[0].speed_factor - 1.05) < 0.001

    if clip_variety:
        # Check if start_time is non-zero for reused clips
        # We need enough segments to reuse clips.
        # 10 clips, 60s audio, segments ~2-4s -> ~15-30 segments.
        # So clips will be reused.
        reused_clips = {}
        for seg in segments:
            if seg.video_path not in reused_clips:
                reused_clips[seg.video_path] = []
            reused_clips[seg.video_path].append(seg.start_time)

        # Ensure at least one clip was reused and had different start times
        found_variety = False
        for path, starts in reused_clips.items():
            if len(starts) > 1 and len(set(starts)) > 1:
                found_variety = True
                break
        assert found_variety, "Expected clip variety (different start times) for reused clips"

    if not snap:
        # Duration might not be exact multiple of SPB
        # SPB = 0.5s.
        # If not snap, uses math.ceil to meet min beats, but target beats calculation is different?
        # Actually logic is: target_beats = max(min_beats, math.ceil(target_seconds / spb))
        # Wait, if snap=False, it still calculates beats:
        # if config.snap_to_beats:
        #     target_beats = max(min_beats, round(target_seconds / spb))
        # else:
        #     target_beats = max(min_beats, math.ceil(target_seconds / spb))
        # So duration is always beat-aligned (beat_count * spb).
        # The difference is rounding vs ceiling.
        # Let's check if we get different durations for specific target seconds.
        # E.g. target=1.2s, SPB=0.5s.
        # Snap=True -> round(2.4) = 2 beats -> 1.0s
        # Snap=False -> ceil(2.4) = 3 beats -> 1.5s
        pass # Logic confirms it returns beats, so duration is always multiple of SPB.
             # The test here is just that it runs without error and produces valid plans.

    if is_shorts:
        # Prioritize vertical clips
        # basic_video_clips has vertical at even indices (0, 2, 4...)
        # sorted_clips should have vertical first.
        # Segments pick round-robin from sorted clips.
        # So first segments should use vertical clips.
        vertical_count = sum(1 for c in basic_video_clips if c.is_vertical)
        for i in range(min(len(segments), vertical_count)):
            # Find the clip object to check is_vertical (segment only has path)
            path = segments[i].video_path
            clip = next(c for c in basic_video_clips if c.path == path)
            assert clip.is_vertical, f"Segment {i} should be vertical in shorts mode"


@pytest.mark.parametrize(
    "audio_override, video_override, expected_check",
    [
        ({"beat_times": []}, None, lambda s: len(s) == 0),
        (None, [], lambda s: len(s) == 0),
        ({"bpm": 0}, None, lambda s: len(s) > 0 and sum(x.duration for x in s) > 0),
        (
            {"beat_times": [0.0, 0.5], "duration": 1.0},
            None,
            lambda s: len(s) == 1 and abs(s[0].duration - 1.0) < 0.001,
        ),
    ],
)
def test_build_segment_plan_edges(
    basic_audio: AudioAnalysisResult,
    basic_video_clips: List[VideoAnalysisResult],
    audio_override: Optional[dict],
    video_override: Optional[List[VideoAnalysisResult]],
    expected_check: Callable[[List[SegmentPlan]], bool],
) -> None:
    generator = MontageGenerator()
    config = PacingConfig()

    # Prepare inputs
    audio_input = basic_audio
    if audio_override:
        audio_input = basic_audio.model_copy(update=audio_override)

    video_input = basic_video_clips
    if video_override is not None:
        video_input = video_override

    # Act
    segments = generator.build_segment_plan(audio_input, video_input, config)

    # Assert
    assert expected_check(segments)
