"""
Unit tests for the AudioAnalyzer class.
"""
import pytest
import numpy as np
from unittest.mock import patch
from pydantic import ValidationError
from src.core.models import AudioSection
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
        mock_librosa.frames_to_time.side_effect = [
            np.array([0.5, 1.0, 1.5]),  # beat_times
            np.array([0.5, 1.0]),  # onset_times
            np.array([0.0, 0.5, 1.0, 1.5, 2.0]),  # rms_times
            np.array([0.0, 90.0, 180.0]),  # segment_times
        ]
        mock_librosa.feature.rms.return_value = np.array(
            [[0.2, 0.5, 0.8, 0.3, 0.1]]
        )

        # Setup mocks for segmentation
        # Mock Chroma and MFCC extraction
        mock_librosa.feature.chroma_cqt.return_value = np.zeros((12, 100))
        mock_librosa.feature.mfcc.return_value = np.zeros((20, 100))
        # Mock agglomerative clustering (returns segment labels for each frame)
        # 50 frames of label 0, 50 frames of label 1
        mock_librosa.segment.agglomerative.return_value = np.array(
            [0]*50 + [1]*50
        )

        input_data = AudioAnalysisInput(file_path="song.mp3")
        result = self.analyzer.analyze(input_data)

        # Verification
        assert result.filename == "song.mp3"
        assert result.bpm == 128.0
        assert result.duration == 180.0
        assert result.peaks == [0.5, 1.0]

        # Verify sections
        assert len(result.sections) == 2
        assert isinstance(result.sections[0], AudioSection)
        assert result.sections[0].label == "Section 1"
        assert result.sections[0].start_time == 0.0
        assert result.sections[0].end_time == 90.0
        assert result.sections[0].duration == 90.0

        assert isinstance(result.sections[1], AudioSection)
        assert result.sections[1].label == "Section 2"
        assert result.sections[1].start_time == 90.0
        assert result.sections[1].end_time == 180.0
        assert result.sections[1].duration == 90.0

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

    @patch("src.core.audio_analyzer.librosa")
    @patch("src.core.validation.os.path.exists", return_value=True)
    def test_analyze_fallback_on_segmentation_failure(
        self, mock_exists, mock_librosa
    ):
        """Test that analyze falls back to full_track if segmentation fails."""
        # Setup mocks for successful basic analysis
        mock_librosa.load.return_value = (np.zeros(100), 22050)
        mock_librosa.get_duration.return_value = 180.0
        mock_librosa.beat.beat_track.return_value = (128.0, np.array([10]))

        # Configure frames_to_time to handle multiple calls without running out
        # of side_effect.
        # beat_times, onset_times, rms_times
        mock_librosa.frames_to_time.side_effect = [
            np.array([0.5]),
            np.array([0.5]),
            np.array([0.0])
        ]

        mock_librosa.onset.onset_detect.return_value = np.array([10])
        mock_librosa.feature.rms.return_value = np.array([[0.5]])

        # Mock segmentation failure (e.g. chroma extraction fails)
        mock_librosa.feature.chroma_cqt.side_effect = Exception(
            "Chroma failed"
        )

        input_data = AudioAnalysisInput(file_path="song.mp3")
        result = self.analyzer.analyze(input_data)

        assert len(result.sections) == 1
        assert result.sections[0].label == "full_track"
        assert result.sections[0].duration == 180.0
