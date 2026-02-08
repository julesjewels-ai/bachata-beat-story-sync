"""
Edge case tests for MontageGenerator.
"""
import pytest
from unittest.mock import MagicMock, patch, ANY
from src.core.montage import MontageGenerator
from src.core.models import AudioAnalysisResult, VideoAnalysisResult

@pytest.fixture
def montage_generator():
    return MontageGenerator()

@pytest.fixture
def audio_result():
    return AudioAnalysisResult(
        file_path="mock_audio.wav",
        filename="mock_audio.wav",
        bpm=60.0,  # 1 sec per beat, 4 sec per bar
        duration=10.0,
        peaks=[],
        sections=[]
    )

@pytest.fixture
def video_results():
    return [
        VideoAnalysisResult(
            path=f"mock_video_{i}.mp4",
            intensity_score=0.5,
            duration=10.0,
            thumbnail_data=None
        ) for i in range(2)
    ]

@patch("src.core.montage.os.path.exists")
@patch("src.core.montage.AudioFileClip")
@patch("src.core.montage.VideoFileClip")
@patch("src.core.montage.concatenate_videoclips")
def test_montage_bpm_fallback(
    mock_concat, mock_video_cls, mock_audio_cls, mock_exists,
    montage_generator, audio_result, video_results, caplog
):
    """Test that invalid BPM triggers fallback to 120."""
    audio_result.bpm = 0.0
    mock_exists.return_value = True

    mock_audio = MagicMock()
    mock_audio.duration = 4.0
    mock_audio_cls.return_value = mock_audio

    mock_video = MagicMock()
    mock_video.duration = 10.0
    mock_video_cls.return_value = mock_video

    # Mock shuffle to be deterministic
    with patch("src.core.montage.random.shuffle"):
        montage_generator.generate(audio_result, video_results, "out.mp4")

    assert "Invalid BPM detected, using fallback 120 BPM" in caplog.text

@patch("src.core.montage.random.shuffle")
@patch("src.core.montage.os.path.exists")
@patch("src.core.montage.AudioFileClip")
@patch("src.core.montage.VideoFileClip")
@patch("src.core.montage.concatenate_videoclips")
@pytest.mark.parametrize("scenario", [
    "video_not_found",
    "video_too_short",
    "processing_error"
])
def test_montage_single_video_failure(
    mock_concat, mock_video_cls, mock_audio_cls, mock_exists, mock_shuffle,
    montage_generator, audio_result, video_results, caplog, scenario
):
    """
    Test that individual video failures (file missing, too short, exception)
    are handled gracefully (skipped) and do not crash the generation.
    """
    # Setup: 4.0 seconds duration = 1 bar (at 60 BPM). Need 1 segment.
    audio_result.bpm = 60.0
    mock_audio = MagicMock()
    mock_audio.duration = 4.0
    mock_audio_cls.return_value = mock_audio

    # video_results has 2 items. pop() takes from end.
    # v0, v1. pop -> v1.
    # We want the first one popped (v1) to fail, and v0 to succeed.

    # Default behavior for exists
    mock_exists.return_value = True

    # Prepare video clips
    mock_v1_fail = MagicMock()
    mock_v1_fail.duration = 10.0

    mock_v0_success = MagicMock()
    mock_v0_success.duration = 10.0

    # Configure scenarios
    if scenario == "video_not_found":
        # v1 (mock_video_1.mp4) not found
        def exists_side_effect(path):
            if "mock_video_1.mp4" in path:
                return False
            return True
        mock_exists.side_effect = exists_side_effect
        # VideoFileClip only called for v0
        mock_video_cls.side_effect = [mock_v0_success]

    elif scenario == "video_too_short":
        # v1 is too short (< 4.0)
        mock_v1_fail.duration = 1.0
        mock_video_cls.side_effect = [mock_v1_fail, mock_v0_success]

    elif scenario == "processing_error":
        # v1 raises exception
        mock_video_cls.side_effect = [Exception("Corrupt file"), mock_v0_success]

    # Run
    montage_generator.generate(audio_result, video_results, "out.mp4")

    # Verify
    if scenario == "video_not_found":
        assert "Video file not found" in caplog.text
        # Should have tried to process valid one
        assert mock_concat.call_count == 1

    elif scenario == "processing_error":
        assert "Error processing clip" in caplog.text
        assert mock_concat.call_count == 1

    elif scenario == "video_too_short":
        # No log for this specific case, but verification that we skipped it
        # and used the next one is implicit if mock_concat is called.
        assert mock_concat.call_count == 1
        # Ensure v1 was closed
        mock_v1_fail.close.assert_called()

@patch("src.core.montage.random.shuffle")
@patch("src.core.montage.os.path.exists")
@patch("src.core.montage.AudioFileClip")
@patch("src.core.montage.VideoFileClip")
def test_montage_all_videos_fail(
    mock_video_cls, mock_audio_cls, mock_exists, mock_shuffle,
    montage_generator, audio_result, video_results
):
    """Test that RuntimeError is raised if no clips can be generated."""
    mock_exists.return_value = True
    mock_audio = MagicMock()
    mock_audio.duration = 10.0
    mock_audio_cls.return_value = mock_audio

    # All videos raise exception
    mock_video_cls.side_effect = Exception("Fail")

    with pytest.raises(RuntimeError, match="No valid video clips"):
        montage_generator.generate(audio_result, video_results, "out.mp4")

@patch("src.core.montage.random.shuffle")
@patch("src.core.montage.os.path.exists")
@patch("src.core.montage.AudioFileClip")
@patch("src.core.montage.VideoFileClip")
@patch("src.core.montage.concatenate_videoclips")
def test_montage_queue_refill(
    mock_concat, mock_video_cls, mock_audio_cls, mock_exists, mock_shuffle,
    montage_generator, audio_result, video_results
):
    """Test that the video queue refills when empty."""
    # We have 2 videos.
    # We want to generate 3 segments.
    # Queue will empty after 2, should refill for 3rd.

    audio_result.bpm = 60.0
    mock_audio = MagicMock()
    mock_audio.duration = 12.0 # 3 segments (4s each)
    mock_audio_cls.return_value = mock_audio

    mock_exists.return_value = True

    mock_video = MagicMock()
    mock_video.duration = 10.0
    mock_video_cls.return_value = mock_video

    montage_generator.generate(audio_result, video_results, "out.mp4")

    # Verify shuffle called at least twice (initial + refill)
    # Actually initial + refill.
    assert mock_shuffle.call_count >= 2
