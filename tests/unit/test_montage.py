"""
Unit tests for MontageGenerator in src.core.montage.
Focus: High branch coverage, edge case handling, and resource cleanup.
"""
import pytest
from unittest.mock import MagicMock
from src.core.montage import MontageGenerator
from src.core.models import AudioAnalysisResult, VideoAnalysisResult


@pytest.fixture
def montage_generator():
    """Fixture for MontageGenerator instance."""
    return MontageGenerator()


@pytest.fixture
def mock_audio_result():
    """Fixture for a valid AudioAnalysisResult."""
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
    """Fixture for a list of valid VideoAnalysisResults."""
    return [
        VideoAnalysisResult(
            path=f"mock_video_{i}.mp4",
            intensity_score=0.5,
            duration=10.0,
            thumbnail_data=None
        ) for i in range(3)
    ]


@pytest.fixture
def mock_moviepy(mocker):
    """
    Mock all moviepy dependencies.
    Returns a dictionary of the mocks for assertion.
    """
    mock_audio_cls = mocker.patch("src.core.montage.AudioFileClip")
    mock_video_cls = mocker.patch("src.core.montage.VideoFileClip")
    mock_concat = mocker.patch("src.core.montage.concatenate_videoclips")

    # Setup default behaviors
    mock_audio_instance = MagicMock()
    mock_audio_instance.duration = 10.0
    mock_audio_cls.return_value = mock_audio_instance

    # Default video clip behavior
    mock_video_instance = MagicMock()
    mock_video_instance.duration = 10.0
    mock_subclip = MagicMock()
    mock_video_instance.subclipped.return_value = mock_subclip
    mock_resized = MagicMock()
    mock_subclip.resized.return_value = mock_resized
    mock_video_cls.return_value = mock_video_instance

    # Default concatenation behavior
    mock_final_video = MagicMock()
    mock_concat.return_value = mock_final_video
    mock_final_video.with_audio.return_value = mock_final_video

    return {
        "AudioFileClip": mock_audio_cls,
        "VideoFileClip": mock_video_cls,
        "concatenate_videoclips": mock_concat,
        "audio_instance": mock_audio_instance,
        "video_instance": mock_video_instance,
        "subclip": mock_subclip,
        "resized": mock_resized,
        "final_video": mock_final_video
    }


@pytest.fixture
def mock_os_path_exists(mocker):
    """Mock os.path.exists to always return True by default."""
    return mocker.patch("src.core.montage.os.path.exists", return_value=True)


@pytest.fixture
def mock_random_shuffle(mocker):
    """Mock random.shuffle to be deterministic (no-op)."""
    return mocker.patch("src.core.montage.random.shuffle")


