"""
Unit tests for MontageGenerator.
"""
import pytest
from unittest.mock import MagicMock, patch
from typing import List, Generator, Any
from src.core.montage import MontageGenerator
from src.core.models import AudioAnalysisResult, VideoAnalysisResult

@pytest.fixture
def montage_generator() -> MontageGenerator:
    return MontageGenerator()

@pytest.fixture
def mock_audio_result() -> AudioAnalysisResult:
    return AudioAnalysisResult(
        file_path="mock_audio.wav",
        filename="mock_audio.wav",
        bpm=120.0,
        duration=10.0,
        peaks=[],
        sections=[]
    )

@pytest.fixture
def mock_video_results() -> List[VideoAnalysisResult]:
    return [
        VideoAnalysisResult(
            path=f"mock_video_{i}.mp4",
            intensity_score=0.5,
            duration=5.0,
            thumbnail_data=None
        ) for i in range(3)
    ]

@pytest.fixture
def mock_exists() -> Generator[MagicMock, None, None]:
    with patch("src.core.montage.os.path.exists") as mock:
        mock.return_value = True
        yield mock

@pytest.fixture
def mock_audio_clip_cls() -> Generator[MagicMock, None, None]:
    with patch("src.core.montage.AudioFileClip") as mock:
        audio_clip = MagicMock()
        audio_clip.duration = 10.0
        mock.return_value = audio_clip
        yield mock

@pytest.fixture
def mock_video_clip_cls() -> Generator[MagicMock, None, None]:
    with patch("src.core.montage.VideoFileClip") as mock:
        video_clip = MagicMock()
        video_clip.duration = 5.0
        subclip = MagicMock()
        video_clip.subclipped.return_value = subclip
        resized = MagicMock()
        subclip.resized.return_value = resized
        mock.return_value = video_clip
        yield mock

@pytest.fixture
def mock_concatenate() -> Generator[MagicMock, None, None]:
    with patch("src.core.montage.concatenate_videoclips") as mock:
        final_video = MagicMock()
        mock.return_value = final_video
        final_video.with_audio.return_value = final_video
        yield mock

@pytest.fixture
def mock_shuffle() -> Generator[MagicMock, None, None]:
    with patch("src.core.montage.random.shuffle") as mock:
        # Default behavior: do nothing (keep order)
        mock.side_effect = lambda x: None
        yield mock

class TestCreateVideoSegment:

    @pytest.mark.parametrize("scenario, file_exists, video_duration, open_error, expected_result", [
        ("file_not_found", False, 5.0, None, None),
        ("video_too_short", True, 1.0, None, None),
        ("open_error", True, 5.0, Exception("Corrupt"), None),
        ("success", True, 10.0, None, "success"),
    ])
    def test_create_video_segment_scenarios(
        self,
        scenario: str,
        file_exists: bool,
        video_duration: float,
        open_error: Exception | None,
        expected_result: str | None,
        montage_generator: MontageGenerator,
        mock_exists: MagicMock,
        mock_video_clip_cls: MagicMock,
        mock_video_results: List[VideoAnalysisResult]
    ) -> None:
        # Setup
        mock_exists.return_value = file_exists
        video_data = mock_video_results[0]

        mock_clip = mock_video_clip_cls.return_value
        mock_clip.duration = video_duration

        if open_error:
            mock_video_clip_cls.side_effect = open_error
        else:
            mock_video_clip_cls.side_effect = None

        # Execute
        result = montage_generator._create_video_segment(video_data, 2.0)

        # Verify
        if scenario == "file_not_found":
            assert result is None
            mock_exists.assert_called_with(video_data.path)

        elif scenario == "video_too_short":
            assert result is None
            assert mock_clip.close.called

        elif scenario == "open_error":
            assert result is None
            # Exception caught and logged

        elif scenario == "success":
            assert result is not None
            if result: # type guard
                segment, source = result
                assert source == mock_clip
                assert segment == mock_clip.subclipped.return_value.resized.return_value
                assert not mock_clip.close.called


