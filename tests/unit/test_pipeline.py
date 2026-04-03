"""
Unit tests for the pipeline orchestrator (src/pipeline.py).

All tests mock BachataSyncEngine and AudioAnalyzer to avoid FFmpeg calls.
"""

import os
import tempfile
from unittest.mock import MagicMock, patch

from src.cli_utils import detect_broll_dir
from src.core.models import AudioAnalysisResult, VideoAnalysisResult
from src.pipeline import (
    _discover_audio_files,
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
# _detect_broll_dir
# ------------------------------------------------------------------


class TestDetectBrollDir:
    def test_explicit_broll_dir(self):
        assert detect_broll_dir("/videos", "/custom/broll") == "/custom/broll"

    def test_auto_detect_broll_subfolder(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            broll_path = os.path.join(tmpdir, "broll")
            os.makedirs(broll_path)
            assert detect_broll_dir(tmpdir, None) == broll_path

    def test_no_broll(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            assert detect_broll_dir(tmpdir, None) is None


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
