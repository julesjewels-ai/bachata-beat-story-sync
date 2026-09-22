import pytest
from pytest_mock import MockerFixture
from src.core.models import PacingConfig, VideoAnalysisResult
from src.core.montage import MontageGenerator, planning_config_from_pacing
from src.core.pacing_views import PlanningConfig


@pytest.fixture
def generator() -> MontageGenerator:
    return MontageGenerator()


@pytest.fixture
def candidate_clips() -> list[VideoAnalysisResult]:
    return [
        VideoAnalysisResult(path="clip1.mp4", intensity_score=0.5, duration=10.0),
        VideoAnalysisResult(path="clip2.mp4", intensity_score=0.5, duration=10.0),
        VideoAnalysisResult(path="clip3.mp4", intensity_score=0.5, duration=10.0),
    ]


@pytest.fixture
def planning_config() -> "PlanningConfig":
    pacing = PacingConfig(duration_sync_tolerance_seconds=0.1, min_clip_seconds=1.0)
    return planning_config_from_pacing(pacing)


@pytest.mark.parametrize(
    "scenario, fit_returns, expected_clip_idx, expected_desc",
    [
        (
            "branch1_primary_no_force_zero",
            [(0.0, 5.0)],
            0,
            None,
        ),
        (
            "branch2_primary_force_zero",
            [(0.0, 0.5), (0.0, 5.0)],
            0,
            "Adaptive fit: safer start offset",
        ),
        (
            "branch3_alternate_clip",
            [(0.0, 0.5), (0.0, 0.5), (0.0, 5.0)],
            1,
            "Adaptive fit: alternate clip",
        ),
        (
            "branch4_reduced_speed",
            [(0.0, 0.5), (0.0, 0.5), (0.0, 0.5), (0.0, 0.5), (0.0, 5.0)],
            0,
            "Adaptive fit: reduced speed aggressiveness",
        ),
        (
            "branch5_recovery_clip",
            [
                (0.0, 0.5),
                (0.0, 0.5),
                (0.0, 0.5),
                (0.0, 0.5),
                (0.0, 0.5),
                (0.0, 0.5),
                (0.0, 5.0),
            ],
            0,
            "Adaptive fit: short recovery segment",
        ),
        (
            "branch6_fallback_none",
            [(0.0, 0.1)] * 20,
            None,
            None,
        ),
    ],
)
def test_fit_segment_adaptive_branches(
    generator: MontageGenerator,
    candidate_clips: list[VideoAnalysisResult],
    planning_config: "PlanningConfig",
    mocker: MockerFixture,
    scenario: str,
    fit_returns: list[tuple[float, float]],
    expected_clip_idx: int | None,
    expected_desc: str | None,
) -> None:
    # Mock _fit_clip_for_duration to return specific values
    mocker.patch.object(
        generator, "_fit_clip_for_duration", side_effect=fit_returns + [(0.0, 0.0)] * 10
    )

    desired_duration = 5.0
    base_speed = 1.5
    remaining = 5.0
    clip_idx = 0

    result = generator._fit_segment_adaptive(
        candidate_clips=candidate_clips,
        desired_duration=desired_duration,
        base_speed=base_speed,
        remaining=remaining,
        config=planning_config,
        clip_idx=clip_idx,
    )

    err_msg = f"Failed scenario: {scenario}"
    if expected_clip_idx is None:
        assert result is None, err_msg
    else:
        assert result is not None, err_msg
        assert result.clip == candidate_clips[expected_clip_idx], err_msg

        if expected_desc is not None:
            assert result.reason_suffix == expected_desc, err_msg
