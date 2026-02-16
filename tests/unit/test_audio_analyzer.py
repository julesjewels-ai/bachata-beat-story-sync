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

    @patch("src.core.audio_analyzer.sklearn.cluster.AgglomerativeClustering")
    @patch("src.core.audio_analyzer.librosa")
    @patch("src.core.validation.os.path.exists", return_value=True)
    def test_analyze_returns_result(self, mock_exists, mock_librosa, mock_agg_cls):
        """Test that analyze returns a valid AudioAnalysisResult."""
        # Setup mocks
        mock_librosa.load.return_value = (np.zeros(100), 22050)
        mock_librosa.get_duration.return_value = 180.0
        mock_librosa.beat.beat_track.return_value = (
            128.0, np.array([10, 20, 30])
        )
        mock_librosa.onset.onset_detect.return_value = np.array([10, 20])
        mock_librosa.frames_to_time.side_effect = [
            np.array([0.0, 0.5, 1.0]),     # beat_times
            np.array([0.5, 1.0]),           # onset_times
            np.array([0.0, 0.5, 1.0, 1.5, 2.0]),  # rms_times
        ]
        mock_librosa.feature.rms.return_value = np.array(
            [[0.2, 0.5, 0.8, 0.3, 0.1]]
        )

        # New mocks for structural segmentation
        mock_librosa.feature.chroma_cqt.return_value = np.zeros((12, 100))
        mock_librosa.feature.mfcc.return_value = np.zeros((13, 100))
        mock_librosa.time_to_frames.return_value = np.array([0, 1, 2]) # beat frames
        mock_librosa.util.sync.return_value = np.zeros((12, 3)) # synced features
        mock_librosa.segment.recurrence_matrix.return_value = np.zeros((3, 3))

        # Mock AgglomerativeClustering
        mock_agg_instance = mock_agg_cls.return_value
        # Labels: 0, 1, 1 (means boundary between 0 and 1, i.e., at index 1)
        # Index 1 in new beat_times is 0.5s.
        mock_agg_instance.labels_ = np.array([0, 1, 1])

        input_data = AudioAnalysisInput(file_path="song.mp3")
        result = self.analyzer.analyze(input_data)

        # Verification
        assert result.filename == "song.mp3"
        assert result.bpm == 128.0
        assert result.duration == 180.0
        assert result.peaks == [0.5, 1.0]

        # Sections verification
        # beat_times are [0.0, 0.5, 1.0].
        # Change at index 1 (0.5s).
        # Boundaries: 0.0 (start), 0.5 (index 1), 180.0 (end).
        # Sections: 0.0-0.5, 0.5-180.0.
        assert len(result.sections) == 2
        assert result.sections[0].start_time == 0.0
        assert result.sections[0].end_time == 0.5
        assert result.sections[1].start_time == 0.5
        assert result.sections[1].end_time == 180.0

        # New fields
        assert result.beat_times == [0.0, 0.5, 1.0]
        assert len(result.intensity_curve) == 3

        # Verify calls
        mock_librosa.load.assert_called_once()
        mock_librosa.beat.beat_track.assert_called_once()
        mock_librosa.onset.onset_detect.assert_called_once()
        mock_librosa.feature.rms.assert_called_once()
        mock_librosa.feature.chroma_cqt.assert_called_once()
        mock_librosa.feature.mfcc.assert_called_once()
        mock_librosa.segment.recurrence_matrix.assert_called_once()
        mock_agg_cls.assert_called_once()
        mock_agg_instance.fit.assert_called_once()

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
    def test_analyze_fallback_on_segmentation_failure(self, mock_exists, mock_librosa):
        """Test fallback to single section if segmentation fails."""
        # Setup basic mocks
        mock_librosa.load.return_value = (np.zeros(100), 22050)
        mock_librosa.get_duration.return_value = 180.0
        mock_librosa.beat.beat_track.return_value = (120.0, np.array([10]))
        mock_librosa.frames_to_time.side_effect = [
            np.array([0.5, 1.0]),     # beat_times
            np.array([]),           # onset_times
            np.array([0.5, 1.0]),  # rms_times
        ]
        # Fix: Ensure RMS has same length as rms_times (2)
        mock_librosa.feature.rms.return_value = np.array([[0.5, 0.5]])

        # Simulate segmentation failure
        mock_librosa.feature.chroma_cqt.side_effect = Exception("Segmentation error")

        input_data = AudioAnalysisInput(file_path="song.mp3")
        result = self.analyzer.analyze(input_data)

        # Should fall back to 1 section covering full track
        assert len(result.sections) == 1
        assert result.sections[0].label == "full_track"
        assert result.sections[0].start_time == 0.0
        assert result.sections[0].end_time == 180.0
