"""
Edge case tests for MontageGenerator.
"""
import pytest
from unittest.mock import MagicMock, patch, Mock
import os
import random
from typing import List, Optional, Type
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

@pytest.mark.parametrize("file_exists, video_duration, target_duration, processing_error, expected_result", [
    (False, 5.0, 2.0, None, None),  # File not found
    (True, 1.0, 2.0, None, None),   # Video too short
    (True, 5.0, 2.0, ValueError("Mock error"), None), # Processing error
    (True, 5.0, 2.0, None, "success") # Success
])
@patch("src.core.montage.os.path.exists")
@patch("src.core.montage.VideoFileClip")
def test_create_video_segment_edge_cases(
    mock_video_clip_cls: MagicMock,
    mock_exists: MagicMock,
    montage_generator: MontageGenerator,
    file_exists: bool,
    video_duration: float,
    target_duration: float,
    processing_error: Optional[Exception],
    expected_result: Optional[str]
) -> None:
    # Setup mocks
    mock_exists.return_value = file_exists

    mock_video_clip = MagicMock()
    mock_video_clip.duration = video_duration

    # Subclip returns a new mock
    mock_subclip = MagicMock()
    mock_video_clip.subclipped.return_value = mock_subclip

    # Resize returns a new mock
    mock_resized = MagicMock()
    mock_subclip.resized.return_value = mock_resized

    if processing_error:
        mock_video_clip_cls.side_effect = processing_error
    else:
        mock_video_clip_cls.return_value = mock_video_clip

    # Video data mock
    video_data = VideoAnalysisResult(
        path="test_video.mp4",
        intensity_score=0.8,
        duration=video_duration,
        thumbnail_data=None
    )

    # Execute
    result = montage_generator._create_video_segment(video_data, target_duration)

    # Verify
    if expected_result == "success":
        assert result is not None
        assert result == mock_resized
        mock_video_clip.subclipped.assert_called_once()
        mock_subclip.resized.assert_called_with(height=720)
    else:
        assert result is None
        if not file_exists:
            mock_video_clip_cls.assert_not_called()
        elif processing_error:
            mock_video_clip_cls.assert_called_once()

@pytest.mark.parametrize("bpm, all_segments_fail, expected_exception", [
    (-1.0, False, None),          # Fallback BPM
    (0.0, False, None),           # Fallback BPM
    (120.0, True, RuntimeError),  # All segments fail -> RuntimeError
    (120.0, False, None),         # Success
])
@patch("src.core.montage.os.path.exists")
@patch("src.core.montage.AudioFileClip")
@patch("src.core.montage.VideoFileClip") # Mock inside _create_video_segment
@patch("src.core.montage.concatenate_videoclips")
def test_generate_edge_cases(
    mock_concatenate: MagicMock,
    mock_video_clip_cls: MagicMock, # This mocks VideoFileClip constructor
    mock_audio_clip_cls: MagicMock,
    mock_exists: MagicMock,
    montage_generator: MontageGenerator,
    mock_audio_result: AudioAnalysisResult,
    mock_video_results: List[VideoAnalysisResult],
    bpm: float,
    all_segments_fail: bool,
    expected_exception: Optional[Type[Exception]]
) -> None:
    # Setup mocks
    mock_exists.return_value = True

    # Audio result setup
    mock_audio_result.bpm = bpm
    mock_audio_clip = MagicMock()
    mock_audio_clip.duration = 10.0
    mock_audio_clip_cls.return_value = mock_audio_clip

    # Video clip setup for _create_video_segment
    mock_video_clip = MagicMock()
    mock_video_clip.duration = 5.0 # Longer than any segment needed
    mock_subclip = MagicMock()
    mock_video_clip.subclipped.return_value = mock_subclip
    mock_resized = MagicMock()
    mock_subclip.resized.return_value = mock_resized

    if all_segments_fail:
        # Simulate failure in _create_video_segment by raising error in VideoFileClip
        mock_video_clip_cls.side_effect = ValueError("Processing failed")
    else:
        mock_video_clip_cls.return_value = mock_video_clip
        mock_video_clip_cls.side_effect = None # Ensure no side effect if success

    mock_final_video = MagicMock()
    mock_concatenate.return_value = mock_final_video
    mock_final_video.with_audio.return_value = mock_final_video

    if expected_exception:
        with pytest.raises(expected_exception):
            montage_generator.generate(
                mock_audio_result, mock_video_results, "output.mp4"
            )
    else:
        output = montage_generator.generate(
            mock_audio_result, mock_video_results, "output.mp4"
        )
        assert output == "output.mp4"
        # Verify fallback logic
        if bpm <= 0:
            # Check logs or implicit behavior (e.g., successful generation means fallback worked)
            pass

        # Verify cleanup
        mock_audio_clip.close.assert_called_once()
        mock_final_video.close.assert_called_once()
