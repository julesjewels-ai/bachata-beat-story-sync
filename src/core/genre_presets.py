"""
Genre Preset System (FEAT-027).

Provides tuned PacingConfig overrides for different music genres so
users can get great results with a single ``--genre`` flag.

Override priority chain::

    PacingConfig defaults  <  YAML file  <  Genre preset  <  CLI flags

COMMUNITY PRESETS:
    The built-in presets below are the foundation. The project also supports
    community-contributed presets in the ``presets/community/`` directory.
    See ``presets/README.md`` for details on using, creating, and submitting
    community presets.
"""

from __future__ import annotations

GENRE_PRESETS: dict[str, dict] = {
    # --- Latin / Dance ---
    "bachata": {
        # Current project defaults — formalised here for explicitness
        "high_intensity_seconds": 2.5,
        "medium_intensity_seconds": 4.0,
        "low_intensity_seconds": 6.0,
        "high_intensity_speed": 1.2,
        "medium_intensity_speed": 1.0,
        "low_intensity_speed": 0.9,
        "video_style": "golden",
        "transition_type": "fade",
        "transition_duration": 0.5,
        "intro_effect": "vignette_breathe",
        "hook_phase": {
            "enabled": True,
            "end_time_seconds": 4.0,
            "variation_selection": "rotate",
            "variations": [
                {
                    "name": "golden_breathe",
                    "intro_effect": "vignette_breathe",
                    "intro_effect_duration": 2.0,
                    "pacing_saturation_pulse": True,
                    "clip_selection": "highest_intensity",
                },
                {
                    "name": "bloom_drift",
                    "intro_effect": "bloom",
                    "intro_effect_duration": 1.5,
                    "pacing_drift_zoom": True,
                    "clip_selection": "highest_intensity",
                },
                {
                    "name": "clean_jitter",
                    "intro_effect": "none",
                    "pacing_micro_jitters": True,
                    "pacing_light_leaks": True,
                    "clip_selection": "highest_intensity",
                },
            ],
        },
        "intro_phase": {
            "enabled": True,
            "end_time_seconds": 10.0,
            "variation_selection": "rotate",
            "variations": [
                {
                    "name": "storytelling",
                    "pacing_saturation_pulse": True,
                    "pacing_alternating_bokeh": True,
                },
                {
                    "name": "energetic",
                    "pacing_light_leaks": True,
                    "pacing_micro_jitters": True,
                },
                {
                    "name": "cinematic",
                    "pacing_drift_zoom": True,
                },
            ],
        },
        "warmup_phase": {
            "enabled": True,
            "end_time_seconds": 30.0,
            "variation_selection": "rotate",
            "variations": [
                {"name": "building", "pacing_saturation_pulse": True},
                {"name": "flowing", "pacing_alternating_bokeh": True},
                {"name": "raw", "pacing_micro_jitters": True},
            ],
        },
    },
    "salsa": {
        "high_intensity_seconds": 1.8,
        "medium_intensity_seconds": 2.8,
        "low_intensity_seconds": 4.0,
        "high_intensity_speed": 1.4,
        "medium_intensity_speed": 1.1,
        "low_intensity_speed": 1.0,
        "video_style": "warm",
        "transition_type": "wipeleft",
        "transition_duration": 0.3,
        "intro_effect": "bloom",
        "hook_phase": {
            "enabled": True,
            "end_time_seconds": 3.0,
            "variation_selection": "rotate",
            "variations": [
                {
                    "name": "hot_bloom",
                    "intro_effect": "bloom",
                    "intro_effect_duration": 1.0,
                    "pacing_saturation_pulse": True,
                    "pacing_micro_jitters": True,
                    "clip_selection": "highest_intensity",
                },
                {
                    "name": "fire_leak",
                    "intro_effect": "bloom",
                    "intro_effect_duration": 0.8,
                    "pacing_light_leaks": True,
                    "clip_selection": "highest_intensity",
                },
                {
                    "name": "raw_cut",
                    "intro_effect": "none",
                    "pacing_micro_jitters": True,
                    "clip_selection": "highest_intensity",
                },
            ],
        },
        "intro_phase": {
            "enabled": True,
            "end_time_seconds": 10.0,
            "variation_selection": "rotate",
            "variations": [
                {"name": "pulse_drive", "pacing_saturation_pulse": True, "pacing_micro_jitters": True},
                {"name": "heat_wave", "pacing_light_leaks": True, "pacing_saturation_pulse": True},
                {"name": "sharp", "pacing_micro_jitters": True},
            ],
        },
        "warmup_phase": {
            "enabled": True,
            "end_time_seconds": 30.0,
            "variation_selection": "rotate",
            "variations": [
                {"name": "momentum", "pacing_saturation_pulse": True},
                {"name": "groove", "pacing_light_leaks": True},
            ],
        },
    },
    "reggaeton": {
        "high_intensity_seconds": 2.2,
        "medium_intensity_seconds": 3.5,
        "low_intensity_seconds": 5.0,
        "high_intensity_speed": 1.3,
        "medium_intensity_speed": 1.0,
        "low_intensity_speed": 0.85,
        "video_style": "cool",
        "transition_type": "fade",
        "transition_duration": 0.4,
        "intro_effect": "bloom",
        "hook_phase": {
            "enabled": True,
            "end_time_seconds": 4.0,
            "variation_selection": "rotate",
            "variations": [
                {
                    "name": "cool_bloom",
                    "intro_effect": "bloom",
                    "intro_effect_duration": 1.2,
                    "pacing_light_leaks": True,
                    "clip_selection": "highest_intensity",
                },
                {
                    "name": "jitter_drop",
                    "intro_effect": "none",
                    "pacing_micro_jitters": True,
                    "pacing_saturation_pulse": True,
                    "clip_selection": "highest_intensity",
                },
                {
                    "name": "drift_open",
                    "intro_effect": "bloom",
                    "intro_effect_duration": 1.5,
                    "pacing_drift_zoom": True,
                    "clip_selection": "highest_intensity",
                },
            ],
        },
        "intro_phase": {
            "enabled": True,
            "end_time_seconds": 10.0,
            "variation_selection": "rotate",
            "variations": [
                {"name": "trap_pulse", "pacing_saturation_pulse": True, "pacing_light_leaks": True},
                {"name": "bounce", "pacing_micro_jitters": True, "pacing_saturation_pulse": True},
                {"name": "chill_drift", "pacing_drift_zoom": True},
            ],
        },
        "warmup_phase": {
            "enabled": True,
            "end_time_seconds": 30.0,
            "variation_selection": "rotate",
            "variations": [
                {"name": "heat", "pacing_saturation_pulse": True},
                {"name": "leak", "pacing_light_leaks": True},
            ],
        },
    },
    "kizomba": {
        "high_intensity_seconds": 3.5,
        "medium_intensity_seconds": 5.0,
        "low_intensity_seconds": 7.0,
        "high_intensity_speed": 1.0,
        "medium_intensity_speed": 0.9,
        "low_intensity_speed": 0.7,
        "video_style": "vintage",
        "transition_type": "fade",
        "transition_duration": 0.8,
        "intro_effect": "bloom",
        "hook_phase": {
            "enabled": True,
            "end_time_seconds": 5.0,
            "variation_selection": "rotate",
            "variations": [
                {
                    "name": "moody_bloom",
                    "intro_effect": "bloom",
                    "intro_effect_duration": 2.5,
                    "pacing_alternating_bokeh": True,
                    "clip_selection": "highest_intensity",
                },
                {
                    "name": "vignette_slow",
                    "intro_effect": "vignette_breathe",
                    "intro_effect_duration": 3.0,
                    "clip_selection": "highest_intensity",
                },
                {
                    "name": "drift_deep",
                    "intro_effect": "bloom",
                    "intro_effect_duration": 2.0,
                    "pacing_drift_zoom": True,
                    "clip_selection": "highest_intensity",
                },
            ],
        },
        "intro_phase": {
            "enabled": True,
            "end_time_seconds": 12.0,
            "variation_selection": "rotate",
            "variations": [
                {"name": "soulful", "pacing_alternating_bokeh": True, "pacing_drift_zoom": True},
                {"name": "intimate", "pacing_drift_zoom": True},
                {"name": "shadow", "pacing_light_leaks": True},
            ],
        },
        "warmup_phase": {
            "enabled": True,
            "end_time_seconds": 35.0,
            "variation_selection": "rotate",
            "variations": [
                {"name": "grounded", "pacing_drift_zoom": True},
                {"name": "sensual", "pacing_alternating_bokeh": True},
            ],
        },
    },
    "merengue": {
        "high_intensity_seconds": 1.5,
        "medium_intensity_seconds": 2.5,
        "low_intensity_seconds": 3.5,
        "high_intensity_speed": 1.5,
        "medium_intensity_speed": 1.2,
        "low_intensity_speed": 1.0,
        "video_style": "warm",
        "transition_type": "none",
        "transition_duration": 0.0,
        "intro_effect": "none",
        "hook_phase": {
            "enabled": True,
            "end_time_seconds": 3.0,
            "variation_selection": "rotate",
            "variations": [
                {
                    "name": "fiesta_burst",
                    "intro_effect": "bloom",
                    "intro_effect_duration": 0.8,
                    "pacing_saturation_pulse": True,
                    "pacing_micro_jitters": True,
                    "clip_selection": "highest_intensity",
                },
                {
                    "name": "warm_open",
                    "intro_effect": "bloom",
                    "intro_effect_duration": 1.0,
                    "pacing_light_leaks": True,
                    "clip_selection": "highest_intensity",
                },
            ],
        },
        "intro_phase": {
            "enabled": True,
            "end_time_seconds": 9.0,
            "variation_selection": "rotate",
            "variations": [
                {"name": "festive", "pacing_saturation_pulse": True, "pacing_micro_jitters": True},
                {"name": "bright", "pacing_light_leaks": True, "pacing_saturation_pulse": True},
            ],
        },
        "warmup_phase": {
            "enabled": True,
            "end_time_seconds": 25.0,
            "variation_selection": "rotate",
            "variations": [
                {"name": "carnival", "pacing_saturation_pulse": True},
                {"name": "groove", "pacing_micro_jitters": True},
            ],
        },
    },
    # --- General ---
    "pop": {
        "high_intensity_seconds": 2.5,
        "medium_intensity_seconds": 3.5,
        "low_intensity_seconds": 5.0,
        "high_intensity_speed": 1.1,
        "medium_intensity_speed": 1.0,
        "low_intensity_speed": 0.95,
        "video_style": "none",
        "transition_type": "fade",
        "transition_duration": 0.5,
        "intro_effect": "none",
        "hook_phase": {
            "enabled": True,
            "end_time_seconds": 4.0,
            "variation_selection": "rotate",
            "variations": [
                {
                    "name": "clean_bloom",
                    "intro_effect": "bloom",
                    "intro_effect_duration": 1.5,
                    "pacing_drift_zoom": True,
                    "clip_selection": "highest_intensity",
                },
                {
                    "name": "pulse_open",
                    "intro_effect": "none",
                    "pacing_saturation_pulse": True,
                    "clip_selection": "highest_intensity",
                },
                {
                    "name": "vibe_check",
                    "intro_effect": "vignette_breathe",
                    "intro_effect_duration": 1.8,
                    "pacing_light_leaks": True,
                    "clip_selection": "highest_intensity",
                },
            ],
        },
        "intro_phase": {
            "enabled": True,
            "end_time_seconds": 10.0,
            "variation_selection": "rotate",
            "variations": [
                {"name": "build_up", "pacing_drift_zoom": True, "pacing_saturation_pulse": True},
                {"name": "steady", "pacing_alternating_bokeh": True},
                {"name": "kinetic", "pacing_micro_jitters": True, "pacing_light_leaks": True},
            ],
        },
        "warmup_phase": {
            "enabled": True,
            "end_time_seconds": 30.0,
            "variation_selection": "rotate",
            "variations": [
                {"name": "flow", "pacing_drift_zoom": True},
                {"name": "charged", "pacing_saturation_pulse": True},
            ],
        },
    },
}


def list_genres() -> list[str]:
    """Return a sorted list of available genre preset names."""
    return sorted(GENRE_PRESETS.keys())


def apply_genre_preset(genre: str, base: dict) -> dict:
    """Merge a genre preset into *base*, filling only unset keys.

    Keys already present in *base* (from YAML or CLI) are **not**
    overwritten — the preset serves as a smart-default layer.

    Args:
        genre: Genre name (must exist in ``GENRE_PRESETS``).
        base: Dict of pacing overrides assembled so far.

    Returns:
        New dict with preset values merged in.

    Raises:
        ValueError: If *genre* is not a known preset name.
    """
    preset = GENRE_PRESETS.get(genre)
    if preset is None:
        available = ", ".join(list_genres())
        raise ValueError(f"Unknown genre '{genre}'. Available presets: {available}")

    merged = dict(preset)  # start with preset defaults
    merged.update(base)  # overlay user-supplied values on top
    # Carry the genre tag through so PacingConfig stores it
    merged["genre"] = genre
    return merged
