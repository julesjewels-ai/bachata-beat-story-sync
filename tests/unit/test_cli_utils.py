"""
Unit tests for shared CLI utilities (src/cli_utils.py).
"""

import argparse
from typing import Any
from unittest.mock import MagicMock

import pytest
from src.cli_utils import (
    add_shorts_args,
    add_visual_args,
    build_pacing_kwargs,
    detect_broll_dir,
    parse_duration,
)

# ------------------------------------------------------------------
# parse_duration
# ------------------------------------------------------------------


class TestParseDuration:
    def test_single_value(self):
        assert parse_duration("60") == (60.0, 60.0)

    def test_range_value(self):
        assert parse_duration("10-15") == (10.0, 15.0)

    def test_invalid_raises(self):
        with pytest.raises(argparse.ArgumentTypeError):
            parse_duration("abc")


# ------------------------------------------------------------------
# build_pacing_kwargs
# ------------------------------------------------------------------


@pytest.fixture
def empty_args() -> argparse.Namespace:
    """Provides a Namespace with all build_pacing_kwargs inputs set to None/False."""
    return argparse.Namespace(
        test_mode=False,
        genre=None,
        video_style=None,
        audio_overlay=None,
        audio_overlay_opacity=None,
        audio_overlay_position=None,
        audio_overlay_padding=None,
        audio_overlay_color=None,
        audio_overlay_palette=None,
        audio_overlay_width_pct=None,
        audio_overlay_height=None,
        broll_interval=None,
        broll_variance=None,
        explain=False,
        explain_html=None,
        intro_effect=None,
        intro_effect_duration=None,
        dry_run=False,
        pacing_drift_zoom=False,
        pacing_crop_tighten=False,
        pacing_saturation_pulse=False,
        pacing_micro_jitters=False,
        pacing_light_leaks=False,
        pacing_warm_wash=False,
        pacing_alternating_bokeh=False,
        zoom=None,
        text_overlay=False,
        no_cold_open=False,
        no_lyrics=False,
        track_artist=None,
        track_title=None,
        lrc_path=None,
    )


class TestBuildPacingKwargs:
    def test_empty_args(self, empty_args: argparse.Namespace) -> None:
        result = build_pacing_kwargs(empty_args)
        assert result == {}

    @pytest.mark.parametrize(
        ("attr", "val", "expected"),
        [
            ("test_mode", True, {"max_clips": 4, "max_duration_seconds": 10.0}),
            ("genre", "action", {"genre": "action"}),
            ("video_style", "warm", {"video_style": "warm"}),
            ("audio_overlay", "waveform", {"audio_overlay": "waveform"}),
            ("audio_overlay_opacity", 0.5, {"audio_overlay_opacity": 0.5}),
            ("audio_overlay_position", "center", {"audio_overlay_position": "center"}),
            ("audio_overlay_padding", 20, {"audio_overlay_padding": 20}),
            ("audio_overlay_color", "white", {"audio_overlay_color": "white"}),
            ("audio_overlay_palette", "inferno", {"audio_overlay_palette": "inferno"}),
            ("audio_overlay_width_pct", 0.8, {"audio_overlay_width_pct": 0.8}),
            ("audio_overlay_height", 100, {"audio_overlay_height": 100}),
            ("broll_interval", 15.0, {"broll_interval_seconds": 15.0}),
            ("broll_variance", 2.0, {"broll_interval_variance": 2.0}),
            ("explain", True, {"explain": True}),
            (
                "explain_html",
                "path.html",
                {"explain_html": "path.html", "explain": True},
            ),
            ("intro_effect", "bloom", {"intro_effect": "bloom"}),
            ("intro_effect_duration", 2.0, {"intro_effect_duration": 2.0}),
            ("dry_run", True, {"dry_run": True}),
            ("pacing_drift_zoom", True, {"pacing_drift_zoom": True}),
            ("pacing_crop_tighten", True, {"pacing_crop_tighten": True}),
            ("pacing_saturation_pulse", True, {"pacing_saturation_pulse": True}),
            ("pacing_micro_jitters", True, {"pacing_micro_jitters": True}),
            ("pacing_light_leaks", True, {"pacing_light_leaks": True}),
            ("pacing_warm_wash", True, {"pacing_warm_wash": True}),
            ("pacing_alternating_bokeh", True, {"pacing_alternating_bokeh": True}),
            ("zoom", 1.5, {"zoom_factor": 1.5}),
            ("track_artist", "Artist", {"track_artist": "Artist"}),
            ("track_title", "Title", {"track_title": "Title"}),
            ("lrc_path", "lyrics.lrc", {"lyrics_lrc_path": "lyrics.lrc"}),
        ],
    )
    def test_single_attributes(
        self,
        empty_args: argparse.Namespace,
        attr: str,
        val: Any,
        expected: dict,
    ) -> None:
        setattr(empty_args, attr, val)
        result = build_pacing_kwargs(empty_args)
        err_msg = f"Failed on input: {attr}={val}"
        assert result == expected, err_msg

    @pytest.mark.parametrize(
        ("no_cold_open", "no_lyrics", "expected_extras"),
        [
            (False, False, {}),
            (True, False, {"cold_open_enabled": False}),
            (False, True, {"lyrics_overlay_enabled": False}),
            (True, True, {"cold_open_enabled": False, "lyrics_overlay_enabled": False}),
        ],
    )
    def test_text_overlay_combinations(
        self,
        empty_args: argparse.Namespace,
        no_cold_open: bool,
        no_lyrics: bool,
        expected_extras: dict,
    ) -> None:
        empty_args.text_overlay = True
        empty_args.no_cold_open = no_cold_open
        empty_args.no_lyrics = no_lyrics

        expected = {"text_overlay_enabled": True}
        expected.update(expected_extras)

        result = build_pacing_kwargs(empty_args)
        err_msg = f"Failed on text_overlay combinations: no_cold={no_cold_open}, no_lyrics={no_lyrics}"
        assert result == expected, err_msg


