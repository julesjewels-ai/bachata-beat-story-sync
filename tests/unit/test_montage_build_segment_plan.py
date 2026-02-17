import pytest
from src.core.montage import MontageGenerator
from src.core.models import (
    AudioAnalysisResult,
    VideoAnalysisResult,
    PacingConfig,
    SegmentPlan,
    MusicalSection,
)

@pytest.fixture
def montage_generator():
    return MontageGenerator()

@pytest.fixture
def base_audio_data():
    """Provides a basic audio analysis result."""
    return AudioAnalysisResult(
        filename="test_audio.wav",
        bpm=120.0,  # 0.5s per beat
        duration=10.0,
        peaks=[],
        sections=[],
        beat_times=[0.5 * i for i in range(20)], # 20 beats, 10s
        intensity_curve=[0.5] * 20, # Default medium intensity
    )

@pytest.fixture
def base_video_clips():
    """Provides a list of video clips."""
    return [
        VideoAnalysisResult(
            path="clip1.mp4",
            intensity_score=0.8,
            duration=5.0,
            thumbnail_data=None,
        ),
        VideoAnalysisResult(
            path="clip2.mp4",
            intensity_score=0.4,
            duration=5.0,
            thumbnail_data=None,
        ),
    ]

@pytest.mark.parametrize(
    "description, audio_overrides, pacing_overrides, clips_override, expected_checks",
    [
        (
            "Standard: Normal inputs",
            {},
            {},
            None,
            lambda segments: len(segments) > 0
        ),
        (
            "Max Clips: Limit to 1 segment",
            {},
            {"max_clips": 1},
            None,
            lambda segments: len(segments) == 1
        ),
        (
            "Max Duration: Limit to small duration",
            {},
            {"max_duration_seconds": 1.0},
            None,
            lambda segments: 0.9 <= sum(s.duration for s in segments) <= 1.5 # Adjusted for beat snapping
        ),
        (
            "High Intensity: Force high intensity",
            {"intensity_curve": [0.9] * 20},
            {"high_intensity_threshold": 0.8},
            None,
            lambda segments: all(s.intensity_level == "high" for s in segments)
        ),
        (
            "Low Intensity: Force low intensity",
            {"intensity_curve": [0.1] * 20},
            {"low_intensity_threshold": 0.2},
            None,
            lambda segments: all(s.intensity_level == "low" for s in segments)
        ),
        (
            "No Speed Ramp: Speed should be 1.0",
            {},
            {"speed_ramp_enabled": False},
            None,
            lambda segments: all(s.speed_factor == 1.0 for s in segments)
        ),
        (
            "No Snap to Beats: Duration logic changes",
            {},
            {"snap_to_beats": False},
            None,
            lambda segments: len(segments) > 0
        ),
        (
            "Zero BPM: Fallback to 0.5s per beat",
            {"bpm": 0.0},
            {},
            None,
            lambda segments: len(segments) > 0
        ),
        (
            "No Video Clips: Empty list",
            {},
            {},
            [],
            lambda segments: segments == []
        ),
        (
            "No Audio Beats: Empty list",
            {"beat_times": []},
            {},
            None,
            lambda segments: segments == []
        ),
        (
            "With Sections: Should assign section labels",
            {
                "sections": [
                    MusicalSection(
                        label="intro",
                        start_time=0.0,
                        end_time=5.0,
                        avg_intensity=0.5
                    )
                ]
            },
            {},
            None,
            lambda segments: any(s.section_label == "intro" for s in segments)
        ),
        (
            "Mismatched Intensity: Curve shorter than beats",
            {"intensity_curve": [0.5] * 10}, # 10 intensity points, 20 beats
            {},
            None,
            lambda segments: len(segments) > 0 # Should fallback to 0.5 intensity and continue
        ),
    ]
)
def test_build_segment_plan_logic(
    montage_generator,
    base_audio_data,
    base_video_clips,
    description,
    audio_overrides,
    pacing_overrides,
    clips_override,
    expected_checks
):
    # Apply overrides
    audio_data = base_audio_data.model_copy(update=audio_overrides)
    pacing = PacingConfig(**pacing_overrides)
    video_clips = clips_override if clips_override is not None else base_video_clips

    # Act
    segments = montage_generator.build_segment_plan(audio_data, video_clips, pacing)

    # Assert
    assert expected_checks(segments), f"Failed: {description}"
