import pytest
from src.core.models import (
    AudioAnalysisResult,
    PacingConfig,
    VideoAnalysisResult,
)
from src.core.montage import MontageGenerator


@pytest.fixture
def clean_audio() -> AudioAnalysisResult:
    return AudioAnalysisResult(
        filename="test.wav",
        duration=30.0,
        bpm=120.0,
        beat_times=[x * 0.5 for x in range(60)],  # 0.0, 0.5, 1.0 ... 29.5
        intensity_curve=[0.5] * 60,
        sections=[],
        peaks=[],
    )


@pytest.fixture
def clean_videos() -> list[VideoAnalysisResult]:
    return [
        VideoAnalysisResult(
            path=f"clip{i}.mp4",
            intensity_score=0.8 - (i * 0.1),
            duration=10.0,
            is_vertical=False,
            scene_changes=[],
        )
        for i in range(3)
    ]


@pytest.fixture
def broll_videos() -> list[VideoAnalysisResult]:
    return [
        VideoAnalysisResult(
            path="broll1.mp4",
            intensity_score=0.5,
            duration=5.0,
            is_vertical=False,
            scene_changes=[],
        )
    ]


@pytest.fixture
def clean_config() -> PacingConfig:
    return PacingConfig(
        max_duration_seconds=30.0,
        broll_interval_seconds=5.0,
        broll_interval_variance=0.0,
        speed_ramp_organic=True,
        explain=True,
        duration_sync_tolerance_seconds=0.1,
        min_clip_seconds=1.0,
        audio_start_offset=0.0,
        max_clips=None,
    )


@pytest.mark.parametrize(
    "scenario, changes, expected_count_op, expected_count_val",
    [
        ("no_videos", {"videos": []}, "eq", 0),
        ("no_beats", {"audio_beats": []}, "eq", 0),
        ("zero_target_duration", {"config_max_duration": 0.0}, "eq", 0),
        ("max_clips_limit", {"config_max_clips": 2}, "eq", 2),
        ("missing_intensity", {"short_intensity": True}, "gt", 5),
        ("with_broll", {"use_broll": True}, "gt", 5),
        (
            "insufficient_beats_for_clip",
            {"audio_beats": [0.0, 0.5], "config_max_duration": 1.0},
            "gt",
            0,
        ),  # Only beats at the start, min clip triggers exit or tail
        ("speed_ramp_disabled", {"speed_ramp": False}, "gt", 5),
        ("transition_overlap", {"transition_overlap": True}, "gt", 5),
    ],
)
def test_build_segment_plan_edge_cases(
    clean_audio: AudioAnalysisResult,
    clean_videos: list[VideoAnalysisResult],
    broll_videos: list[VideoAnalysisResult],
    clean_config: PacingConfig,
    scenario: str,
    changes: dict,
    expected_count_op: str,
    expected_count_val: int,
) -> None:
    # Arrange
    generator = MontageGenerator()

    videos = clean_videos if changes.get("videos") is None else changes["videos"]
    broll = broll_videos if changes.get("use_broll") else None

    if "audio_beats" in changes:
        clean_audio.beat_times = changes["audio_beats"]
    if "config_max_duration" in changes:
        clean_config.max_duration_seconds = changes["config_max_duration"]
    if "config_max_clips" in changes:
        clean_config.max_clips = changes["config_max_clips"]
    if "short_intensity" in changes:
        clean_audio.intensity_curve = [0.5, 0.6]  # Way shorter than beats
    if "speed_ramp" in changes:
        clean_config.speed_ramp_organic = changes["speed_ramp"]
    if "transition_overlap" in changes:
        clean_config.intro_effect = (
            "bloom"  # Just to ensure we trigger overlap compensation branch if any
        )
        # The overlap compensation requires some duration
        clean_config.duration_sync_tolerance_seconds = 0.5

    # Act
    segments = generator.build_segment_plan(
        audio_data=clean_audio,
        video_clips=videos,
        pacing=clean_config,
        broll_clips=broll,
    )

    # Assert
    if expected_count_op == "eq":
        assert len(segments) == expected_count_val, (
            f"Failed on {scenario}: expected {expected_count_val}, got {len(segments)}"
        )
    elif expected_count_op == "gt":
        err_msg = (
            f"Failed on {scenario}: "
            f"expected > {expected_count_val}, got {len(segments)}"
        )
        assert len(segments) > expected_count_val, err_msg