# ------------------------------------------------------------------
# add_visual_args
# ------------------------------------------------------------------


class TestAddVisualArgs:
    def test_registers_all_visual_arguments(self):
        parser = argparse.ArgumentParser()
        add_visual_args(parser)
        ns = parser.parse_args([])
        assert ns.video_style is None
        assert ns.audio_overlay is None
        assert ns.audio_overlay_opacity is None
        assert ns.audio_overlay_position is None
        assert ns.audio_overlay_padding is None
        assert ns.broll_interval is None
        assert ns.broll_variance is None

    def test_accepts_valid_choices(self):
        parser = argparse.ArgumentParser()
        add_visual_args(parser)
        ns = parser.parse_args(
            [
                "--video-style",
                "warm",
                "--audio-overlay",
                "bars",
                "--audio-overlay-position",
                "center",
                "--audio-overlay-padding",
                "30",
            ]
        )
        assert ns.video_style == "warm"
        assert ns.audio_overlay == "bars"
        assert ns.audio_overlay_position == "center"
        assert ns.audio_overlay_padding == 30

    def test_rejects_invalid_video_style(self):
        parser = argparse.ArgumentParser()
        add_visual_args(parser)
        with pytest.raises(SystemExit):
            parser.parse_args(["--video-style", "neon"])


# ------------------------------------------------------------------
# add_shorts_args
# ------------------------------------------------------------------


class TestAddShortsArgs:
    def test_registers_all_shorts_arguments(self):
        parser = argparse.ArgumentParser()
        add_shorts_args(parser)
        ns = parser.parse_args([])
        assert ns.dynamic_flow is False
        assert ns.human_touch is False
        assert ns.cliffhanger is False
        assert ns.smart_start is True

    def test_enables_flags(self):
        parser = argparse.ArgumentParser()
        add_shorts_args(parser)
        ns = parser.parse_args(
            [
                "--dynamic-flow",
                "--human-touch",
                "--cliffhanger",
            ]
        )
        assert ns.dynamic_flow is True
        assert ns.human_touch is True
        assert ns.cliffhanger is True

    def test_no_smart_start_disables(self):
        parser = argparse.ArgumentParser()
        add_shorts_args(parser)
        ns = parser.parse_args(["--no-smart-start"])
        assert ns.smart_start is False


# ------------------------------------------------------------------
# detect_broll_dir
# ------------------------------------------------------------------


class TestDetectBrollDir:
    def test_explicit_override(self, tmp_path):
        """Explicit broll_dir is returned unchanged."""
        explicit = str(tmp_path / "my_broll")
        result = detect_broll_dir(str(tmp_path), explicit)
        assert result == explicit

    def test_auto_detect(self, tmp_path):
        """Auto-detects 'broll' subfolder inside video_dir."""
        broll = tmp_path / "broll"
        broll.mkdir()
        result = detect_broll_dir(str(tmp_path))
        assert result == str(broll)

    def test_no_broll(self, tmp_path):
        """Returns None when no broll subfolder exists."""
        result = detect_broll_dir(str(tmp_path))
        assert result is None


