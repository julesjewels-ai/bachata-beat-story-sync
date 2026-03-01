"""
Unit tests for the AudioAnalyzer class.
"""
import pytest
import numpy as np
from unittest.mock import patch
from pydantic import ValidationError
from src.core.audio_analyzer import AudioAnalyzer, AudioAnalysisInput


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

    @patch("src.core.audio_analyzer.segment_structure")
    @patch("src.core.audio_analyzer.librosa")
    @patch("src.core.validation.os.path.exists", return_value=True)
    def test_analyze_returns_result(self, mock_exists, mock_librosa, mock_segment_structure):
        """Test that analyze returns a valid AudioAnalysisResult."""
        # Setup mocks
        mock_librosa.load.return_value = (np.zeros(100), 22050)
        mock_librosa.get_duration.return_value = 180.0
        mock_librosa.beat.beat_track.return_value = (
            128.0, np.array([10, 20, 30])
        )
        mock_librosa.onset.onset_detect.return_value = np.array([10, 20])
        mock_librosa.frames_to_time.side_effect = [
            np.array([0.5, 1.0, 1.5]),     # beat_times
            np.array([0.5, 1.0]),           # onset_times
            np.array([0.0, 0.5, 1.0, 1.5, 2.0]),  # rms_times
        ]
        mock_librosa.feature.rms.return_value = np.array(
            [[0.2, 0.5, 0.8, 0.3, 0.1]]
        )
        mock_segment_structure.return_value = [0, 1, 3]

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
        mock_segment_structure.assert_called_once()

    @patch("src.core.audio_analyzer.librosa")
    @patch("src.core.validation.os.path.exists", return_value=True)
    def test_analyze_handles_error(self, mock_exists, mock_librosa):
        """Test that analyze handles librosa errors."""
        mock_librosa.load.side_effect = Exception("Corrupt file")

        input_data = AudioAnalysisInput(file_path="bad_song.wav")

        with pytest.raises(RuntimeError) as excinfo:
            self.analyzer.analyze(input_data)

        assert "Audio analysis failed" in str(excinfo.value)
