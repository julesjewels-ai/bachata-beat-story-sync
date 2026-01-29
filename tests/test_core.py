"""
Unit tests for the core logic.
"""
import pytest
import os
from src.core.app import BachataSyncEngine
from src.core.models import AudioAnalysisResult


@pytest.fixture
def engine():
    return BachataSyncEngine()


def test_engine_initialization(engine):
    assert engine is not None


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
