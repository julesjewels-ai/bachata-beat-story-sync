"""
Unit tests for the core logic.
"""
import pytest
import os
from unittest.mock import MagicMock
from typing import List
from src.core.app import BachataSyncEngine
from src.core.models import AudioAnalysisResult, VideoAnalysisResult


@pytest.fixture
def engine():
    return BachataSyncEngine()


def test_engine_initialization(engine):
    assert engine is not None
    # engine.supported_audio_ext is removed


def test_generate_story_mock(engine, tmp_path):
    """Test the generation logic with mock data."""
    # Mock internal montage generator
    engine.montage_generator = MagicMock()
    output_file = tmp_path / "test_output.mp4"
    engine.montage_generator.generate.return_value = str(output_file)

    mock_audio = AudioAnalysisResult(
        file_path="mock/test.wav",
        bpm=120,
        peaks=[],
        filename="test.wav",
        duration=100,
        sections=[]
    )
    mock_video: List[VideoAnalysisResult] = []

    result = engine.generate_story(mock_audio, mock_video, str(output_file))

    assert result == str(output_file)
    engine.montage_generator.generate.assert_called_once()
