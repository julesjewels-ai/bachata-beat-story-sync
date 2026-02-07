"""
Edge case tests for MontageGenerator.
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
@patch("src.core.montage.VideoFileClip")
@patch("src.core.montage.AudioFileClip")
def test_generate_skip_missing_video(
    mock_audio_cls, mock_video_cls, mock_exists,
    montage_generator, mock_audio_result, mock_video_results
):
    # Mock audio file exists, but video file missing
    def exists_side_effect(path):
        if path == "mock_audio.wav":
            return True
        if path == "mock_video_0.mp4":
            return False
        return True

    mock_exists.side_effect = exists_side_effect

    mock_audio_cls.return_value.duration = 4.0  # Just enough for 2 clips (2s each at 120bpm)

    # Mock video clip creation for existing videos
    mock_video_clip = MagicMock()
    mock_video_clip.duration = 5.0
    mock_video_cls.return_value = mock_video_clip
    # Ensure chained calls return mocks
    mock_video_clip.subclipped.return_value = mock_video_clip
    mock_video_clip.resized.return_value = mock_video_clip

    # We expect it to skip video 0 and use others
    # Since generate randomizes, we can't be sure which one is picked first,
    # but we can check that it doesn't crash and returns a path.

    # We need to mock concatenate_videoclips too
    with patch("src.core.montage.concatenate_videoclips") as mock_concat:
        mock_final = MagicMock()
        mock_concat.return_value = mock_final
        mock_final.with_audio.return_value = mock_final

        output = montage_generator.generate(
            mock_audio_result, mock_video_results, "output.mp4"
        )
        assert output == "output.mp4"


@patch("src.core.montage.os.path.exists")
@patch("src.core.montage.VideoFileClip")
@patch("src.core.montage.AudioFileClip")
@patch("src.core.montage.random.shuffle")
def test_generate_skip_short_video(
    mock_shuffle, mock_audio_cls, mock_video_cls, mock_exists,
    montage_generator, mock_audio_result, mock_video_results
):
    mock_exists.return_value = True
    mock_audio_cls.return_value.duration = 4.0

    # Mock video clips: one short, one long
    long_clip = MagicMock()
    long_clip.duration = 10.0
    long_clip.subclipped.return_value = long_clip
    long_clip.resized.return_value = long_clip

    short_clip = MagicMock()
    short_clip.duration = 0.5  # Too short for 2s bar

    def video_cls_side_effect(path):
        if "mock_video_0" in path:
            return short_clip
        return long_clip

    mock_video_cls.side_effect = video_cls_side_effect

    # Setup specific video results to control processing order
    # shuffle does nothing
    mock_shuffle.side_effect = lambda x: x

    # We want mock_video_0 (short) to be processed.
    # The generator pops from the queue (end of list).
    # So we put mock_video_0 at the end.

    video_0 = next(v for v in mock_video_results if v.path == "mock_video_0.mp4")
    video_1 = next(v for v in mock_video_results if v.path == "mock_video_1.mp4")

    custom_results = [video_1, video_0] # video_0 is at the end, will be popped first

    with patch("src.core.montage.concatenate_videoclips") as mock_concat:
        mock_final = MagicMock()
        mock_concat.return_value = mock_final
        mock_final.with_audio.return_value = mock_final

        output = montage_generator.generate(
            mock_audio_result, custom_results, "output.mp4"
        )
        assert output == "output.mp4"
        # Ensure short clip was closed
        short_clip.close.assert_called()


@patch("src.core.montage.os.path.exists")
@patch("src.core.montage.VideoFileClip")
@patch("src.core.montage.AudioFileClip")
def test_generate_video_processing_error(
    mock_audio_cls, mock_video_cls, mock_exists,
    montage_generator, mock_audio_result, mock_video_results
):
    mock_exists.return_value = True
    mock_audio_cls.return_value.duration = 4.0

    # Raise exception for one video
    def video_cls_side_effect(path):
        if "mock_video_0" in path:
            raise ValueError("Corrupt file")
        mock_clip = MagicMock()
        mock_clip.duration = 10.0
        mock_clip.subclipped.return_value = mock_clip
        mock_clip.resized.return_value = mock_clip
        return mock_clip

    mock_video_cls.side_effect = video_cls_side_effect

    with patch("src.core.montage.concatenate_videoclips") as mock_concat:
        mock_final = MagicMock()
        mock_concat.return_value = mock_final
        mock_final.with_audio.return_value = mock_final

        output = montage_generator.generate(
            mock_audio_result, mock_video_results, "output.mp4"
        )
        assert output == "output.mp4"


@patch("src.core.montage.os.path.exists")
@patch("src.core.montage.VideoFileClip")
@patch("src.core.montage.AudioFileClip")
def test_generate_no_valid_clips_raises_error(
    mock_audio_cls, mock_video_cls, mock_exists,
    montage_generator, mock_audio_result, mock_video_results
):
    mock_exists.return_value = True
    mock_audio_cls.return_value.duration = 4.0

    # All videos fail
    mock_video_cls.side_effect = ValueError("All bad")

    with pytest.raises(RuntimeError, match="No valid video clips"):
        montage_generator.generate(
            mock_audio_result, mock_video_results, "output.mp4"
        )
