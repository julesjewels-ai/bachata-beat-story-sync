"""
Unit tests for the pipeline orchestrator (src/pipeline.py).

All tests mock BachataSyncEngine and AudioAnalyzer to avoid FFmpeg calls.
"""

import argparse
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from src.core.models import AudioAnalysisResult, VideoAnalysisResult
from src.pipeline import (
    _build_pacing_kwargs,
    _detect_broll_dir,
    _discover_audio_files,
    _parse_duration,
    _safe_filename,
    _scan_videos,
)

# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


def _make_audio_result(bpm: float = 128.0, duration: float = 180.0):
    return AudioAnalysisResult(
        filename="test.wav",
        bpm=bpm,
        duration=duration,
        peaks=[10.0, 30.0, 60.0],
        sections=[],
        beat_times=[0.5 * i for i in range(int(duration * 2))],
        intensity_curve=[0.5] * int(duration * 2),
    )


def _make_video_clip(path: str = "/vid/clip.mp4", duration: float = 10.0):
    return VideoAnalysisResult(
        path=path,
        intensity_score=0.5,
        duration=duration,
        is_vertical=False,
        thumbnail_data=b"fakepng",
    )


# ------------------------------------------------------------------
# _discover_audio_files
# ------------------------------------------------------------------


class TestDiscoverAudioFiles:
    def test_finds_and_sorts_audio_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            for name in ["03_track.mp3", "01_track.wav", "02_track.flac"]:
                open(os.path.join(tmpdir, name), "w").close()
            result = _discover_audio_files(tmpdir)
            basenames = [os.path.basename(f) for f in result]
            assert basenames == ["01_track.wav", "02_track.flac", "03_track.mp3"]

    def test_excludes_mixed_audio_cache(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            open(os.path.join(tmpdir, "_mixed_audio.wav"), "w").close()
            open(os.path.join(tmpdir, "track.mp3"), "w").close()
            result = _discover_audio_files(tmpdir)
            assert len(result) == 1
            assert "_mixed_audio.wav" not in result[0]

    def test_ignores_non_audio_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            open(os.path.join(tmpdir, "readme.txt"), "w").close()
            open(os.path.join(tmpdir, "image.png"), "w").close()
            open(os.path.join(tmpdir, "song.mp3"), "w").close()
            result = _discover_audio_files(tmpdir)
            assert len(result) == 1


# ------------------------------------------------------------------
# _parse_duration
# ------------------------------------------------------------------


class TestParseDuration:
    def test_single_value(self):
        assert _parse_duration("60") == (60.0, 60.0)

    def test_range_value(self):
        assert _parse_duration("10-15") == (10.0, 15.0)

    def test_invalid_raises(self):
        with pytest.raises(argparse.ArgumentTypeError):
            _parse_duration("abc")


# ------------------------------------------------------------------
# _build_pacing_kwargs
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
        result = _build_pacing_kwargs(args)
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
        result = _build_pacing_kwargs(args)
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
        result = _build_pacing_kwargs(args)
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
        result = _build_pacing_kwargs(args)
        assert result["broll_interval_seconds"] == 20.0
        assert result["broll_interval_variance"] == 3.0


# ------------------------------------------------------------------
# _detect_broll_dir
# ------------------------------------------------------------------


class TestDetectBrollDir:
    def test_explicit_broll_dir(self):
        assert _detect_broll_dir("/videos", "/custom/broll") == "/custom/broll"

    def test_auto_detect_broll_subfolder(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            broll_path = os.path.join(tmpdir, "broll")
            os.makedirs(broll_path)
            assert _detect_broll_dir(tmpdir, None) == broll_path

    def test_no_broll(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            assert _detect_broll_dir(tmpdir, None) is None


# ------------------------------------------------------------------
# _safe_filename
# ------------------------------------------------------------------


class TestSafeFilename:
    def test_strips_extension_and_spaces(self):
        assert _safe_filename("/path/to/My Song.mp3") == "My_Song"

    def test_simple_name(self):
        assert _safe_filename("track_01.wav") == "track_01"


# ------------------------------------------------------------------
# _scan_videos (mocked engine)
# ------------------------------------------------------------------


class TestScanVideos:
    @patch("src.pipeline.RichProgressObserver")
    def test_strips_thumbnail_data(self, mock_obs_cls):
        mock_obs = MagicMock()
        mock_obs.__enter__ = MagicMock(return_value=mock_obs)
        mock_obs.__exit__ = MagicMock(return_value=False)
        mock_obs_cls.return_value = mock_obs

        clip = _make_video_clip()
        assert clip.thumbnail_data is not None

        engine = MagicMock()
        engine.scan_video_library.return_value = [clip]

        clips, broll = _scan_videos(engine, "/videos", None)

        assert clips[0].thumbnail_data is None
        assert broll is None

    @patch("src.pipeline.RichProgressObserver")
    def test_scans_broll_separately(self, mock_obs_cls):
        mock_obs = MagicMock()
        mock_obs.__enter__ = MagicMock(return_value=mock_obs)
        mock_obs.__exit__ = MagicMock(return_value=False)
        mock_obs_cls.return_value = mock_obs

        clip = _make_video_clip()
        broll_clip = _make_video_clip(path="/videos/broll/bg.mp4")

        engine = MagicMock()
        engine.scan_video_library.side_effect = [[clip], [broll_clip]]

        with tempfile.TemporaryDirectory() as tmpdir:
            broll_path = os.path.join(tmpdir, "broll")
            os.makedirs(broll_path)
            clips, broll = _scan_videos(engine, tmpdir, broll_path)

        assert len(clips) == 1
        assert broll is not None
        assert len(broll) == 1
        assert engine.scan_video_library.call_count == 2
