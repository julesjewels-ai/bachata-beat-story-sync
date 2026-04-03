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


# ------------------------------------------------------------------
# FEAT-030: Per-Track Video Clip Pools
# ------------------------------------------------------------------


class TestPerTrackClipPools:
    def test_get_track_video_dir_uses_per_track_folder(self):
        """Test that per-track clip folder is used if configured."""
        from src.core.models import PacingConfig
        from src.pipeline import _get_track_video_dir

        with tempfile.TemporaryDirectory() as tmpdir:
            per_track_dir = os.path.join(tmpdir, "track1_clips")
            os.makedirs(per_track_dir)

            config = PacingConfig(
                per_track_clips={"track1.wav": per_track_dir}
            )
            track_path = "/audio/track1.wav"

            result = _get_track_video_dir(track_path, config, "/global/videos")
            assert result == per_track_dir

    def test_get_track_video_dir_fallback_to_global(self):
        """Test that global video-dir is used if no per-track config."""
        from src.core.models import PacingConfig
        from src.pipeline import _get_track_video_dir

        config = PacingConfig(per_track_clips={})
        track_path = "/audio/track1.wav"
        global_dir = "/global/videos"

        result = _get_track_video_dir(track_path, config, global_dir)
        assert result == global_dir

    def test_get_track_video_dir_raises_if_path_missing(self):
        """Test that FileNotFoundError is raised if per-track path doesn't exist."""
        from src.core.models import PacingConfig
        from src.pipeline import _get_track_video_dir

        config = PacingConfig(
            per_track_clips={"track1.wav": "/nonexistent/path"}
        )
        track_path = "/audio/track1.wav"

        with pytest.raises(FileNotFoundError) as exc_info:
            _get_track_video_dir(track_path, config, "/global/videos")
        assert "track1.wav" in str(exc_info.value)


# ------------------------------------------------------------------
# FEAT-031: Per-Track Video Style Filters
# ------------------------------------------------------------------


class TestPerTrackVideoStyles:
    def test_get_track_video_style_uses_per_track_style(self):
        """Test that per-track style is used if configured."""
        from src.core.models import PacingConfig
        from src.pipeline import _get_track_video_style

        config = PacingConfig(
            video_style="none",
            per_track_styles={"track1.wav": "vintage"}
        )
        track_path = "/audio/track1.wav"

        result = _get_track_video_style(track_path, config)
        assert result == "vintage"

    def test_get_track_video_style_fallback_to_global(self):
        """Test that global video_style is used if no per-track config."""
        from src.core.models import PacingConfig
        from src.pipeline import _get_track_video_style

        config = PacingConfig(
            video_style="bw",
            per_track_styles={}
        )
        track_path = "/audio/track1.wav"

        result = _get_track_video_style(track_path, config)
        assert result == "bw"

    def test_get_track_video_style_raises_if_invalid(self):
        """Test that invalid per-track style is rejected at config validation."""
        from pydantic import ValidationError
        from src.core.models import PacingConfig

        # Invalid styles are caught at config validation time (Pydantic validator)
        with pytest.raises(ValidationError) as exc_info:
            PacingConfig(
                video_style="none",
                per_track_styles={"track1.wav": "invalid_style"}
            )
        assert "invalid_style" in str(exc_info.value)
        assert "Valid options" in str(exc_info.value)


# ------------------------------------------------------------------
# Config Validation (FEAT-030 & FEAT-031)
# ------------------------------------------------------------------


class TestPerTrackConfigValidation:
    def test_pacing_config_validates_per_track_styles(self):
        """Test that PacingConfig validates per_track_styles on construction."""
        from src.core.models import PacingConfig

        # Valid styles should pass
        config = PacingConfig(
            per_track_styles={
                "track1.wav": "vintage",
                "track2.wav": "bw",
                "track3.wav": "cool"
            }
        )
        assert config.per_track_styles["track1.wav"] == "vintage"

    def test_pacing_config_rejects_invalid_per_track_styles(self):
        """Test that PacingConfig rejects invalid per_track_styles."""
        from pydantic import ValidationError
        from src.core.models import PacingConfig

        with pytest.raises(ValidationError) as exc_info:
            PacingConfig(
                per_track_styles={
                    "track1.wav": "invalid_style"
                }
            )
        assert "invalid_style" in str(exc_info.value)

    def test_pacing_config_accepts_empty_per_track_mappings(self):
        """Test that empty per_track_clips/styles dicts are allowed."""
        from src.core.models import PacingConfig

        config = PacingConfig(per_track_clips={}, per_track_styles={})
        assert config.per_track_clips == {}
        assert config.per_track_styles == {}
