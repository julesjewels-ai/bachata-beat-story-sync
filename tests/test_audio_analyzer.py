"""
Unit tests for the AudioAnalyzer.
"""
import pytest
import os
from pydantic import ValidationError
from src.core.audio_analyzer import AudioAnalyzer, AudioAnalysisInput, SUPPORTED_AUDIO_EXTENSIONS

@pytest.fixture
def analyzer():
    return AudioAnalyzer()

def test_analyzer_supported_extensions():
    assert ".wav" in SUPPORTED_AUDIO_EXTENSIONS
    assert ".mp3" in SUPPORTED_AUDIO_EXTENSIONS

def test_file_not_found_handling():
    """Ensure the analyzer validation raises errors for missing files."""
    with pytest.raises(ValidationError) as excinfo:
        AudioAnalysisInput(file_path="non_existent_bachata.wav")
    assert "File not found" in str(excinfo.value)

def test_analyze_audio_mock(analyzer):
    """Test analyze with valid input model (mocked existence)."""
    # Create a dummy file
    with open("test_audio.wav", "w") as f:
        f.write("mock")

    try:
        inp = AudioAnalysisInput(file_path="test_audio.wav")
        res = analyzer.analyze(inp)
        assert res.bpm == 128
        assert res.filename == "test_audio.wav"
    finally:
        os.remove("test_audio.wav")
