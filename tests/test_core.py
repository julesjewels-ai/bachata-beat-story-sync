"""
Unit tests for the core logic.
"""
import pytest
import os
from pydantic import ValidationError
from src.core.app import BachataSyncEngine
from src.core.audio_analyzer import AudioAnalyzer, AudioAnalysisInput, SUPPORTED_AUDIO_EXTENSIONS
from src.core.models import AudioAnalysisResult, VideoAnalysisResult

@pytest.fixture
def engine():
    return BachataSyncEngine()

@pytest.fixture
def analyzer():
    return AudioAnalyzer()

def test_engine_initialization(engine):
    assert engine is not None

def test_analyzer_initialization(analyzer):
    assert analyzer is not None
    assert ".wav" in SUPPORTED_AUDIO_EXTENSIONS

def test_file_not_found_handling():
    """Ensure the input model raises errors for missing files."""
    with pytest.raises(ValidationError) as excinfo:
        AudioAnalysisInput(file_path="non_existent_bachata.wav")
    assert "File not found" in str(excinfo.value)

def test_analyze_audio_with_model(analyzer):
    """Test analyze with valid input model (mocked existence)."""
    # Create a dummy file
    with open("test_audio.wav", "w") as f:
        f.write("mock")

    try:
        inp = AudioAnalysisInput(file_path="test_audio.wav")
        res = analyzer.analyze(inp)
        assert res.bpm == 128
    finally:
        os.remove("test_audio.wav")

def test_generate_story_mock(engine, tmp_path):
    """Test the generation logic with mock data."""
    mock_audio = AudioAnalysisResult(
        bpm=120,
        peaks=[],
        filename="test.wav",
        duration=100,
        sections=[]
    )
    mock_video = []
    output_file = tmp_path / "test_output.mp4"
    
    result = engine.generate_story(mock_audio, mock_video, str(output_file))
    
    assert result == str(output_file)
    assert os.path.exists(result)
