"""
Unit tests for the core logic.
"""
import pytest
import os
from typing import List
from unittest.mock import patch, MagicMock
from src.core.app import BachataSyncEngine
from src.core.models import AudioAnalysisResult, VideoAnalysisResult


@pytest.fixture
def engine():
    return BachataSyncEngine()


def test_engine_initialization(engine):
    assert engine is not None
    assert engine.montage_generator is not None


def test_generate_story_delegates_to_montage():
    """Test that generate_story delegates to MontageGenerator."""
    engine = BachataSyncEngine()
    mock_montage_gen = MagicMock()
    mock_montage_gen.generate.return_value = "/tmp/output.mp4"
    engine.montage_generator = mock_montage_gen

    mock_audio = AudioAnalysisResult(
        bpm=120,
        peaks=[],
        filename="test.wav",
        duration=100,
        sections=[]
    )
    mock_video: List[VideoAnalysisResult] = []

    result = engine.generate_story(
        mock_audio, mock_video, "/tmp/output.mp4"
    )

    mock_montage_gen.generate.assert_called_once_with(
        mock_audio, mock_video, "/tmp/output.mp4", None
    )
    assert result == "/tmp/output.mp4"
