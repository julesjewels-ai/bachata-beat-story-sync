import pytest
from unittest.mock import MagicMock, patch, call
from src.core.montage import MontageGenerator
from src.core.models import AudioAnalysisResult, VideoAnalysisResult
import os
import random

@pytest.fixture
def montage_generator():
    return MontageGenerator()

@pytest.fixture
def mock_audio_result():
    return AudioAnalysisResult(
        file_path="test_audio.wav",
        filename="test_audio.wav",
        bpm=120,
        duration=10.0,
        peaks=[0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5, 9.5],
        sections=["full_track"]
    )

@pytest.fixture
def mock_video_results():
    return [
        VideoAnalysisResult(
            path="test_video.mp4", intensity_score=0.5, duration=20.0, thumbnail_data=None
        )
    ]

# -- Edge Case Tests for _create_video_segment --

@pytest.mark.parametrize("file_exists, video_duration, exception_trigger, expected_result", [
    (False, 20.0, None, None),  # File not found -> None
    (True, 1.0, None, None),    # Video shorter than source duration (2.0) -> None
    (True, 20.0, Exception("Processing Error"), None), # Exception during processing -> None
])
def test_create_video_segment_edge_cases(
    file_exists, video_duration, exception_trigger, expected_result,
    montage_generator, mock_video_results
):
    video_data = mock_video_results[0]
    target_duration = 2.0 # Medium intensity -> speed factor 1.0 -> source duration 2.0

    with patch('os.path.exists', return_value=file_exists):
        with patch('src.core.montage.VideoFileClip') as mock_video_cls:
            mock_video = MagicMock()
            mock_video.duration = video_duration
            mock_video_cls.return_value = mock_video

            if exception_trigger:
                 # Trigger exception during subclipped call
                 mock_video.subclipped.side_effect = exception_trigger
            else:
                 mock_sub = MagicMock()
                 mock_processed = MagicMock()
                 mock_processed.duration = target_duration # Ensure duration is set
                 mock_video.subclipped.return_value = mock_sub
                 mock_sub.resized.return_value = mock_processed
                 mock_processed.with_effects.return_value = mock_processed

            result = montage_generator._create_video_segment(video_data, target_duration)
            assert result == expected_result

            if file_exists and video_duration < target_duration and not exception_trigger:
                # If short video, close should be called
                mock_video.close.assert_called()

# -- Edge Case Tests for _calculate_peak_percentiles --

def test_calculate_peak_percentiles_empty(montage_generator):
    """Test that empty peaks list returns (0.0, 0.0)"""
    p33, p66 = montage_generator._calculate_peak_percentiles(10.0, 2.0, [])
    assert p33 == 0.0
    assert p66 == 0.0

def test_calculate_peak_percentiles_zero_duration(montage_generator):
    """Test that zero duration results in no peak counts and returns (0.0, 0.0)"""
    p33, p66 = montage_generator._calculate_peak_percentiles(0.0, 2.0, [1.0, 2.0])
    assert p33 == 0.0
    assert p66 == 0.0

# -- Edge Case Tests for _get_next_video --

def test_get_next_video_empty_buckets(montage_generator):
    """Test that if all buckets are empty, returns None"""
    buckets = {'low': [], 'medium': [], 'high': []}
    result = montage_generator._get_next_video('medium', buckets)
    assert result is None

# -- Edge Case Tests for generate (Failures & Fallbacks) --

@pytest.mark.parametrize("scenario, mocks_setup, expected_exception", [
    (
        "invalid_bpm",
        lambda audio: setattr(audio, 'bpm', 0),
        None  # Should not raise exception, but log warning and continue
    ),
    (
        "processing_error",
        lambda audio: None, # Will be handled inside test body via side_effect
        Exception
    ),
])
def test_generate_edge_cases(
    scenario, mocks_setup, expected_exception,
    montage_generator, mock_audio_result, mock_video_results
):
    mocks_setup(mock_audio_result)

    with patch('src.core.montage.VideoFileClip') as mock_v_cls, \
         patch('src.core.montage.AudioFileClip') as mock_a_cls, \
         patch('src.core.montage.concatenate_videoclips') as mock_concat, \
         patch('os.path.exists') as mock_exists, \
         patch('src.core.montage.random.shuffle') as mock_shuffle: # Deterministic shuffle

        # Setup common mocks
        mock_audio = MagicMock()
        mock_audio.duration = 10.0
        mock_a_cls.return_value = mock_audio

        mock_video = MagicMock()
        mock_video.duration = 20.0
        mock_sub = MagicMock()
        mock_processed = MagicMock()
        # Set duration on processed clip to avoid TypeError if accessed
        mock_processed.duration = 2.0
        mock_video.subclipped.return_value = mock_sub
        mock_sub.resized.return_value = mock_processed
        mock_v_cls.return_value = mock_video

        mock_final = MagicMock()
        mock_concat.return_value = mock_final
        mock_final.with_audio.return_value = mock_final

        mock_exists.return_value = True

        if scenario == "invalid_bpm":
            # Test that it continues with fallback BPM
            # We need to ensure loop runs at least once
            res = montage_generator.generate(mock_audio_result, mock_video_results, "out.mp4")
            assert res == "out.mp4"

        elif scenario == "processing_error":
            # Simulate generic exception during processing
            mock_concat.side_effect = Exception("General Error")
            with pytest.raises(Exception, match="General Error"):
                 montage_generator.generate(mock_audio_result, mock_video_results, "out.mp4")

