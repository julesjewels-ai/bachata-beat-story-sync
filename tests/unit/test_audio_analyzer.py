"""
Unit tests for AudioAnalyzer.
"""
import pytest
import os
from pydantic import ValidationError
from src.core.audio_analyzer import AudioAnalyzer, AudioAnalysisInput


@pytest.fixture
def analyzer():
    return AudioAnalyzer()


def test_initialization(analyzer):
    assert analyzer is not None


def test_validation_error():
    """Ensure invalid paths raise validation errors."""
    with pytest.raises(ValidationError) as excinfo:
        AudioAnalysisInput(file_path="non_existent_bachata.wav")
    assert "File not found" in str(excinfo.value)


def test_unsupported_extension():
    """Ensure unsupported extensions raise validation errors."""
    # We need to create a dummy file because "File not found" check runs first
    with open("test.txt", "w") as f:
        f.write("test")

    try:
        with pytest.raises(ValidationError) as excinfo:
            AudioAnalysisInput(file_path="test.txt")
        # The specific error message depends on validate_file_path
        # implementation usually "Unsupported extension"
        assert "Unsupported extension" in str(excinfo.value)
    finally:
        os.remove("test.txt")


def test_analyze_audio(analyzer):
    """Test analyze method returns expected result."""
    with open("test_audio.wav", "w") as f:
        f.write("mock")

    try:
        input_data = AudioAnalysisInput(file_path="test_audio.wav")
        result = analyzer.analyze(input_data)

        assert result.filename == "test_audio.wav"
        assert result.bpm == 128
        assert len(result.peaks) > 0
    finally:
        os.remove("test_audio.wav")
