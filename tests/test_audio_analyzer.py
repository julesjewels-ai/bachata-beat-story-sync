"""
Unit tests for AudioAnalyzer.
"""
import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from src.core.audio_analyzer import AudioAnalyzer, AudioAnalysisInput
from src.core.models import AudioAnalysisResult

@pytest.fixture
def analyzer():
    return AudioAnalyzer()

@patch('src.core.audio_analyzer.validate_file_path')
@patch('src.core.audio_analyzer.librosa')
def test_analyze_success(mock_librosa, mock_validate, analyzer):
    """Test successful audio analysis with mocked librosa."""
    # Mock validation to pass through
    mock_validate.side_effect = lambda x, y: x

    # Setup mock return values
    mock_librosa.load.return_value = (np.array([0.1, 0.2]), 22050)
    mock_librosa.get_duration.return_value = 10.0
    mock_librosa.beat.beat_track.return_value = (120.0, np.array([10, 20]))
    mock_librosa.onset.onset_strength.return_value = np.array([0.0, 1.0, 0.0])
    mock_librosa.util.peak_pick.return_value = np.array([1])
    mock_librosa.frames_to_time.return_value = np.array([0.5])

    inp = AudioAnalysisInput(file_path="test_song.wav")

    # Execute
    result = analyzer.analyze(inp)

    # Verify
    assert isinstance(result, AudioAnalysisResult)
    assert result.filename == "test_song.wav"
    assert result.bpm == 120.0
    assert result.duration == 10.0
    assert result.peaks == [0.5]
    assert result.sections == ["main"]

    # Verify librosa calls
    mock_librosa.load.assert_called_once()

@patch('src.core.audio_analyzer.validate_file_path')
@patch('src.core.audio_analyzer.librosa')
def test_analyze_librosa_failure(mock_librosa, mock_validate, analyzer):
    """Test failure handling when librosa raises exception."""
    mock_validate.side_effect = lambda x, y: x
    mock_librosa.load.side_effect = Exception("Librosa error")

    inp = AudioAnalysisInput(file_path="bad_file.wav")

    with pytest.raises(Exception) as excinfo:
        analyzer.analyze(inp)

    assert "Librosa error" in str(excinfo.value)

@patch('src.core.audio_analyzer.validate_file_path')
@patch('src.core.audio_analyzer.librosa')
def test_analyze_tempo_array(mock_librosa, mock_validate, analyzer):
    """Test handling when librosa returns tempo as array."""
    mock_validate.side_effect = lambda x, y: x
    mock_librosa.load.return_value = (np.zeros(100), 22050)
    mock_librosa.get_duration.return_value = 5.0
    # tempo as array
    mock_librosa.beat.beat_track.return_value = (np.array([125.0]), np.array([]))
    mock_librosa.onset.onset_strength.return_value = np.zeros(10)
    mock_librosa.util.peak_pick.return_value = np.array([])
    mock_librosa.frames_to_time.return_value = np.array([])

    inp = AudioAnalysisInput(file_path="array_tempo.wav")
    result = analyzer.analyze(inp)

    assert result.bpm == 125.0
