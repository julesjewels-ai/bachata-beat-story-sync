"""
Unit tests for MontageGenerator edge cases and error handling.
"""
import pytest
from unittest.mock import MagicMock, patch, call
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
def test_resource_cleanup(
    mock_concatenate,
    mock_video_clip_cls,
    mock_audio_clip_cls,
    mock_exists,
    montage_generator,
    mock_audio_result,
    mock_video_results
):
    """Verify that all video clips (source and segments) are closed."""
    mock_exists.return_value = True

    # Audio Mock
    mock_audio_clip = MagicMock()
    mock_audio_clip.duration = 4.0  # short duration for test
    mock_audio_clip_cls.return_value = mock_audio_clip

    # Video Mock
    mock_source_clip = MagicMock()
    mock_source_clip.duration = 10.0
    mock_subclip = MagicMock()
    mock_resized = MagicMock()

    mock_source_clip.subclipped.return_value = mock_subclip
    mock_subclip.resized.return_value = mock_resized

    mock_video_clip_cls.return_value = mock_source_clip

    # Concatenate Mock
    mock_final_video = MagicMock()
    mock_concatenate.return_value = mock_final_video
    mock_final_video.with_audio.return_value = mock_final_video

    montage_generator.generate(
        mock_audio_result, mock_video_results, "output.mp4"
    )

    # Check if source clips were closed
    assert mock_source_clip.close.called
    # Check if segments were closed
    assert mock_resized.close.called
    # Check if audio was closed
    assert mock_audio_clip.close.called
    # Check if final video was closed
    assert mock_final_video.close.called


@patch("src.core.montage.os.path.exists")
@patch("src.core.montage.AudioFileClip")
@patch("src.core.montage.VideoFileClip")
@patch("src.core.montage.concatenate_videoclips")
def test_short_video_skipped(
    mock_concatenate,
    mock_video_clip_cls,
    mock_audio_clip_cls,
    mock_exists,
    montage_generator,
    mock_audio_result,
    mock_video_results
):
    """Verify that short videos are skipped and closed immediately."""
    mock_exists.return_value = True

    mock_audio_clip = MagicMock()
    mock_audio_clip.duration = 4.0
    mock_audio_clip_cls.return_value = mock_audio_clip

    # First video is short, second is long
    short_clip = MagicMock()
    short_clip.duration = 0.5  # Less than beat_duration (0.5s)

    long_clip = MagicMock()
    long_clip.duration = 10.0
    sub_clip = MagicMock()
    resized_clip = MagicMock()
    long_clip.subclipped.return_value = sub_clip
    sub_clip.resized.return_value = resized_clip

    mock_video_clip_cls.side_effect = [short_clip, long_clip, long_clip, long_clip]

    # Force specific order or mock shuffle?
    # Since we can't easily control shuffle, we patch random.shuffle to be deterministic
    with patch("random.shuffle", side_effect=lambda x: x):
        # But queue logic might pop differently.
        # Instead, let's just ensure short_clip.close() is called.

        montage_generator.generate(
            mock_audio_result, mock_video_results, "output.mp4"
        )

    assert short_clip.close.called
    assert long_clip.close.called


@patch("src.core.montage.os.path.exists")
@patch("src.core.montage.AudioFileClip")
@patch("src.core.montage.VideoFileClip")
def test_all_videos_invalid(
    mock_video_clip_cls,
    mock_audio_clip_cls,
    mock_exists,
    montage_generator,
    mock_audio_result,
    mock_video_results
):
    """Verify RuntimeError if no valid clips can be generated."""
    mock_exists.return_value = True

    mock_audio_clip = MagicMock()
    mock_audio_clip.duration = 10.0
    mock_audio_clip_cls.return_value = mock_audio_clip

    # All videos raise exception
    mock_video_clip_cls.side_effect = Exception("Corrupt file")

    with pytest.raises(RuntimeError, match="No valid video clips"):
        montage_generator.generate(
            mock_audio_result, mock_video_results, "output.mp4"
        )
