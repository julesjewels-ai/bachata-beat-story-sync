"""
Unit tests for the core logic.
"""
import pytest
import os
from pydantic import ValidationError
from src.core.app import BachataSyncEngine, StoryGenerationInput

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

def test_generate_story_mock(engine, tmp_path, monkeypatch):
    """Test the generation logic with mock data."""
    # Ensure we work in the temp directory so we don't pollute the repo
    monkeypatch.chdir(tmp_path)

    mock_audio = {"bpm": 120, "peaks": [], "filename": "test.wav"}
    mock_video = []
    
    output_filename = "test_output.mp4"
    input_data = StoryGenerationInput(output_path=output_filename)

    result = engine.generate_story(mock_audio, mock_video, input_data)

    assert result == output_filename
    # Check existence in the current working directory (which is tmp_path)
    assert os.path.exists(result)

def test_generate_story_security_validation(engine):
    """Ensure path traversal attempts are blocked by Pydantic validation."""
    malicious_paths = [
        "../pwned.txt",
        "/etc/passwd",
        "subdir/test.mp4",  # Even valid subdirs are blocked by current strict policy
        "test*.mp4"         # Invalid characters
    ]
    
    for bad_path in malicious_paths:
        with pytest.raises(ValidationError):
             StoryGenerationInput(output_path=bad_path)