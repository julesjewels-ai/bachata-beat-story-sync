"""
Unit tests for the core logic.
"""
import pytest
import os
from unittest.mock import patch
from src.core.app import BachataSyncEngine
from src.core.models import AudioAnalysisResult, VideoAnalysisResult, AudioSection


@pytest.fixture
def engine():
    return BachataSyncEngine()


def test_engine_initialization(engine):
    assert engine is not None
    assert engine.montage_generator is not None


@patch("src.core.montage.shutil.which", return_value="/usr/bin/ffmpeg")
def test_generate_story_delegates_to_montage(mock_which):
    """Test that generate_story delegates to MontageGenerator."""
    engine = BachataSyncEngine()

    mock_audio = AudioAnalysisResult(
        bpm=120,
        peaks=[],
        filename="test.wav",
        duration=100,
        sections=[
            AudioSection(start_time=0.0, end_time=100.0, duration=100.0, label="full_track")
        ],
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
