"""
Unit tests for the core logic.
"""
import pytest
import os
from src.core.app import BachataSyncEngine

@pytest.fixture
def engine():
    return BachataSyncEngine()

def test_engine_initialization(engine):
    assert engine is not None
    assert ".wav" in engine.supported_audio_ext

def test_simulation_mode(engine, caplog):
    """Test that simulation mode runs without error."""
    with caplog.at_level("INFO"):
        engine.run_simulation()
    assert "--- SIMULATION MODE ---" in caplog.text

def test_file_not_found_handling(engine):
    """Ensure the engine raises errors for missing files."""
    with pytest.raises(FileNotFoundError):
        engine.analyze_audio("non_existent_bachata.wav")

def test_generate_story_mock(engine, tmp_path):
    """Test the generation logic with mock data."""
    mock_audio = {"bpm": 120, "peaks": [], "filename": "test.wav"}
    mock_video = []
    
    # We enforce strict filename characters (no dirs), so we must run in tmp_path
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        output_file = "test_output.mp4"
        result = engine.generate_story(mock_audio, mock_video, output_file)

        assert result == output_file
        assert os.path.exists(result)
    finally:
        os.chdir(cwd)