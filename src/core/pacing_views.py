"""Concern-specific views derived from ``PacingConfig``.

This module keeps external compatibility (callers still pass ``PacingConfig``)
while allowing planner/render/overlay logic to depend on smaller config
surfaces with tighter contracts.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.core.models import MixTrackSegment, PacingConfig


@dataclass(frozen=True)
class PlanningConfig:
    """Planner-only subset of pacing settings."""

    min_clip_seconds: float
    high_intensity_seconds: float
    medium_intensity_seconds: float
    low_intensity_seconds: float
    snap_to_beats: bool
    high_intensity_threshold: float
    low_intensity_threshold: float
    speed_ramp_enabled: bool
    high_intensity_speed: float
    medium_intensity_speed: float
    low_intensity_speed: float
    speed_ramp_organic: bool
    speed_ramp_sensitivity: float
    speed_ramp_curve: str
    speed_ramp_min: float
    speed_ramp_max: float
    max_clips: int | None
    max_duration_seconds: float | None
    clip_variety_enabled: bool
    broll_interval_seconds: float
    broll_interval_variance: float
    is_shorts: bool
    seed: str
    accelerate_pacing: bool
    randomize_speed_ramps: bool
    audio_start_offset: float
    explain: bool
    explain_html: str | None
    prefix_offset: int


@dataclass(frozen=True)
class RenderConfig:
    """Render/FFmpeg filter subset of pacing settings."""

    is_shorts: bool
    speed_ramp_organic: bool
    zoom_factor: float
    interpolation_method: str
    intro_effect: str
    intro_effect_duration: float
    pacing_drift_zoom: bool
    pacing_crop_tighten: bool
    pacing_saturation_pulse: bool
    pacing_micro_jitters: bool
    pacing_light_leaks: bool
    pacing_alternating_bokeh: bool
    video_style: str
    transition_type: str
    transition_duration: float
    pacing_warm_wash: bool
    text_overlay_enabled: bool
    text_overlay_font: str
    mix_fade_transitions: bool
    mix_track_segments: list[MixTrackSegment]
    mix_fade_duration: float


@dataclass(frozen=True)
class OverlayConfig:
    """Audio overlay/mux subset of pacing settings."""

    is_shorts: bool
    audio_overlay: str
    audio_overlay_opacity: float
    audio_overlay_position: str
    audio_overlay_padding: int
    audio_start_offset: float


def planning_config_from_pacing(config: PacingConfig) -> PlanningConfig:
    """Build a ``PlanningConfig`` view from ``PacingConfig``."""
    return PlanningConfig(
        min_clip_seconds=config.min_clip_seconds,
        high_intensity_seconds=config.high_intensity_seconds,
        medium_intensity_seconds=config.medium_intensity_seconds,
        low_intensity_seconds=config.low_intensity_seconds,
        snap_to_beats=config.snap_to_beats,
        high_intensity_threshold=config.high_intensity_threshold,
        low_intensity_threshold=config.low_intensity_threshold,
        speed_ramp_enabled=config.speed_ramp_enabled,
        high_intensity_speed=config.high_intensity_speed,
        medium_intensity_speed=config.medium_intensity_speed,
        low_intensity_speed=config.low_intensity_speed,
        speed_ramp_organic=config.speed_ramp_organic,
        speed_ramp_sensitivity=config.speed_ramp_sensitivity,
        speed_ramp_curve=config.speed_ramp_curve,
        speed_ramp_min=config.speed_ramp_min,
        speed_ramp_max=config.speed_ramp_max,
        max_clips=config.max_clips,
        max_duration_seconds=config.max_duration_seconds,
        clip_variety_enabled=config.clip_variety_enabled,
        broll_interval_seconds=config.broll_interval_seconds,
        broll_interval_variance=config.broll_interval_variance,
        is_shorts=config.is_shorts,
        seed=config.seed,
        accelerate_pacing=config.accelerate_pacing,
        randomize_speed_ramps=config.randomize_speed_ramps,
        audio_start_offset=config.audio_start_offset,
        explain=config.explain,
        explain_html=config.explain_html,
        prefix_offset=config.prefix_offset,
    )


def render_config_from_pacing(config: PacingConfig) -> RenderConfig:
    """Build a ``RenderConfig`` view from ``PacingConfig``."""
    return RenderConfig(
        is_shorts=config.is_shorts,
        speed_ramp_organic=config.speed_ramp_organic,
        zoom_factor=config.zoom_factor,
        interpolation_method=config.interpolation_method,
        intro_effect=config.intro_effect,
        intro_effect_duration=config.intro_effect_duration,
        pacing_drift_zoom=config.pacing_drift_zoom,
        pacing_crop_tighten=config.pacing_crop_tighten,
        pacing_saturation_pulse=config.pacing_saturation_pulse,
        pacing_micro_jitters=config.pacing_micro_jitters,
        pacing_light_leaks=config.pacing_light_leaks,
        pacing_alternating_bokeh=config.pacing_alternating_bokeh,
        video_style=config.video_style,
        transition_type=config.transition_type,
        transition_duration=config.transition_duration,
        pacing_warm_wash=config.pacing_warm_wash,
        text_overlay_enabled=config.text_overlay_enabled,
        text_overlay_font=config.text_overlay_font,
        mix_fade_transitions=config.mix_fade_transitions,
        mix_track_segments=config.mix_track_segments,
        mix_fade_duration=config.mix_fade_duration,
    )


def overlay_config_from_pacing(config: PacingConfig) -> OverlayConfig:
    """Build an ``OverlayConfig`` view from ``PacingConfig``."""
    return OverlayConfig(
        is_shorts=config.is_shorts,
        audio_overlay=config.audio_overlay,
        audio_overlay_opacity=config.audio_overlay_opacity,
        audio_overlay_position=config.audio_overlay_position,
        audio_overlay_padding=config.audio_overlay_padding,
        audio_start_offset=config.audio_start_offset,
    )


def split_pacing_config(
    config: PacingConfig,
) -> tuple[PlanningConfig, RenderConfig, OverlayConfig]:
    """Return all concern-specific config views in one call."""
    return (
        planning_config_from_pacing(config),
        render_config_from_pacing(config),
        overlay_config_from_pacing(config),
    )
