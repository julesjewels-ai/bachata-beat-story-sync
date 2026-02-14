"""
Unit tests for the core logic.
"""
import pytest
import os
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

    mock_audio = AudioAnalysisResult(
        bpm=120,
        peaks=[],
        filename="test.wav",
        duration=100,
        sections=[],
        beat_times=[],
        intensity_curve=[],
    )
    mock_video = [
        VideoAnalysisResult(
            path="/videos/clip.mp4",
            intensity_score=0.5,
            duration=10.0,
            thumbnail_data=None,
        )
    ]

    # No beats → segment plan is empty → ValueError
    with pytest.raises(ValueError, match="segment plan"):
        engine.generate_story(
            mock_audio, mock_video, "/tmp/output.mp4"
        )
