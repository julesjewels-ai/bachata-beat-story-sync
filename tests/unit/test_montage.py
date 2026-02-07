"""
Unit tests for MontageGenerator.
"""
import pytest
from unittest.mock import MagicMock, patch
from src.core.montage import MontageGenerator
from src.core.models import AudioAnalysisResult, VideoAnalysisResult


@pytest.fixture
def montage_generator():
    return MontageGenerator()


@pytest.fixture
def mock_audio_result():
    return AudioAnalysisResult(
        file_path="mock_audio.wav",
        filename="mock_audio.wav",
        bpm=120.0,
        duration=10.0,
        peaks=[],
        sections=[]
    )


@pytest.fixture
def mock_video_results():
    return [
        VideoAnalysisResult(
            path=f"mock_video_{i}.mp4",
            intensity_score=0.5,
            duration=5.0,
            thumbnail_data=None
        ) for i in range(3)
    ]


@patch("src.core.montage.os.path.exists")
@patch("src.core.montage.AudioFileClip")
@patch("src.core.montage.VideoFileClip")
@patch("src.core.montage.concatenate_videoclips")
def test_generate_success(
    mock_concatenate,
    mock_video_clip_cls,
    mock_audio_clip_cls,
    mock_exists,
    montage_generator,
    mock_audio_result,
    mock_video_results
):
    # Setup mocks
    mock_exists.return_value = True

    mock_audio_clip = MagicMock()
    mock_audio_clip.duration = 10.0
    mock_audio_clip_cls.return_value = mock_audio_clip

    mock_video_clip = MagicMock()
    mock_video_clip.duration = 5.0
    # subclipped returns a new clip (mock)
    mock_subclip = MagicMock()
    mock_video_clip.subclipped.return_value = mock_subclip
    # resized returns a new clip (mock)
    mock_resized = MagicMock()
    mock_subclip.resized.return_value = mock_resized

    mock_video_clip_cls.return_value = mock_video_clip

    mock_final_video = MagicMock()
    mock_concatenate.return_value = mock_final_video
    mock_final_video.with_audio.return_value = mock_final_video

    # Run
    output = montage_generator.generate(
        mock_audio_result, mock_video_results, "output.mp4"
    )

    # Verify
    assert output == "output.mp4"
    mock_audio_clip_cls.assert_called_with("mock_audio.wav")
    assert mock_video_clip_cls.call_count > 0
    mock_concatenate.assert_called_once()
    mock_final_video.write_videofile.assert_called_once()


@patch("src.core.montage.os.path.exists")
def test_generate_audio_not_found(
    mock_exists, montage_generator, mock_audio_result, mock_video_results
):
    # Mock exists to return False for audio file
    def side_effect(path):
        if path == "mock_audio.wav":
            return False
        return True

    mock_exists.side_effect = side_effect

    with pytest.raises(FileNotFoundError):
        montage_generator.generate(
            mock_audio_result, mock_video_results, "out.mp4"
        )


def test_generate_no_videos(montage_generator, mock_audio_result):
    with pytest.raises(ValueError, match="No video clips"):
        montage_generator.generate(mock_audio_result, [], "out.mp4")