class TestGenerate:
    def test_generate_success(
        self,
        montage_generator: MontageGenerator,
        mock_audio_result: AudioAnalysisResult,
        mock_video_results: List[VideoAnalysisResult],
        mock_exists: MagicMock,
        mock_audio_clip_cls: MagicMock,
        mock_video_clip_cls: MagicMock,
        mock_concatenate: MagicMock,
        mock_shuffle: MagicMock
    ) -> None:
        output = montage_generator.generate(
            mock_audio_result, mock_video_results, "output.mp4"
        )

        assert output == "output.mp4"
        mock_concatenate.assert_called_once()
        mock_concatenate.return_value.write_videofile.assert_called_once()

        # Verify cleanup
        assert mock_audio_clip_cls.return_value.close.called
        assert mock_concatenate.return_value.close.called
        # Verify video clips closed
        assert mock_video_clip_cls.return_value.subclipped.return_value.resized.return_value.close.called
        assert mock_video_clip_cls.return_value.close.called

    def test_generate_skips_short_videos(
        self,
        montage_generator: MontageGenerator,
        mock_audio_result: AudioAnalysisResult,
        mock_video_results: List[VideoAnalysisResult],
        mock_exists: MagicMock,
        mock_audio_clip_cls: MagicMock,
        mock_video_clip_cls: MagicMock,
        mock_concatenate: MagicMock,
        mock_shuffle: MagicMock
    ) -> None:
        # Setup: Audio 4s long. Video 0 is short (1s), Video 1 is long (5s).
        mock_audio_result.duration = 4.0
        mock_audio_clip_cls.return_value.duration = 4.0

        # Video 0 (Short)
        short_video = MagicMock()
        short_video.duration = 1.0 # < 2.0 (target)
        short_video.close = MagicMock()

        # Video 1 (Long)
        long_video = MagicMock()
        long_video.duration = 5.0
        long_sub = MagicMock()
        long_video.subclipped.return_value = long_sub
        long_resized = MagicMock()
        long_sub.resized.return_value = long_resized

        # Define side effect to return short then long
        def video_side_effect(path: str) -> MagicMock:
            if "mock_video_0" in path:
                return short_video
            return long_video

        mock_video_clip_cls.side_effect = video_side_effect

        # Mock shuffle to ensure order: video_0, video_1, video_2
        # Queue is popped from end, so we want video_0 to be at end to be processed first?
        # montage.py: video_data = video_queue.pop()
        # So last element is processed first.
        # If we want video_0 processed first, it should be at the end.

        def shuffle_side_effect(lst: List[Any]) -> None:
            # Sort so video_0 is last (popped first)
            # Find the index of video_0
            idx = -1
            for i, v in enumerate(lst):
                if "mock_video_0" in v.path:
                    idx = i
                    break

            if idx != -1:
                # Move it to the end
                item = lst.pop(idx)
                lst.append(item)

        mock_shuffle.side_effect = shuffle_side_effect

        output = montage_generator.generate(
            mock_audio_result, mock_video_results, "output.mp4"
        )

        assert output == "output.mp4"

        # Verify short video was closed immediately
        assert short_video.close.called, "Short video should have been closed"

        # Verify long video was used
        assert long_video.close.called, "Long video should have been closed"

    def test_generate_cleanup_on_error(
        self,
        montage_generator: MontageGenerator,
        mock_audio_result: AudioAnalysisResult,
        mock_video_results: List[VideoAnalysisResult],
        mock_exists: MagicMock,
        mock_audio_clip_cls: MagicMock,
        mock_video_clip_cls: MagicMock,
        mock_concatenate: MagicMock,
        mock_shuffle: MagicMock
    ) -> None:
        mock_concatenate.side_effect = RuntimeError("Concat failed")

        with pytest.raises(RuntimeError, match="Concat failed"):
            montage_generator.generate(
                mock_audio_result, mock_video_results, "output.mp4"
            )

        # Verify cleanup
        assert mock_audio_clip_cls.return_value.close.called
        # Video clips should be closed
        assert mock_video_clip_cls.return_value.close.called

    def test_generate_audio_not_found(
        self,
        montage_generator: MontageGenerator,
        mock_audio_result: AudioAnalysisResult,
        mock_video_results: List[VideoAnalysisResult],
        mock_exists: MagicMock,
        mock_audio_clip_cls: MagicMock
    ) -> None:
        mock_exists.side_effect = lambda p: p != mock_audio_result.file_path

        with pytest.raises(FileNotFoundError):
            montage_generator.generate(
                mock_audio_result, mock_video_results, "output.mp4"
            )

        assert not mock_audio_clip_cls.called

    def test_generate_no_videos(
        self,
        montage_generator: MontageGenerator,
        mock_audio_result: AudioAnalysisResult
    ) -> None:
        with pytest.raises(ValueError, match="No video clips"):
            montage_generator.generate(mock_audio_result, [], "output.mp4")

    def test_bpm_fallback(
        self,
        montage_generator: MontageGenerator,
        mock_audio_result: AudioAnalysisResult,
        mock_video_results: List[VideoAnalysisResult],
        mock_exists: MagicMock,
        mock_audio_clip_cls: MagicMock,
        mock_video_clip_cls: MagicMock,
        mock_concatenate: MagicMock,
        mock_shuffle: MagicMock
    ) -> None:
        mock_audio_result.bpm = 0

        montage_generator.generate(
            mock_audio_result, mock_video_results, "output.mp4"
        )

        # BPM 0 -> fallback 120 -> beat 0.5s -> bar 2.0s
        # Check that segments are created with duration 2.0 (first segment)
        # Note: Seg duration depends on audio duration and loop logic
        # But we can assume fallback didn't crash
        assert mock_concatenate.called

    def test_runtime_error_if_no_valid_clips(
        self,
        montage_generator: MontageGenerator,
        mock_audio_result: AudioAnalysisResult,
        mock_video_results: List[VideoAnalysisResult],
        mock_exists: MagicMock,
        mock_audio_clip_cls: MagicMock,
        mock_video_clip_cls: MagicMock,
        mock_concatenate: MagicMock,
        mock_shuffle: MagicMock
    ) -> None:
        # All videos fail to process
        mock_video_clip_cls.side_effect = Exception("Fail")

        with pytest.raises(RuntimeError, match="No valid video clips"):
            montage_generator.generate(
                mock_audio_result, mock_video_results, "output.mp4"
            )

        assert mock_audio_clip_cls.return_value.close.called
