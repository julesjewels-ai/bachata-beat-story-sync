from unittest.mock import MagicMock, patch

import pytest
from src.core.models import PacingConfig
from src.core.montage import MontageGenerator


class TestAudioOverlay:
    """Tests for FEAT-013: Music-Synced Waveform Overlay."""

    @pytest.fixture
    def generator(self):
        return MontageGenerator()

    def test_audio_overlay_default_is_none(self):
        """Default audio_overlay is 'none'."""
        config = PacingConfig()
        assert config.audio_overlay == "none"
        assert config.audio_overlay_opacity == 0.5

    def test_audio_overlay_accepts_valid_values(self):
        """Valid overlay values are accepted."""
        config1 = PacingConfig(audio_overlay="none")
        assert config1.audio_overlay == "none"
        config2 = PacingConfig(audio_overlay="waveform")
        assert config2.audio_overlay == "waveform"
        config3 = PacingConfig(audio_overlay="bars")
        assert config3.audio_overlay == "bars"

    def test_audio_overlay_rejects_invalid(self):
        """Invalid audio_overlay values are rejected by Pydantic."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            PacingConfig(audio_overlay="neon")  # type: ignore[arg-type]

    @patch("src.core.ffmpeg_utils.subprocess.run")
    def test_overlay_audio_none_uses_stream_copy(self, mock_run, generator):
        """When audio_overlay='none', stream copy is used."""
        mock_run.return_value = MagicMock(returncode=0)
        config = PacingConfig(audio_overlay="none")

        generator._overlay_audio("video.mp4", "audio.wav", "out.mp4", config)

        call_args = mock_run.call_args[0][0]
        assert "-c:v" in call_args
        vcodec_idx = call_args.index("-c:v") + 1
        assert call_args[vcodec_idx] == "copy"
        assert "-filter_complex" not in call_args

    @patch("src.core.ffmpeg_utils.subprocess.run")
    def test_overlay_audio_waveform(self, mock_run, generator):
        """When audio_overlay='waveform', command includes showwaves filter."""
        mock_run.return_value = MagicMock(returncode=0)
        config = PacingConfig(audio_overlay="waveform")

        generator._overlay_audio("video.mp4", "audio.wav", "out.mp4", config)

        call_args = mock_run.call_args[0][0]
        cmd_str = " ".join(str(c) for c in call_args)

        assert "-filter_complex" in cmd_str
        assert "showwaves" in cmd_str
        assert "-c:v copy" not in cmd_str
        assert "libx264" in cmd_str
        assert "1920x280" in cmd_str

    @patch("src.core.ffmpeg_utils.subprocess.run")
    def test_overlay_audio_bars_shorts(self, mock_run, generator):
        """When audio_overlay='bars' and is_shorts=True, uses showcqt and 1080 width."""
        mock_run.return_value = MagicMock(returncode=0)
        config = PacingConfig(audio_overlay="bars", is_shorts=True)

        generator._overlay_audio("video.mp4", "audio.wav", "out.mp4", config)

        call_args = mock_run.call_args[0][0]
        cmd_str = " ".join(str(c) for c in call_args)

        assert "-filter_complex" in cmd_str
        assert "showcqt" in cmd_str
        assert "1080x280" in cmd_str
