"""
Unit tests for the core logic.
"""
import pytest
import os
from unittest.mock import MagicMock
from pydantic import ValidationError
from src.core.app import BachataSyncEngine, AudioAnalysisInput
from src.core.models import AudioAnalysisResult, VideoAnalysisResult

@pytest.fixture
def engine():
    return BachataSyncEngine()

def test_engine_initialization(engine):
    assert engine is not None
    assert ".wav" in engine.supported_audio_ext

def test_file_not_found_handling(engine):
    """Ensure the engine raises errors for missing files."""
    # Since we are using Pydantic, the validation happens at instantiation of AudioAnalysisInput
    # and it raises ValueError (which Pydantic wraps or we see it directly depending on usage)
    # The validate_path method raises ValueError.
    # When creating the model: AudioAnalysisInput(file_path="...")

    with pytest.raises(ValidationError) as excinfo:
        AudioAnalysisInput(file_path="non_existent_bachata.wav")
    assert "File not found" in str(excinfo.value)

def test_analyze_audio_with_model(engine):
    """Test analyze_audio with valid input model (mocked existence)."""
    # Create a dummy file
    with open("test_audio.wav", "w") as f:
        f.write("mock")

    try:
        inp = AudioAnalysisInput(file_path="test_audio.wav")
        res = engine.analyze_audio(inp)
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

def test_scan_video_library_with_observer(engine, tmp_path):
    """Test scan_video_library calls the observer."""
    # Create dummy video files
    video_dir = tmp_path / "videos"
    video_dir.mkdir()
    (video_dir / "vid1.mp4").touch()
    (video_dir / "vid2.mp4").touch()

    # Mock engine._process_video_file because it tries to read the file with cv2
    engine._process_video_file = MagicMock(return_value=VideoAnalysisResult(path="p", intensity_score=1.0, duration=10))

    observer = MagicMock()
    engine.scan_video_library(str(video_dir), observer=observer)

    # Verify observer was called
    # Should be called once for init (0/2) and once for each file (1/2, 2/2)
    assert observer.on_progress.call_count == 3

    calls = observer.on_progress.call_args_list
    # First call: 0, 2
    assert calls[0][0][0] == 0
    assert calls[0][0][1] == 2

    # Last call: 2, 2
    assert calls[2][0][0] == 2
    assert calls[2][0][1] == 2
