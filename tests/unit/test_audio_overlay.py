"""Unit tests for the audio-overlay palette + FFmpeg filter construction."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.core.audio_overlay_palettes import (
    PALETTES,
    resolve_colors,
    spectrum_color_for_palette,
    validate_color,
)
from src.core.ffmpeg_renderer import build_overlay_filter
from src.core.models import PacingConfig
from src.core.pacing_views import OverlayConfig, overlay_config_from_pacing


def _overlay(**overrides: object) -> OverlayConfig:
    defaults: dict[str, object] = {
        "is_shorts": False,
        "audio_overlay": "waveform",
        "audio_overlay_opacity": 0.5,
        "audio_overlay_position": "right",
        "audio_overlay_padding": 10,
        "audio_start_offset": 0.0,
        "audio_overlay_color": "white",
        "audio_overlay_palette": "none",
        "audio_overlay_width_pct": 0.2,
        "audio_overlay_height": 120,
    }
    defaults.update(overrides)
    return OverlayConfig(**defaults)  # type: ignore[arg-type]


# --- palette helpers -------------------------------------------------------


def test_resolve_colors_custom_uses_single_color_with_opacity() -> None:
    assert resolve_colors("custom", "#FF8800", 0.3) == "#FF8800@0.30"


def test_resolve_colors_none_falls_back_to_custom_color() -> None:
    assert resolve_colors("none", "gold", 1.0) == "gold@1.00"


def test_resolve_colors_none_empty_custom_defaults_to_white() -> None:
    assert resolve_colors("none", "", 0.5) == "White@0.50"


def test_resolve_colors_rainbow_joins_all_palette_entries() -> None:
    out = resolve_colors("rainbow", "white", 0.5)
    entries = out.split("|")
    assert len(entries) == len(PALETTES["rainbow"])
    assert all(e.endswith("@0.50") for e in entries)
    assert entries[0] == "#FF0000@0.50"


def test_resolve_colors_clamps_opacity() -> None:
    assert resolve_colors("custom", "red", -0.5).endswith("@0.00")
    assert resolve_colors("custom", "red", 2.0).endswith("@1.00")


def test_validate_color_accepts_hex_and_name() -> None:
    assert validate_color("#FF8800") == "#FF8800"
    assert validate_color("#abc") == "#abc"
    assert validate_color("gold") == "gold"


def test_validate_color_rejects_garbage() -> None:
    with pytest.raises(ValueError):
        validate_color("not a color")
    with pytest.raises(ValueError):
        validate_color("#ZZZ")
    with pytest.raises(ValueError):
        validate_color("")


def test_spectrum_color_mapping_has_known_presets() -> None:
    assert spectrum_color_for_palette("warm") == "fiery"
    assert spectrum_color_for_palette("cool") == "cool"
    assert spectrum_color_for_palette("rainbow") == "rainbow"
    assert spectrum_color_for_palette("bogus") == "rainbow"


# --- PacingConfig validators ----------------------------------------------


def test_pacing_config_clamps_width_pct() -> None:
    cfg = PacingConfig(audio_overlay_width_pct=5.0)
    assert cfg.audio_overlay_width_pct == 1.0
    cfg2 = PacingConfig(audio_overlay_width_pct=0.0)
    assert cfg2.audio_overlay_width_pct == 0.05


def test_pacing_config_clamps_height() -> None:
    cfg = PacingConfig(audio_overlay_height=9999)
    assert cfg.audio_overlay_height == 400
    cfg2 = PacingConfig(audio_overlay_height=1)
    assert cfg2.audio_overlay_height == 40


def test_pacing_config_rejects_invalid_color() -> None:
    with pytest.raises(ValidationError):
        PacingConfig(audio_overlay_color="not a color!")


def test_overlay_config_roundtrips_new_fields() -> None:
    pacing = PacingConfig(
        audio_overlay="spectrum",
        audio_overlay_palette="warm",
        audio_overlay_color="#FF8800",
        audio_overlay_width_pct=0.5,
        audio_overlay_height=200,
    )
    overlay = overlay_config_from_pacing(pacing)
    assert overlay.audio_overlay == "spectrum"
    assert overlay.audio_overlay_palette == "warm"
    assert overlay.audio_overlay_color == "#FF8800"
    assert overlay.audio_overlay_width_pct == 0.5
    assert overlay.audio_overlay_height == 200


# --- build_overlay_filter snapshots ---------------------------------------


def test_filter_waveform_default_matches_legacy_shape() -> None:
    f = build_overlay_filter(_overlay())
    assert "showwaves" in f
    assert "mode=line" in f
    assert "colors=white@0.50" in f
    assert "s=384x120" in f  # 20% of 1920
    assert "overlay=W-384-10:H-h-10" in f


def test_filter_waveform_centered_uses_cline() -> None:
    f = build_overlay_filter(_overlay(audio_overlay="waveform_centered"))
    assert "showwaves" in f
    assert "mode=cline" in f


def test_filter_bars_with_palette_distributes_colors() -> None:
    f = build_overlay_filter(
        _overlay(audio_overlay="bars", audio_overlay_palette="rainbow")
    )
    assert "showfreqs" in f
    assert "mode=bar" in f
    # Pipe-joined colors for the rainbow palette.
    assert "#FF0000@0.50|#FFA500@0.50" in f


def test_filter_spectrum_uses_color_preset_and_log_scale() -> None:
    f = build_overlay_filter(
        _overlay(audio_overlay="spectrum", audio_overlay_palette="warm")
    )
    assert "showspectrum" in f
    assert "color=fiery" in f
    assert "scale=log" in f


def test_filter_cqt_renders_and_applies_opacity_mixer() -> None:
    f = build_overlay_filter(
        _overlay(audio_overlay="cqt", audio_overlay_opacity=0.4)
    )
    assert "showcqt" in f
    assert "colorchannelmixer=aa=0.40" in f


def test_filter_cqt_opaque_omits_mixer() -> None:
    f = build_overlay_filter(
        _overlay(audio_overlay="cqt", audio_overlay_opacity=1.0)
    )
    assert "showcqt" in f
    assert "colorchannelmixer" not in f


def test_filter_shorts_width_uses_1080_base() -> None:
    f = build_overlay_filter(_overlay(is_shorts=True))
    assert "s=216x120" in f  # 20% of 1080


def test_filter_respects_width_pct_and_height() -> None:
    f = build_overlay_filter(
        _overlay(audio_overlay_width_pct=0.5, audio_overlay_height=200)
    )
    assert "s=960x200" in f  # 50% of 1920


def test_filter_position_left_and_center() -> None:
    fl = build_overlay_filter(_overlay(audio_overlay_position="left"))
    assert "overlay=10:H-h-10" in fl

    fc = build_overlay_filter(_overlay(audio_overlay_position="center"))
    assert "overlay=(W-384)/2:H-h-10" in fc


def test_filter_unknown_style_raises() -> None:
    with pytest.raises(ValueError):
        build_overlay_filter(_overlay(audio_overlay="nope"))
