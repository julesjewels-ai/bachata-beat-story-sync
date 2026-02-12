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

    # Verify cleanup happens even in success
    assert mock_audio_clip.close.called
    assert mock_final_video.close.called
    assert mock_resized.close.called
    assert mock_video_clip.close.called


@patch("src.core.montage.os.path.exists")
@patch("src.core.montage.AudioFileClip")
@patch("src.core.montage.VideoFileClip")
@patch("src.core.montage.concatenate_videoclips")
def test_generate_cleanup_on_error(
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
    mock_subclip = MagicMock()
    mock_video_clip.subclipped.return_value = mock_subclip
    mock_resized = MagicMock()
    mock_subclip.resized.return_value = mock_resized
    mock_video_clip_cls.return_value = mock_video_clip

    # Simulate error during concatenation
    mock_concatenate.side_effect = RuntimeError("Concatenation failed")

    # Run
    with pytest.raises(RuntimeError, match="Concatenation failed"):
        montage_generator.generate(
            mock_audio_result, mock_video_results, "output.mp4"
        )

    # Verify cleanup
    assert mock_audio_clip.close.called
    # final_video won't be created, so can't check its close, but clips should be closed
    assert mock_resized.close.called
    assert mock_video_clip.close.called


@patch("src.core.montage.random.shuffle")
@patch("src.core.montage.os.path.exists")
@patch("src.core.montage.AudioFileClip")
@patch("src.core.montage.VideoFileClip")
@patch("src.core.montage.concatenate_videoclips")
def test_generate_skips_short_videos(
    mock_concatenate,
    mock_video_clip_cls,
    mock_audio_clip_cls,
    mock_exists,
    mock_shuffle,
    montage_generator,
    mock_audio_result,
    mock_video_results
):
    # Setup mocks
    mock_exists.return_value = True

    # Ensure deterministic shuffle: put video 0 at the end so it's popped first
    def side_effect_shuffle(x):
        # Sort reverse by path: [video_2, video_1, video_0]
        # pop() will give video_0
        x.sort(key=lambda v: v.path, reverse=True)

    mock_shuffle.side_effect = side_effect_shuffle

    mock_audio_clip = MagicMock()
    mock_audio_clip.duration = 4.0 # short audio
    mock_audio_clip_cls.return_value = mock_audio_clip

    # One short video, one long
    mock_short_video = MagicMock()
    mock_short_video.duration = 1.0 # shorter than bar duration (2.0s at 120BPM)

    mock_long_video = MagicMock()
    mock_long_video.duration = 5.0
    mock_subclip = MagicMock()
    mock_long_video.subclipped.return_value = mock_subclip
    mock_resized = MagicMock()
    mock_subclip.resized.return_value = mock_resized

    # Side effect for VideoFileClip
    def video_clip_side_effect(path):
        if "mock_video_0" in path:
            return mock_short_video
        return mock_long_video

    mock_video_clip_cls.side_effect = video_clip_side_effect

    mock_final_video = MagicMock()
    mock_concatenate.return_value = mock_final_video
    mock_final_video.with_audio.return_value = mock_final_video

    # Run
    # Provide multiple videos so it can pick the long one after skipping the short one
    output = montage_generator.generate(
        mock_audio_result, mock_video_results, "output.mp4"
    )

    assert output == "output.mp4"

    # Verify short video was closed immediately
    assert mock_short_video.close.called
    # Verify long video was processed
    assert mock_long_video.subclipped.called
    assert mock_resized.close.called
    assert mock_long_video.close.called


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


@patch("src.core.montage.random.shuffle")
@patch("src.core.montage.os.path.exists")
@patch("src.core.montage.AudioFileClip")
@patch("src.core.montage.VideoFileClip")
@patch("src.core.montage.concatenate_videoclips")
@pytest.mark.parametrize("scenario", [
    {
        "name": "invalid_bpm",
        "bpm": 0.0,
        "exists_side_effect": lambda p: True,
        "video_side_effect": None,
        "expected_error": None
    },
    {
        "name": "video_not_found",
        "bpm": 120.0,
        "exists_side_effect": lambda p: not p.endswith(".mp4"),
        "video_side_effect": None,
        "expected_error": RuntimeError
    },
    {
        "name": "video_processing_error",
        "bpm": 120.0,
        "exists_side_effect": lambda p: True,
        "video_side_effect": Exception("Corrupt"),
        "expected_error": RuntimeError
    },
    {
        "name": "cleanup_exception",
        "bpm": 120.0,
        "exists_side_effect": lambda p: True,
        "video_side_effect": None,
        "cleanup_side_effect": Exception("Cleanup failed"),
        "expected_error": None
    },
])
def test_generate_edge_cases(
    mock_concatenate,
    mock_video_clip_cls,
    mock_audio_clip_cls,
    mock_exists,
    mock_shuffle,
    scenario,
    montage_generator,
    mock_audio_result,
    mock_video_results
):
    # Unpack scenario
    mock_audio_result.bpm = scenario["bpm"]
    mock_exists.side_effect = scenario["exists_side_effect"]

    if isinstance(scenario.get("video_side_effect"), Exception):
        mock_video_clip_cls.side_effect = scenario["video_side_effect"]
    else:
        # Normal behavior
        mock_video_clip = MagicMock()
        mock_video_clip.duration = 5.0
        mock_subclip = MagicMock()
        mock_video_clip.subclipped.return_value = mock_subclip
        mock_resized = MagicMock()
        mock_subclip.resized.return_value = mock_resized
        mock_video_clip_cls.return_value = mock_video_clip

        if scenario.get("cleanup_side_effect"):
             mock_video_clip.close.side_effect = scenario["cleanup_side_effect"]
             mock_resized.close.side_effect = scenario["cleanup_side_effect"]

    mock_audio_clip = MagicMock()
    mock_audio_clip.duration = 10.0
    mock_audio_clip_cls.return_value = mock_audio_clip

    mock_final_video = MagicMock()
    mock_concatenate.return_value = mock_final_video
    mock_final_video.with_audio.return_value = mock_final_video

    # Shuffle side effect to be deterministic (no-op or sort)
    # Just sort to be consistent
    mock_shuffle.side_effect = lambda x: x.sort(key=lambda v: v.path)

    if scenario["expected_error"]:
        with pytest.raises(scenario["expected_error"]):
            montage_generator.generate(
                mock_audio_result, mock_video_results, "output.mp4"
            )
    else:
        output = montage_generator.generate(
            mock_audio_result, mock_video_results, "output.mp4"
        )
        assert output == "output.mp4"
