"""
Unit tests for the VideoAnalyzer module.
"""
import pytest
from unittest.mock import patch, MagicMock
import numpy as np
from pydantic import ValidationError
from src.core.video_analyzer import VideoAnalyzer, VideoAnalysisInput


@pytest.fixture
def analyzer():
    return VideoAnalyzer()


@patch('os.path.exists', return_value=True)
@patch('cv2.VideoCapture')
def test_analyze_video(mock_video_capture, mock_exists, analyzer):
    """Tests the video analysis logic with a mock video."""
    # Mock the video capture object
    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = True
    # FPS, Frame Count, Frame Count (again), Intensity FPS
    mock_cap.get.side_effect = [30.0, 300, 300, 3.0]

    # Generate enough frames to trigger motion calculation with skip_rate=10
    # We need at least frame 0 and frame 10 (11 frames) to get one motion vector.
    frames = [(True, np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)) for _ in range(12)]
    frames.append((False, None))
    mock_cap.read.side_effect = frames
    mock_video_capture.return_value = mock_cap

    input_data = VideoAnalysisInput(file_path='dummy_path.mp4')
    result = analyzer.analyze(input_data)

    assert result.path == 'dummy_path.mp4'
    assert result.duration == pytest.approx(10.0)
    assert result.intensity_score > 0.0


@patch('os.path.exists', return_value=False)
def test_analyze_file_not_found(mock_exists):
    """Tests that a ValidationError is raised when the video file does not exist."""
    with pytest.raises(ValidationError, match="File not found"):
        VideoAnalysisInput(file_path='non_existent_file.mp4')
