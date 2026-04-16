"""Unit tests for concern-specific pacing config views."""

from src.core.models import MixTrackSegment, PacingConfig
from src.core.pacing_views import (
    overlay_config_from_pacing,
    planning_config_from_pacing,
    render_config_from_pacing,
    split_pacing_config,
)


def _base_pacing() -> PacingConfig:
    return PacingConfig(
        min_clip_seconds=2.0,
        high_intensity_seconds=3.0,
        speed_ramp_organic=True,
        broll_interval_seconds=12.0,
        audio_overlay="waveform",
        audio_overlay_padding=24,
        text_overlay_enabled=True,
        transition_type="fade",
        transition_duration=0.7,
        mix_fade_transitions=True,
        mix_fade_duration=0.4,
        mix_track_segments=[
            MixTrackSegment(
                artist="A",
                title="Song",
                start_time=15.0,
                audio_path="/audio/a.wav",
            )
        ],
    )


def test_planning_config_from_pacing_maps_planner_fields() -> None:
    pacing = _base_pacing()
    planning = planning_config_from_pacing(pacing)

    assert planning.min_clip_seconds == 2.0
    assert planning.high_intensity_seconds == 3.0
    assert planning.speed_ramp_organic is True
    assert planning.broll_interval_seconds == 12.0


def test_render_config_from_pacing_maps_render_fields() -> None:
    pacing = _base_pacing()
    render = render_config_from_pacing(pacing)

    assert render.text_overlay_enabled is True
    assert render.transition_type == "fade"
    assert render.transition_duration == 0.7
    assert render.mix_fade_transitions is True
    assert render.mix_fade_duration == 0.4
    assert len(render.mix_track_segments) == 1


def test_overlay_config_from_pacing_maps_overlay_fields() -> None:
    pacing = _base_pacing()
    overlay = overlay_config_from_pacing(pacing)

    assert overlay.audio_overlay == "waveform"
    assert overlay.audio_overlay_padding == 24
    assert overlay.is_shorts is False


def test_split_pacing_config_returns_all_views() -> None:
    planning, render, overlay = split_pacing_config(_base_pacing())

    assert planning.min_clip_seconds == 2.0
    assert render.transition_type == "fade"
    assert overlay.audio_overlay == "waveform"
