"""Color palettes and helpers for the audio-overlay visualizer.

The FFmpeg filters ``showwaves`` and ``showfreqs`` both accept a
``colors=`` argument that takes a ``|``-separated list of colors; when the
filter renders multiple bands/channels, the colors are distributed across
them. This module centralises the mapping from a friendly palette name to
the pipe-joined FFmpeg string, so the renderer stays focused on filter
construction.

A ``spectrum`` or ``cqt`` visualizer style uses FFmpeg's built-in color
engines rather than a custom palette; for those we expose
``spectrum_color_for_palette`` which maps our palette names to the closest
preset FFmpeg supports natively.
"""

from __future__ import annotations

import re

# Low → high frequency ordering. When ``showfreqs`` splits the palette
# across bands, the first colour maps to the lowest band.
PALETTES: dict[str, list[str]] = {
    "warm": ["#FFE5B4", "#FFB347", "#FF7F50", "#D2691E"],
    "cool": ["#B0E0E6", "#4682B4", "#1E90FF", "#00008B"],
    "sunset": ["#FFD700", "#FF8C00", "#FF4500", "#8B008B"],
    "neon": ["#39FF14", "#00FFFF", "#FF00FF", "#FFFF00"],
    "rainbow": ["#FF0000", "#FFA500", "#FFFF00", "#00FF00", "#0000FF", "#8B00FF"],
    "mono": ["#FFFFFF"],
}

PALETTE_NAMES: tuple[str, ...] = (
    "none",
    "warm",
    "cool",
    "sunset",
    "neon",
    "rainbow",
    "mono",
    "custom",
)

# Map our palette names to FFmpeg's showspectrum ``color=`` presets.
# Anything unmapped falls back to "rainbow".
_SPECTRUM_COLOR_MAP: dict[str, str] = {
    "warm": "fiery",
    "cool": "cool",
    "sunset": "fire",
    "neon": "rainbow",
    "rainbow": "rainbow",
    "mono": "intensity",
    "none": "rainbow",
    "custom": "rainbow",
}

_HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
# FFmpeg accepts a subset of X11/SVG names. We do not validate the full
# list; instead we allow a simple ASCII identifier and let FFmpeg surface
# errors on truly invalid names.
_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")


def validate_color(color: str) -> str:
    """Return ``color`` if it looks like a valid FFmpeg color, else raise.

    Accepts:
        - ``#RGB`` or ``#RRGGBB`` hex strings
        - Simple color names (e.g. ``white``, ``gold``, ``deepskyblue``)
    """
    c = color.strip()
    if not c:
        raise ValueError("audio_overlay_color must not be empty")
    if _HEX_RE.match(c) or _NAME_RE.match(c):
        return c
    raise ValueError(
        f"audio_overlay_color {color!r} is not a valid hex "
        "(e.g. '#FF8800') or color name"
    )


def resolve_colors(palette: str, custom_color: str, opacity: float) -> str:
    """Return the ``colors=`` value for ``showwaves`` / ``showfreqs``.

    Every color gets an ``@{opacity}`` alpha suffix so the visualizer
    respects the existing opacity control.
    """
    op = max(0.0, min(1.0, opacity))
    suffix = f"@{op:.2f}"

    if palette in ("none", "custom") or palette not in PALETTES:
        color = validate_color(custom_color) if custom_color else "White"
        return f"{color}{suffix}"

    colors = PALETTES[palette]
    return "|".join(f"{c}{suffix}" for c in colors)


def spectrum_color_for_palette(palette: str) -> str:
    """Return the ``showspectrum`` ``color=`` preset for a given palette."""
    return _SPECTRUM_COLOR_MAP.get(palette, "rainbow")
