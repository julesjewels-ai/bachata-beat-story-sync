"""
Unit tests for the AudioAnalyzer class.
"""

from unittest.mock import patch

import numpy as np
import pytest
from pydantic import ValidationError
from src.core.audio_analyzer import AudioAnalysisInput, AudioAnalyzer, find_audio_hooks
from src.core.models import AudioAnalysisResult, MusicalSection


class TestAudioAnalyzer:
    def setup_method(self):
        self.analyzer = AudioAnalyzer()

    def test_initialization(self):
        """Test that the analyzer initializes correctly."""
        assert self.analyzer is not None

    @patch("src.core.validation.os.path.exists", return_value=True)
    def test_input_validation_valid(self, mock_exists):
        """Test validation with a valid file extension."""
        input_data = AudioAnalysisInput(file_path="test_audio.wav")
        assert input_data.file_path == "test_audio.wav"

    @patch("src.core.validation.os.path.exists", return_value=True)
    def test_input_validation_invalid_extension(self, mock_exists):
        """Test validation with an invalid file extension."""
        with pytest.raises(ValidationError) as excinfo:
            AudioAnalysisInput(file_path="test_video.mp4")
        assert "Unsupported extension" in str(excinfo.value)

    @patch("src.core.validation.os.path.exists", return_value=False)
    def test_input_validation_file_not_found(self, mock_exists):
        """Test validation when file does not exist."""
        with pytest.raises(ValidationError) as excinfo:
            AudioAnalysisInput(file_path="ghost.wav")
        assert "File not found" in str(excinfo.value)

    @patch("src.core.audio_analyzer.librosa")
    @patch("src.core.validation.os.path.exists", return_value=True)
    def test_analyze_returns_result(self, mock_exists, mock_librosa):
        """Test that analyze returns a valid AudioAnalysisResult."""
        # Setup mocks
        mock_librosa.load.return_value = (np.zeros(100), 22050)
        mock_librosa.get_duration.return_value = 180.0
        mock_librosa.beat.beat_track.return_value = (128.0, np.array([10, 20, 30]))
        mock_librosa.onset.onset_detect.return_value = np.array([10, 20])
        mock_librosa.frames_to_time.side_effect = [
            np.array([0.5, 1.0, 1.5]),  # beat_times
            np.array([0.5, 1.0]),  # onset_times
            np.array([0.0, 0.5, 1.0, 1.5, 2.0]),  # rms_times
        ]
        mock_librosa.feature.rms.return_value = np.array([[0.2, 0.5, 0.8, 0.3, 0.1]])

        input_data = AudioAnalysisInput(file_path="song.mp3")
        result = self.analyzer.analyze(input_data)

        # Verification
        assert result.filename == "song.mp3"
        assert result.bpm == 128.0
        assert result.duration == 180.0
        assert result.peaks == [0.5, 1.0]
        assert len(result.sections) >= 1
        assert result.sections[0].start_time >= 0.0

        # New fields
        assert result.beat_times == [0.5, 1.0, 1.5]
        assert len(result.intensity_curve) == 3
        # Intensity values should be normalised 0.0-1.0
        for val in result.intensity_curve:
            assert 0.0 <= val <= 1.0

        # Verify librosa calls
        mock_librosa.load.assert_called_once()
        mock_librosa.beat.beat_track.assert_called_once()
        mock_librosa.onset.onset_detect.assert_called_once()
        mock_librosa.feature.rms.assert_called_once()

    @patch("src.core.audio_analyzer.librosa")
    @patch("src.core.validation.os.path.exists", return_value=True)
    def test_analyze_handles_error(self, mock_exists, mock_librosa):
        """Test that analyze handles librosa errors."""
        mock_librosa.load.side_effect = Exception("Corrupt file")

        input_data = AudioAnalysisInput(file_path="bad_song.wav")

        with pytest.raises(RuntimeError) as excinfo:
            self.analyzer.analyze(input_data)

        assert "Audio analysis failed" in str(excinfo.value)


