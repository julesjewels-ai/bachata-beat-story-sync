"""
Unit tests for shared CLI utilities (src/cli_utils.py).
"""

import argparse
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


class TestBuildPacingKwargs:
    def test_empty_args(self):
        args = MagicMock()
        args.test_mode = False
        args.video_style = None
        args.audio_overlay = None
        args.audio_overlay_opacity = None
        args.audio_overlay_position = None
        args.broll_interval = None
        args.broll_variance = None
        args.explain = False
        result = build_pacing_kwargs(args)
        assert result == {}

    def test_test_mode(self):
        args = MagicMock()
        args.test_mode = True
        args.video_style = None
        args.audio_overlay = None
        args.audio_overlay_opacity = None
        args.audio_overlay_position = None
        args.broll_interval = None
        args.broll_variance = None
        result = build_pacing_kwargs(args)
        assert result["max_clips"] == 4
        assert result["max_duration_seconds"] == 10.0

    def test_all_visual_args(self):
        args = MagicMock()
        args.test_mode = False
        args.video_style = "warm"
        args.audio_overlay = "waveform"
        args.audio_overlay_opacity = 0.8
        args.audio_overlay_position = "center"
        args.broll_interval = None
        args.broll_variance = None
        result = build_pacing_kwargs(args)
        assert result["video_style"] == "warm"
        assert result["audio_overlay"] == "waveform"
        assert result["audio_overlay_opacity"] == 0.8
        assert result["audio_overlay_position"] == "center"

    def test_broll_interval_args(self):
        args = MagicMock()
        args.test_mode = False
        args.video_style = None
        args.audio_overlay = None
        args.audio_overlay_opacity = None
        args.audio_overlay_position = None
        args.broll_interval = 20.0
        args.broll_variance = 3.0
        result = build_pacing_kwargs(args)
        assert result["broll_interval_seconds"] == 20.0
        assert result["broll_interval_variance"] == 3.0


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
        assert ns.broll_interval is None
        assert ns.broll_variance is None

    def test_accepts_valid_choices(self):
        parser = argparse.ArgumentParser()
        add_visual_args(parser)
        ns = parser.parse_args([
            "--video-style", "warm",
            "--audio-overlay", "bars",
            "--audio-overlay-position", "center",
        ])
        assert ns.video_style == "warm"
        assert ns.audio_overlay == "bars"
        assert ns.audio_overlay_position == "center"

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
        ns = parser.parse_args([
            "--dynamic-flow", "--human-touch", "--cliffhanger",
        ])
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

