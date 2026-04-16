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

    # Canary threshold: keep planning and analysis in tight agreement.
    assert gap <= 0.20, (
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

    # Canary threshold allows tiny mux/probe variance while catching regressions.
    assert delta <= 0.25, (
        f"Rendered duration drifted by {delta:.3f}s "
        f"(rendered={rendered_duration:.3f}s, audio={audio_duration:.3f}s)"
    )
