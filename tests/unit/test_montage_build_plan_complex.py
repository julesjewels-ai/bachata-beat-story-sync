import pytest
from src.core.models import (
    AudioAnalysisResult,
    MusicalSection,
    PacingConfig,
    VideoAnalysisResult,
)
from src.core.montage import MontageGenerator


@pytest.fixture
def gen() -> MontageGenerator:
    return MontageGenerator()


@pytest.fixture
def mock_video_clips() -> list[VideoAnalysisResult]:
    return [
        VideoAnalysisResult(
            path="/videos/clip1.mp4",
            intensity_score=0.8,
            duration=10.0,
            thumbnail_data=None,
        ),
        VideoAnalysisResult(
            path="/videos/clip2.mp4",
            intensity_score=0.3,
            duration=10.0,
            thumbnail_data=None,
        ),
    ]


@pytest.fixture
def mock_broll_clips() -> list[VideoAnalysisResult]:
    return [
        VideoAnalysisResult(
            path="/videos/broll1.mp4",
            intensity_score=0.5,
            duration=10.0,
            thumbnail_data=None,
        )
    ]


@pytest.fixture
def mock_audio_data() -> AudioAnalysisResult:
    return AudioAnalysisResult(
        filename="test.wav",
        bpm=120.0,
        duration=10.0,
        peaks=[],
        sections=[
            MusicalSection(
                label="intro",
                start_time=0.0,
                end_time=5.0,
                avg_intensity=0.5,
            ),
            MusicalSection(
                label="outro",
                start_time=5.0,
                end_time=10.0,
                avg_intensity=0.5,
            ),
        ],
        beat_times=[float(i) * 0.5 for i in range(20)],
        intensity_curve=[0.5] * 20,
    )


@pytest.mark.parametrize(
    "pacing_kwargs, audio_kwargs, broll_enabled, expected_len, validation_fn, mock_video_clips_override",
    [
        # Case 1: Hit config.max_clips limit
        (
            {"max_clips": 3},
            {},
            False,
            3,
            lambda segments: len(segments) == 3,
            None,
        ),
        # Case 2: Hit config.max_duration_seconds limit
        (
            {"max_duration_seconds": 2.5, "clip_variety_enabled": False},
            {},
            False,
            None,  # Variable length
            lambda segments: (
                len(segments) > 0
                and sum(s.duration for s in segments) == 2.5
                and segments[-1].duration == 2.5
            ),
            None,
        ),
        # Case 3: Hit intensity_curve fallback (beat_idx >= len(intensity_curve))
        (
            {},
            {"intensity_curve": [0.5]},  # Only 1 element, 20 beats
            False,
            None,
            lambda segments: True,  # Just verify it doesn't crash
            None,
        ),
        # Case 4: Hit sections fallback (time bounds fail)
        (
            {},
            {"sections": []},  # Empty sections
            False,
            None,
            lambda segments: all(s.section_label is None for s in segments),
            None,
        ),
        # Case 5: Hit actual_duration <= 0 (skip segment)
        (
            {"clip_variety_enabled": False},
            {},
            False,
            None,
            lambda segments: True,
            [
                VideoAnalysisResult(
                    path="/videos/clip1.mp4",
                    intensity_score=0.8,
                    duration=0.0,  # Zero duration
                    thumbnail_data=None,
                )
            ],
        ),
        # Case 6: Hit timeline_pos > 0.0 for broll logic
        (
            {"broll_interval_seconds": 1.0, "broll_interval_variance": 0.0},
            {},
            True,
            None,
            lambda segments: (
                any("broll" in s.video_path for s in segments)
                and len(segments) > 0
                and "broll" not in segments[0].video_path
            ),
            None,
        ),
        # Case 7: trigger early exit with max_clips duration bounds
        (
            {"max_clips": 1, "max_duration_seconds": 100},
            {},
            False,
            1,
            lambda segments: len(segments) > 0 and segments[0].duration > 0,
            None,
        ),
        # Case 8: Stop if duration limit hit
        (
            {"max_duration_seconds": 0.0},
            {},
            False,
            0,
            lambda segments: len(segments) == 0,
            None,
        ),
    ],
)
def test_build_segment_plan_complex(
    gen: MontageGenerator,
    mock_video_clips: list[VideoAnalysisResult],
    mock_broll_clips: list[VideoAnalysisResult],
    mock_audio_data: AudioAnalysisResult,
    pacing_kwargs: dict,
    audio_kwargs: dict,
    broll_enabled: bool,
    expected_len: int | None,
    validation_fn,
    mock_video_clips_override: list[VideoAnalysisResult] | None,
) -> None:
    # Arrange
    config = PacingConfig(**pacing_kwargs)

    # Update audio data
    audio_dict = mock_audio_data.model_dump()
    audio_dict.update(audio_kwargs)
    audio_data = AudioAnalysisResult(**audio_dict)

    video_clips = (
        mock_video_clips_override
        if mock_video_clips_override is not None
        else mock_video_clips
    )

    broll = mock_broll_clips if broll_enabled else None

    # Act
    segments = gen.build_segment_plan(
        audio_data, video_clips, pacing=config, broll_clips=broll
    )

    # Assert
    if expected_len is not None:
        assert len(segments) == expected_len, (
            f"Expected length {expected_len}, got {len(segments)}"
        )

    assert validation_fn(segments) is True, "Validation function failed for segments."