# ------------------------------------------------------------------
# Intro Effect CLI (FEAT-022)
# ------------------------------------------------------------------


class TestIntroEffectCLI:
    def test_intro_args_registered(self):
        """--intro-effect and --intro-effect-duration parse correctly."""
        parser = argparse.ArgumentParser()
        add_visual_args(parser)
        ns = parser.parse_args(
            [
                "--intro-effect",
                "bloom",
                "--intro-effect-duration",
                "2.0",
            ]
        )
        assert ns.intro_effect == "bloom"
        assert ns.intro_effect_duration == 2.0

    def test_intro_args_defaults_none(self):
        """When omitted, both intro args default to None."""
        parser = argparse.ArgumentParser()
        add_visual_args(parser)
        ns = parser.parse_args([])
        assert ns.intro_effect is None
        assert ns.intro_effect_duration is None

    def test_build_pacing_kwargs_includes_intro(self):
        """build_pacing_kwargs forwards intro_effect when set."""
        ns = argparse.Namespace(
            test_mode=False,
            video_style=None,
            audio_overlay=None,
            audio_overlay_opacity=None,
            audio_overlay_position=None,
            broll_interval=None,
            broll_variance=None,
            explain=False,
            intro_effect="bloom",
            intro_effect_duration=2.0,
            dry_run=False,
        )
        kwargs = build_pacing_kwargs(ns)
        assert kwargs["intro_effect"] == "bloom"
        assert kwargs["intro_effect_duration"] == 2.0

    def test_build_pacing_kwargs_omits_intro_when_none(self):
        """build_pacing_kwargs omits intro fields when None."""
        ns = argparse.Namespace(
            test_mode=False,
            video_style=None,
            audio_overlay=None,
            audio_overlay_opacity=None,
            audio_overlay_position=None,
            broll_interval=None,
            broll_variance=None,
            explain=False,
            intro_effect=None,
            intro_effect_duration=None,
            dry_run=False,
        )
        kwargs = build_pacing_kwargs(ns)
        assert "intro_effect" not in kwargs
        assert "intro_effect_duration" not in kwargs


# ------------------------------------------------------------------
# Dry-Run CLI (FEAT-026)
# ------------------------------------------------------------------


class TestDryRunCLI:
    def test_dry_run_flag_parsed(self):
        """--dry-run registers as True."""
        parser = argparse.ArgumentParser()
        add_visual_args(parser)
        ns = parser.parse_args(["--dry-run"])
        assert ns.dry_run is True

    def test_dry_run_default_false(self):
        """Without --dry-run, default is False."""
        parser = argparse.ArgumentParser()
        add_visual_args(parser)
        ns = parser.parse_args([])
        assert ns.dry_run is False

    def test_dry_run_output_flag(self):
        """--dry-run-output stores a path."""
        parser = argparse.ArgumentParser()
        add_visual_args(parser)
        ns = parser.parse_args(["--dry-run-output", "/tmp/plan.txt"])
        assert ns.dry_run_output == "/tmp/plan.txt"

    def test_build_pacing_kwargs_includes_dry_run(self):
        """build_pacing_kwargs includes dry_run when set."""
        ns = argparse.Namespace(
            test_mode=False,
            video_style=None,
            audio_overlay=None,
            audio_overlay_opacity=None,
            audio_overlay_position=None,
            broll_interval=None,
            broll_variance=None,
            explain=False,
            intro_effect=None,
            intro_effect_duration=None,
            dry_run=True,
        )
        kwargs = build_pacing_kwargs(ns)
        assert kwargs["dry_run"] is True

    def test_build_pacing_kwargs_omits_dry_run_when_false(self):
        """build_pacing_kwargs omits dry_run when False."""
        ns = argparse.Namespace(
            test_mode=False,
            video_style=None,
            audio_overlay=None,
            audio_overlay_opacity=None,
            audio_overlay_position=None,
            broll_interval=None,
            broll_variance=None,
            explain=False,
            intro_effect=None,
            intro_effect_duration=None,
            dry_run=False,
        )
        kwargs = build_pacing_kwargs(ns)
        assert "dry_run" not in kwargs
