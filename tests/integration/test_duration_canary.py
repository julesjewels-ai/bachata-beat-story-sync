"""End-to-end duration and coverage canaries with tiny real media."""

from __future__ import annotations

from pathlib import Path

from src.application.story_workflow import run_story_workflow
from src.core.ffmpeg_renderer import get_video_duration

# Stable pacing overrides for deterministic canary behavior.
_CANARY_PACING = {
    "speed_ramp_enabled": False,
    "min_clip_seconds": 0.25,
    "clip_variety_enabled": False,
    "seed": "integration-canary",
}


def test_dry_run_segment_plan_covers_audio(
    synthetic_story_media: dict[str, str],
) -> None:
    """Canary: dry-run plan should cover full synthetic audio timeline."""
    result = run_story_workflow(
        synthetic_story_media["audio_path"],
        synthetic_story_media["clips_dir"],
        "unused.mp4",
        pacing_overrides={**_CANARY_PACING, "dry_run": True},
    )

    assert result.plan_report is not None
    assert result.segments, "Expected non-empty segment plan for click-track audio"

    planned_duration = (
        result.segments[-1].timeline_position + result.segments[-1].duration
    )
    audio_duration = float(synthetic_story_media["audio_duration"])
    gap = abs(audio_duration - planned_duration)

    # Canary threshold: dry-run should align tightly to target contract.
    assert gap <= 0.10, (
        f"Dry-run plan drifted by {gap:.3f}s "
        f"(planned={planned_duration:.3f}s, audio={audio_duration:.3f}s)"
    )


def test_rendered_output_duration_matches_audio(
    synthetic_story_media: dict[str, str],
    tmp_path: Path,
) -> None:
    """Canary: rendered output duration should remain aligned to source audio."""
    output_path = tmp_path / "story_canary.mp4"
    result = run_story_workflow(
        synthetic_story_media["audio_path"],
        synthetic_story_media["clips_dir"],
        str(output_path),
        pacing_overrides=_CANARY_PACING,
    )

    assert result.output_path is not None
    assert output_path.exists()

    rendered_duration = get_video_duration(str(output_path))
    audio_duration = result.audio_meta.duration
    delta = abs(rendered_duration - audio_duration)

    assert delta <= 0.10, (
        f"Rendered duration drifted by {delta:.3f}s "
        f"(rendered={rendered_duration:.3f}s, audio={audio_duration:.3f}s)"
    )


def test_rendered_output_duration_matches_audio_with_transitions(
    synthetic_story_media: dict[str, str],
    tmp_path: Path,
) -> None:
    """Canary: transition overlap compensation keeps final render aligned."""
    dry_result = run_story_workflow(
        synthetic_story_media["sectioned_audio_path"],
        synthetic_story_media["clips_dir"],
        "unused.mp4",
        pacing_overrides={
            **_CANARY_PACING,
            "dry_run": True,
            "transition_type": "fade",
            "transition_duration": 0.5,
        },
    )
    assert dry_result.segments
    group_count = 1
    current_label = dry_result.segments[0].section_label
    for segment in dry_result.segments[1:]:
        if segment.section_label != current_label:
            group_count += 1
            current_label = segment.section_label
    assert group_count > 1, "Expected transition canary to plan multiple groups"

    output_path = tmp_path / "story_canary_transitions.mp4"
    result = run_story_workflow(
        synthetic_story_media["sectioned_audio_path"],
        synthetic_story_media["clips_dir"],
        str(output_path),
        pacing_overrides={
            **_CANARY_PACING,
            "transition_type": "fade",
            "transition_duration": 0.5,
        },
    )

    assert result.output_path is not None
    assert output_path.exists()

    rendered_duration = get_video_duration(str(output_path))
    audio_duration = result.audio_meta.duration
    delta = abs(rendered_duration - audio_duration)

    assert delta <= 0.10, (
        f"Transition render drifted by {delta:.3f}s "
        f"(rendered={rendered_duration:.3f}s, audio={audio_duration:.3f}s)"
    )


def test_dry_run_short_footage_stress_stays_aligned(
    synthetic_story_media: dict[str, str],
) -> None:
    """Canary: adaptive fill should keep short-footage plans aligned."""
    result = run_story_workflow(
        synthetic_story_media["audio_path"],
        synthetic_story_media["short_clips_dir"],
        "unused.mp4",
        pacing_overrides={
            **_CANARY_PACING,
            "dry_run": True,
            "speed_ramp_enabled": True,
            "high_intensity_threshold": 0.0,
            "low_intensity_threshold": -1.0,
            "high_intensity_speed": 1.4,
            "medium_intensity_speed": 1.3,
            "low_intensity_speed": 1.2,
            "clip_variety_enabled": True,
        },
    )

    assert result.segments, "Expected non-empty plan in short-footage stress canary"
    planned_duration = (
        result.segments[-1].timeline_position + result.segments[-1].duration
    )
    audio_duration = float(synthetic_story_media["audio_duration"])
    delta = abs(planned_duration - audio_duration)
    assert delta <= 0.10, (
        f"Short-footage dry-run drifted by {delta:.3f}s "
        f"(planned={planned_duration:.3f}s, audio={audio_duration:.3f}s)"
    )