def test_generate_audio_file_not_found(
    montage_generator, mock_audio_result, mock_video_results
):
    """Test specifically for FileNotFoundError on missing audio file."""
    with patch('os.path.exists', return_value=False):
        with pytest.raises(FileNotFoundError, match="Audio file not found"):
            montage_generator.generate(mock_audio_result, mock_video_results, "out.mp4")

# -- Test Clips Empty (RuntimeError) --

def test_generate_no_clips_generated(
    montage_generator, mock_audio_result, mock_video_results
):
    """Test that RuntimeError is raised if no clips are generated after loop."""
    with patch('src.core.montage.VideoFileClip') as mock_v_cls, \
         patch('src.core.montage.AudioFileClip') as mock_a_cls, \
         patch('os.path.exists', return_value=True):

        mock_audio = MagicMock()
        mock_audio.duration = 10.0
        mock_a_cls.return_value = mock_audio

        # Make _create_video_segment always return None (e.g. all videos short/fail)
        # We can simulate this by mocking VideoFileClip to have short duration
        mock_video = MagicMock()
        mock_video.duration = 0.1 # Too short for any segment
        mock_v_cls.return_value = mock_video

        with pytest.raises(RuntimeError, match="No valid video clips could be generated"):
            montage_generator.generate(mock_audio_result, mock_video_results, "out.mp4")

# -- Test Cleanup Logic --

def test_cleanup_resources_handles_exceptions(montage_generator):
    """Test that cleanup handles exceptions during close() calls gracefully."""
    mock_audio = MagicMock()
    mock_audio.close.side_effect = Exception("Close error")

    mock_video = MagicMock()
    mock_video.close.side_effect = Exception("Close error")

    clips = [MagicMock()]
    clips[0].close.side_effect = Exception("Close error")

    source_clips = [MagicMock()]
    source_clips[0].close.side_effect = Exception("Close error")

    # Should not raise exception
    montage_generator._cleanup_resources(mock_audio, mock_video, clips, source_clips)

    # Verify close was called
    mock_audio.close.assert_called()
    mock_video.close.assert_called()
    clips[0].close.assert_called()
    source_clips[0].close.assert_called()

# -- Test attempts counter increment --
def test_generate_skips_short_videos(
    montage_generator, mock_audio_result, mock_video_results
):
    """
    Test that the loop skips segments when creation fails (returns None),
    incrementing attempts and advancing time eventually.
    """
    with patch('src.core.montage.VideoFileClip') as mock_v_cls, \
         patch('src.core.montage.AudioFileClip') as mock_a_cls, \
         patch('src.core.montage.concatenate_videoclips') as mock_concat, \
         patch('os.path.exists', return_value=True), \
         patch('src.core.montage.random.shuffle'):

        mock_audio = MagicMock()
        mock_audio.duration = 8.0 # Just enough for skip (4.0) + one segment (4.0)
        mock_a_cls.return_value = mock_audio

        # Video creation fails 11 times (triggering attempts > 10 check)
        # Then succeeds

        # We need to control _create_video_segment behavior.
        # Since it's a method on the class under test, we can mock the method itself or controlled dependencies.
        # Mocking the method is cleaner for testing logic flow here.

        with patch.object(montage_generator, '_create_video_segment') as mock_create:
            # 11 failures, then 1 success
            failures = [None] * 11
            success = (MagicMock(), MagicMock())
            mock_create.side_effect = failures + [success]

            mock_final = MagicMock()
            mock_concat.return_value = mock_final
            mock_final.with_audio.return_value = mock_final

            # Reduce max segments to avoid infinite loops in test if logic fails
            # But the code has safeguards.

            res = montage_generator.generate(mock_audio_result, mock_video_results, "out.mp4")

            assert res == "out.mp4"
            assert mock_create.call_count >= 12
            # Verify concat was called with the one successful clip
            args, _ = mock_concat.call_args
            assert len(args[0]) >= 1
