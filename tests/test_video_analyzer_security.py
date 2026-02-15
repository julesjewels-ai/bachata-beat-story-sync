"""
Tests for video analyzer security validations.
"""
import pytest
from unittest.mock import MagicMock, patch
import cv2
from pydantic import ValidationError
from src.core.video_analyzer import VideoAnalyzer, VideoAnalysisInput


@pytest.fixture
def analyzer():
    return VideoAnalyzer()


@patch('cv2.VideoCapture')
@patch('os.path.exists')
def test_dos_vulnerability_large_video(mock_exists, mock_capture, analyzer):
    """
    Test that the analyzer REJECTS a video that is too large/long.
    """
    mock_exists.return_value = True

    # Mock a video with huge duration/frames
    mock_cap_instance = MagicMock()
    mock_capture.return_value = mock_cap_instance
    mock_cap_instance.isOpened.return_value = True

    # Huge frame count: 1 Billion frames
    mock_cap_instance.get.side_effect = lambda prop: {
        cv2.CAP_PROP_FPS: 30.0,
        cv2.CAP_PROP_FRAME_COUNT: 10**9
    }.get(prop, 0)

    # We expect a ValueError (from our explicit check)
    with pytest.raises(ValueError, match="exceeds maximum allowed frames"):
        input_data = VideoAnalysisInput(file_path="fake_huge_video.mp4")
        analyzer.analyze(input_data)


@patch('os.path.exists')
def test_invalid_extension(mock_exists):
    """
    Test that files with invalid extensions are rejected by Pydantic model.
    """
    mock_exists.return_value = True
    with pytest.raises(ValidationError, match="Unsupported extension"):
        VideoAnalysisInput(file_path="dangerous_script.py")


@patch('os.path.exists')
def test_path_traversal(mock_exists):
    """Test that paths with traversal characters are rejected."""
    mock_exists.return_value = True

    with pytest.raises(ValidationError, match="Path traversal attempt detected"):
        VideoAnalysisInput(file_path="../secret.mp4")
