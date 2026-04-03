"""
Unit tests for FEAT-027 — Genre Preset System.

Tests cover: preset validity, unknown genre errors, override priority,
list_genres(), YAML integration via load_pacing_config(), and CLI arg parsing.
"""

import argparse
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest
from src.core.genre_presets import GENRE_PRESETS, apply_genre_preset, list_genres
from src.core.models import PacingConfig


# ------------------------------------------------------------------
# 1. All presets produce valid PacingConfig instances
# ------------------------------------------------------------------
class TestPresetsValidity:
    """Every preset dict must merge with defaults and validate."""

    @pytest.mark.parametrize("genre", list_genres())
    def test_preset_creates_valid_config(self, genre: str) -> None:
        merged = apply_genre_preset(genre, {})
        config = PacingConfig(**merged)
        assert config.genre == genre


# ------------------------------------------------------------------
# 2. Unknown genre raises ValueError
# ------------------------------------------------------------------
class TestUnknownGenre:
    def test_unknown_genre_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown genre 'dubstep'"):
            apply_genre_preset("dubstep", {})

    def test_error_lists_available_genres(self) -> None:
        with pytest.raises(ValueError, match="bachata") as exc_info:
            apply_genre_preset("nonexistent", {})
        for genre in list_genres():
            assert genre in str(exc_info.value)


# ------------------------------------------------------------------
# 3. Preset values override PacingConfig defaults
# ------------------------------------------------------------------
class TestPresetOverridesDefaults:
    def test_salsa_high_intensity_seconds(self) -> None:
        """Salsa preset should set high_intensity_seconds=1.8, not default 2.5."""
        merged = apply_genre_preset("salsa", {})
        config = PacingConfig(**merged)
        assert config.high_intensity_seconds == 1.8

    def test_kizomba_video_style(self) -> None:
        merged = apply_genre_preset("kizomba", {})
        config = PacingConfig(**merged)
        assert config.video_style == "vintage"

    def test_merengue_transition_none(self) -> None:
        merged = apply_genre_preset("merengue", {})
        config = PacingConfig(**merged)
        assert config.transition_type == "none"


# ------------------------------------------------------------------
# 4. Explicit values take priority over presets
# ------------------------------------------------------------------
class TestOverridePriority:
    def test_cli_style_overrides_preset(self) -> None:
        """User-supplied video_style='bw' should beat salsa preset 'warm'."""
        user_overrides = {"video_style": "bw"}
        merged = apply_genre_preset("salsa", user_overrides)
        config = PacingConfig(**merged)
        assert config.video_style == "bw"
        assert config.genre == "salsa"

    def test_cli_speed_overrides_preset(self) -> None:
        user_overrides = {"high_intensity_speed": 2.0}
        merged = apply_genre_preset("bachata", user_overrides)
        config = PacingConfig(**merged)
        assert config.high_intensity_speed == 2.0


# ------------------------------------------------------------------
# 5. list_genres() returns expected names
# ------------------------------------------------------------------
class TestListGenres:
    def test_returns_sorted_list(self) -> None:
        genres = list_genres()
        assert genres == sorted(genres)

    def test_contains_all_presets(self) -> None:
        genres = list_genres()
        for key in GENRE_PRESETS:
            assert key in genres

    def test_count_matches_registry(self) -> None:
        assert len(list_genres()) == len(GENRE_PRESETS)


# ------------------------------------------------------------------
# 6. load_pacing_config() with genre in YAML
# ------------------------------------------------------------------
class TestYamlGenreLoading:
    def test_yaml_genre_applies_preset(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            textwrap.dedent("""\
                pacing:
                  genre: reggaeton
            """)
        )
        from src.core.montage import load_pacing_config

        config = load_pacing_config(str(config_file))
        assert config.genre == "reggaeton"
        assert config.video_style == "cool"

    def test_yaml_explicit_overrides_genre(self, tmp_path: Path) -> None:
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            textwrap.dedent("""\
                pacing:
                  genre: reggaeton
                  video_style: bw
            """)
        )
        from src.core.montage import load_pacing_config

        config = load_pacing_config(str(config_file))
        assert config.genre == "reggaeton"
        assert config.video_style == "bw"  # explicit wins over preset


# ------------------------------------------------------------------
# 7. CLI --genre argument parsing
# ------------------------------------------------------------------
class TestCLIGenreArg:
    def test_genre_arg_parsed(self) -> None:
        from src.cli_utils import add_visual_args, build_pacing_kwargs

        parser = argparse.ArgumentParser()
        add_visual_args(parser)
        args = parser.parse_args(["--genre", "salsa"])
        kwargs = build_pacing_kwargs(args)
        assert kwargs["genre"] == "salsa"

    def test_genre_none_by_default(self) -> None:
        from src.cli_utils import add_visual_args, build_pacing_kwargs

        parser = argparse.ArgumentParser()
        add_visual_args(parser)
        args = parser.parse_args([])
        kwargs = build_pacing_kwargs(args)
        assert "genre" not in kwargs

    def test_invalid_genre_rejected(self) -> None:
        from src.cli_utils import add_visual_args

        parser = argparse.ArgumentParser()
        add_visual_args(parser)
        with pytest.raises(SystemExit):
            parser.parse_args(["--genre", "dubstep"])
