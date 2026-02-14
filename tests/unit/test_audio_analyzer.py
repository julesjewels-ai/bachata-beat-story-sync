"""
Unit tests for the AudioAnalyzer class.
"""
import pytest
import numpy as np
from unittest.mock import patch
from pydantic import ValidationError
from src.core.audio_analyzer import AudioAnalyzer, AudioAnalysisInput
from src.core.models import AudioSection


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
        mock_librosa.beat.beat_track.return_value = (
            128.0, np.array([10, 20, 30])
        )
        mock_librosa.onset.onset_detect.return_value = np.array([10, 20])

        # Mocks for segmentation
        mock_librosa.feature.chroma_cqt.return_value = np.zeros((12, 100))
        mock_librosa.feature.mfcc.return_value = np.zeros((20, 100))
        mock_librosa.segment.recurrence_matrix.return_value = np.zeros((100, 100))

        # Mock agglomerative clustering labels (3 sections)
        # 0 for first 30 frames, 1 for next 30, 2 for last 40
        labels = np.array([0]*30 + [1]*30 + [2]*40)
        mock_librosa.segment.agglomerative.return_value = labels

        # Configure frames_to_time side effects
        def frames_to_time_side_effect(frames, sr=22050, hop_length=512):
            # If frames is a scalar or small array, return specific values
            if np.array_equal(frames, np.array([10, 20, 30])): # beat_frames
                return np.array([0.5, 1.0, 1.5])
            if np.array_equal(frames, np.array([10, 20])): # onset_frames
                return np.array([0.5, 1.0])
            if len(frames) == 5: # rms_times (len(rms) is 5 in mock below)
                return np.array([0.0, 0.5, 1.0, 1.5, 2.0])
            if len(frames) == 100: # sections (len(labels) is 100)
                return np.linspace(0, 180, 100)
            return np.zeros_like(frames, dtype=float)

        mock_librosa.frames_to_time.side_effect = frames_to_time_side_effect

        mock_librosa.feature.rms.return_value = np.array(
            [[0.2, 0.5, 0.8, 0.3, 0.1]]
        )

        input_data = AudioAnalysisInput(file_path="song.mp3")
        result = self.analyzer.analyze(input_data)

        # Verification
        assert result.filename == "song.mp3"
        assert result.bpm == 128.0
        assert result.duration == 180.0
        assert result.peaks == [0.5, 1.0]
        assert result.beat_times == [0.5, 1.0, 1.5]

        # Verify sections
        assert len(result.sections) == 3
        assert isinstance(result.sections[0], AudioSection)
        assert result.sections[0].label == "Section 1"
        assert result.sections[0].start_time == 0.0
        # Check end time of first section (index 30 -> 30/100 * 180 = 54.0 roughly)
        # Since we used linspace(0, 180, 100), index 30 corresponds to 30 * (180/99) approx 54.54
        expected_end_1 = 30 * (180.0 / 99.0)
        assert abs(result.sections[0].end_time - expected_end_1) < 0.001

        # Verify librosa calls
        mock_librosa.load.assert_called_once()
        mock_librosa.beat.beat_track.assert_called_once()
        mock_librosa.onset.onset_detect.assert_called_once()
        mock_librosa.feature.rms.assert_called_once()
        mock_librosa.segment.agglomerative.assert_called_once()

    @patch("src.core.audio_analyzer.librosa")
    @patch("src.core.validation.os.path.exists", return_value=True)
    def test_analyze_handles_error(self, mock_exists, mock_librosa):
        """Test that analyze handles librosa errors."""
        mock_librosa.load.side_effect = Exception("Corrupt file")

        input_data = AudioAnalysisInput(file_path="bad_song.wav")

        with pytest.raises(RuntimeError) as excinfo:
            self.analyzer.analyze(input_data)

        assert "Audio analysis failed" in str(excinfo.value)