# ------------------------------------------------------------------
# FEAT-019: find_audio_hooks() tests
# ------------------------------------------------------------------

def _make_audio(
    duration: float = 120.0,
    bpm: float = 120.0,
    beat_count: int = 240,
    peaks: list[float] | None = None,
    sections: list[MusicalSection] | None = None,
    intensity: list[float] | None = None,
) -> AudioAnalysisResult:
    """Helper to build synthetic AudioAnalysisResult for hook tests."""
    beat_times = [i * (60.0 / bpm) for i in range(beat_count)]
    if intensity is None:
        intensity = [0.5] * beat_count
    return AudioAnalysisResult(
        filename="hook_test.wav",
        bpm=bpm,
        duration=duration,
        peaks=peaks or [],
        sections=sections or [],
        beat_times=beat_times,
        intensity_curve=intensity,
    )


class TestFindAudioHooks:
    """Tests for find_audio_hooks (FEAT-019)."""

    def test_returns_correct_count(self):
        audio = _make_audio(duration=120.0, beat_count=240)
        hooks = find_audio_hooks(audio, short_duration=15.0, count=3)
        assert len(hooks) == 3

    def test_skips_first_second(self):
        audio = _make_audio(duration=60.0, beat_count=120)
        hooks = find_audio_hooks(audio, short_duration=10.0, count=5)
        for h in hooks:
            assert h >= 1.0, f"Hook at {h}s violates 1s skip"

    def test_respects_duration_limit(self):
        audio = _make_audio(duration=30.0, beat_count=60)
        hooks = find_audio_hooks(audio, short_duration=15.0, count=5)
        for h in hooks:
            assert h + 15.0 <= audio.duration

    def test_minimum_separation(self):
        audio = _make_audio(duration=120.0, beat_count=240)
        hooks = find_audio_hooks(audio, short_duration=15.0, count=4)
        min_sep = 15.0 * 0.5
        for i, a in enumerate(hooks):
            for b in hooks[i + 1 :]:
                assert abs(a - b) >= min_sep, (
                    f"Hooks {a:.1f}s and {b:.1f}s are too close"
                )

    def test_prefers_high_intensity(self):
        # First half low, second half high
        intensities = [0.1] * 120 + [0.9] * 120
        audio = _make_audio(
            duration=120.0, beat_count=240, intensity=intensities
        )
        hooks = find_audio_hooks(audio, short_duration=10.0, count=1)
        # Best hook should be in the high-intensity second half
        assert hooks[0] >= 60.0

    def test_section_boundary_bonus(self):
        # Section boundary at exactly 5.0s — candidate at 1.0s should
        # score bonus for pace_target=4.0 ± 1.0 => match at 5.0
        sections = [
            MusicalSection(start_time=0.0, end_time=5.0, label="intro", avg_intensity=0.3),
            MusicalSection(start_time=5.0, end_time=30.0, label="verse", avg_intensity=0.7),
        ]
        audio = _make_audio(
            duration=30.0, beat_count=60, sections=sections,
            intensity=[0.5] * 60,
        )
        hooks = find_audio_hooks(audio, short_duration=10.0, count=1)
        # Hook near 1.0s should benefit from the section boundary at 5.0s
        assert hooks[0] <= 2.0

    def test_fallback_empty_data(self):
        audio = AudioAnalysisResult(
            filename="empty.wav",
            bpm=120.0,
            duration=10.0,
            peaks=[],
            sections=[],
            beat_times=[],
            intensity_curve=[],
        )
        hooks = find_audio_hooks(audio, short_duration=5.0, count=3)
        assert hooks == [0.0]

    def test_single_count(self):
        audio = _make_audio(duration=60.0, beat_count=120)
        hooks = find_audio_hooks(audio, short_duration=10.0, count=1)
        assert len(hooks) == 1
        assert isinstance(hooks[0], float)

