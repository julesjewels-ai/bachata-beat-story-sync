"""Unit tests for Streamlit request-building helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from src.application.streamlit_requests import (
    build_pacing_kwargs,
    prepare_run_request,
    resolve_output_targets,
    should_trigger_demo_run,
)
from src.ui.settings_form import GenerationSettings


def test_should_trigger_demo_run_requires_demo_flag_and_session_marker():
    """Demo auto-run should only trigger when the session marker is present."""
    state = SimpleNamespace(
        demo_mode=True,
        result_path=None,
        plan_report=None,
        error=None,
        is_running=False,
    )

    with patch(
        "src.application.streamlit_requests.st.session_state",
        {"_demo_dry_run": True},
    ):
        assert should_trigger_demo_run(state) is True

    with patch("src.application.streamlit_requests.st.session_state", {}):
        assert should_trigger_demo_run(state) is False


def test_build_pacing_kwargs_applies_demo_overrides():
    """Demo mode should enforce its protected pacing defaults."""
    settings = GenerationSettings(
        genre_choice="bachata",
        video_style="warm",
        transition_type="fade",
        intro_effect="bloom",
    )

    result = build_pacing_kwargs(
        settings,
        demo_mode=True,
        demo_dry_run=True,
    )

    assert result["genre"] == "bachata"
    assert result["video_style"] == "warm"
    assert result["transition_type"] == "fade"
    assert result["intro_effect"] == "bloom"
    assert result["dry_run"] is True
    assert result["max_clips"] == 6
    assert result["max_duration_seconds"] == 20.0
    assert result["text_overlay_enabled"] is True
    assert result["track_artist"] == "Sample Artist"
    assert result["track_title"] == "Sample Bachata"


def test_build_pacing_kwargs_applies_manual_limits_effects_and_text():
    """Manual runs should map advanced settings into pacing kwargs consistently."""
    settings = GenerationSettings(
        test_mode=True,
        max_clips_input=7,
        max_duration_input=15,
        dry_run=True,
        speed_ramp_organic=True,
        speed_ramp_sensitivity=1.5,
        speed_ramp_curve="ease_out",
        speed_ramp_min=0.7,
        speed_ramp_max=1.4,
        pacing_drift_zoom=True,
        pacing_light_leaks=True,
        text_overlay_enabled=True,
        cold_open_enabled=False,
        lyrics_overlay_enabled=False,
        track_artist="  Artist  ",
        track_title=" Song ",
    )

    result = build_pacing_kwargs(
        settings,
        demo_mode=False,
        demo_dry_run=False,
    )

    assert result["dry_run"] is True
    assert result["max_clips"] == 7
    assert result["max_duration_seconds"] == 15.0
    assert result["speed_ramp_organic"] is True
    assert result["speed_ramp_sensitivity"] == 1.5
    assert result["speed_ramp_curve"] == "ease_out"
    assert result["speed_ramp_min"] == 0.7
    assert result["speed_ramp_max"] == 1.4
    assert result["pacing_drift_zoom"] is True
    assert result["pacing_light_leaks"] is True
    assert result["text_overlay_enabled"] is True
    assert result["cold_open_enabled"] is False
    assert result["lyrics_overlay_enabled"] is False
    assert result["track_artist"] == "Artist"
    assert result["track_title"] == "Song"


def test_resolve_output_targets_uses_demo_temp_output_and_report_suffix():
    """Demo renders should get a temp video path and matching report name."""
    state = SimpleNamespace(demo_mode=True)
    settings = GenerationSettings(export_report=True)

    output_path, report_path = resolve_output_targets(
        state,
        settings,
        output_path="",
        pacing_kwargs={},
    )

    assert output_path.endswith("_demo.mp4")
    assert report_path is not None
    assert report_path.endswith("_demo_report.xlsx")


def test_prepare_run_request_reports_missing_manual_inputs():
    """Manual runs should fail fast with clear validation errors."""
    state = SimpleNamespace(demo_mode=False)
    settings = GenerationSettings()

    with patch("src.application.streamlit_requests.st.session_state", {}):
        prepared_run, errors = prepare_run_request(
            state,
            settings,
            audio_path_text="",
            video_dir="",
            broll_dir_input="",
            output_path="output_story.mp4",
        )

    assert prepared_run is None
    assert errors == [
        "Please provide an audio file path or upload a file.",
        "Please upload video files or enter the path to your video clips folder.",
    ]
