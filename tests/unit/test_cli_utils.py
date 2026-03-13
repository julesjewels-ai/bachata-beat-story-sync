"""
Unit tests for shared CLI utilities (src/cli_utils.py).
"""

import argparse
from unittest.mock import MagicMock

import pytest
from src.cli_utils import build_pacing_kwargs, parse_duration


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