class TestMontageGenerator:
    """Test suite for MontageGenerator."""

    def test_generate_success_standard(
        self,
        montage_generator,
        mock_audio_result,
        mock_video_results,
        mock_moviepy,
        mock_os_path_exists,
        mock_random_shuffle
    ):
        """
        Test standard successful generation.
        Verifies that clips are created, concatenated, and saved.
        """
        output_path = "output.mp4"
        result = montage_generator.generate(
            mock_audio_result, mock_video_results, output_path
        )

        assert result == output_path

        # Verify Audio loaded
        mock_moviepy["AudioFileClip"].assert_called_with(mock_audio_result.file_path)

        # Verify Video processing
        # With 120 BPM, bar duration is 2.0s. Total audio 10s.
        # Should generate 5 segments (10 / 2).
        assert mock_moviepy["VideoFileClip"].call_count == 5
        assert mock_moviepy["subclip"].resized.call_count == 5

        # Verify Concatenation
        mock_moviepy["concatenate_videoclips"].assert_called_once()
        args, _ = mock_moviepy["concatenate_videoclips"].call_args
        assert len(args[0]) == 5 # List of clips

        # Verify Output
        mock_moviepy["final_video"].write_videofile.assert_called_once_with(
            output_path,
            codec="libx264",
            audio_codec="aac",
            fps=24,
            logger=None,
            preset='ultrafast'
        )

        # Verify Cleanup
        assert mock_moviepy["audio_instance"].close.called
        assert mock_moviepy["final_video"].close.called
        assert mock_moviepy["resized"].close.called
        assert mock_moviepy["video_instance"].close.called


    @pytest.mark.parametrize("bpm", [0, -10])
    def test_generate_bpm_fallback(
        self,
        bpm,
        montage_generator,
        mock_audio_result,
        mock_video_results,
        mock_moviepy,
        mock_os_path_exists
    ):
        """Test that invalid BPM falls back to 120."""
        mock_audio_result.bpm = bpm

        montage_generator.generate(
            mock_audio_result, mock_video_results, "out.mp4"
        )

        # 120 BPM -> 2.0s bar duration. 10s audio -> 5 clips.
        # If it didn't fallback, it might divide by zero or have weird behavior
        assert mock_moviepy["VideoFileClip"].call_count == 5


    def test_generate_replenish_queue(
        self,
        montage_generator,
        mock_audio_result,
        mock_video_results,
        mock_moviepy,
        mock_os_path_exists
    ):
        """Test that video queue is replenished if not enough videos."""
        # Only 1 video available
        single_video = [mock_video_results[0]]

        # 120 BPM -> 5 segments needed
        montage_generator.generate(
            mock_audio_result, single_video, "out.mp4"
        )

        assert mock_moviepy["VideoFileClip"].call_count == 5
        # It should have reused the same video file 5 times


    def test_generate_skips_missing_video_files(
        self,
        montage_generator,
        mock_audio_result,
        mock_video_results,
        mock_moviepy,
        mock_os_path_exists
    ):
        """Test that missing video files are skipped without crashing."""
        # Make the first video 'missing'
        def side_effect(path):
            if path == mock_video_results[0].path:
                return False
            return True
        mock_os_path_exists.side_effect = side_effect

        montage_generator.generate(
            mock_audio_result, mock_video_results, "out.mp4"
        )

        # Should skip the first one and use others
        # We need 5 segments. Queue has 3 items. Item 0 is missing.
        # It will try item 0 -> fail. Try item 1 -> success.
        # It will loop until 5 segments are created.

        # Verify we didn't try to open the missing file
        call_args_list = mock_moviepy["VideoFileClip"].call_args_list
        paths_opened = [c[0][0] for c in call_args_list]
        assert mock_video_results[0].path not in paths_opened


    def test_generate_skips_short_videos(
        self,
        montage_generator,
        mock_audio_result,
        mock_video_results,
        mock_moviepy,
        mock_os_path_exists
    ):
        """Test that videos shorter than target duration are skipped."""
        target_duration = 2.0 # at 120 BPM

        # Setup specific video clips
        short_clip = MagicMock()
        short_clip.duration = 1.0 # Too short

        long_clip = MagicMock()
        long_clip.duration = 10.0
        long_sub = MagicMock()
        long_clip.subclipped.return_value = long_sub
        long_resized = MagicMock()
        long_sub.resized.return_value = long_resized

        def video_side_effect(path):
            if "mock_video_0" in path:
                return short_clip
            return long_clip

        mock_moviepy["VideoFileClip"].side_effect = video_side_effect

        montage_generator.generate(
            mock_audio_result, mock_video_results, "out.mp4"
        )

        # Verify short clip was opened and closed, but not processed
        assert short_clip.close.called
        assert not short_clip.subclipped.called

        # Verify long clip was processed
        assert long_clip.subclipped.called


    def test_generate_video_processing_exception(
        self,
        montage_generator,
        mock_audio_result,
        mock_video_results,
        mock_moviepy,
        mock_os_path_exists
    ):
        """Test that exceptions during video processing are handled gracefully."""
        # Make one video raise an exception on init
        def video_side_effect(path):
            if "mock_video_0" in path:
                raise Exception("Corrupt file")
            return mock_moviepy["video_instance"] # Default valid one

        mock_moviepy["VideoFileClip"].side_effect = video_side_effect

        montage_generator.generate(
            mock_audio_result, mock_video_results, "out.mp4"
        )

        # Should still succeed by using other videos
        assert mock_moviepy["concatenate_videoclips"].called


    @pytest.mark.parametrize("exception_type, match_msg, setup_func", [
        (
            FileNotFoundError,
            "Audio file not found",
            lambda mocks, audio, videos: mocks["os_path_exists"].__setattr__("return_value", False)
        ),
        (
            ValueError,
            "No video clips",
            lambda mocks, audio, videos: videos.clear()
        ),
        (
            RuntimeError,
            "No valid video clips",
            lambda mocks, audio, videos: mocks["os_path_exists"].__setattr__("side_effect", lambda p: p == audio.file_path)
        )
    ])
    def test_generate_errors(
        self,
        exception_type,
        match_msg,
        setup_func,
        montage_generator,
        mock_audio_result,
        mock_video_results,
        mock_moviepy,
        mock_os_path_exists
    ):
        """
        Parametrized test for failure scenarios.
        """
        mocks = {
            "os_path_exists": mock_os_path_exists,
            "moviepy": mock_moviepy
        }
        setup_func(mocks, mock_audio_result, mock_video_results)

        with pytest.raises(exception_type, match=match_msg):
            montage_generator.generate(
                mock_audio_result, mock_video_results, "out.mp4"
            )


    def test_generate_cleanup_on_concatenation_error(
        self,
        montage_generator,
        mock_audio_result,
        mock_video_results,
        mock_moviepy,
        mock_os_path_exists
    ):
        """Test that resources are cleaned up if concatenation fails."""
        mock_moviepy["concatenate_videoclips"].side_effect = RuntimeError("Concat failed")

        with pytest.raises(RuntimeError, match="Concat failed"):
            montage_generator.generate(
                mock_audio_result, mock_video_results, "out.mp4"
            )

        # Verify cleanup
        assert mock_moviepy["audio_instance"].close.called
        assert mock_moviepy["resized"].close.called
        assert mock_moviepy["video_instance"].close.called


    def test_cleanup_handles_close_exceptions(
        self,
        montage_generator,
        mock_audio_result,
        mock_video_results,
        mock_moviepy,
        mock_os_path_exists
    ):
        """Test that exceptions during cleanup (close()) are suppressed."""
        # Setup a scenario where close() raises an exception
        mock_moviepy["resized"].close.side_effect = Exception("Failed to close clip")
        mock_moviepy["video_instance"].close.side_effect = Exception("Failed to close source")

        # Run generation (should succeed despite cleanup errors)
        montage_generator.generate(
            mock_audio_result, mock_video_results, "out.mp4"
        )

        # Verify close was attempted
        assert mock_moviepy["resized"].close.called
        assert mock_moviepy["video_instance"].close.called
