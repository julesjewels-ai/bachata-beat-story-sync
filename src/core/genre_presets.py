"""
Genre Preset System (FEAT-027).

Provides tuned PacingConfig overrides for different music genres so
users can get great results with a single ``--genre`` flag.

Override priority chain::

    PacingConfig defaults  <  YAML file  <  Genre preset  <  CLI flags
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
