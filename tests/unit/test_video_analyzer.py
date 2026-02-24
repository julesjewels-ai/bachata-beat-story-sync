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

    # Expected calls to cap.get():
    # 1. FPS (30.0) - _validate_video_properties
    # 2. Frame Count (300) - _validate_video_properties
    # 3. Width (1920) - analyze
    # 4. Height (1080) - analyze
    # 5. Frame Count (300) - _get_middle_frame
    # 6. FPS (30.0) - _calculate_intensity
    mock_cap.get.side_effect = [30.0, 300, 1920, 1080, 300, 30.0]

    # Mock frames: 1 for thumbnail, 1 for intensity, then end
    frame1 = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
    frame2 = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)

    mock_cap.read.side_effect = [
        (True, frame1), # _get_middle_frame
        (True, frame2), # _calculate_intensity (first frame)
        (False, None)   # _calculate_intensity (end)
    ]
    mock_video_capture.return_value = mock_cap

    input_data = VideoAnalysisInput(file_path='dummy_path.mp4')
    result = analyzer.analyze(input_data)

    assert result.path == 'dummy_path.mp4'
    assert result.duration == pytest.approx(10.0)
    assert result.intensity_score >= 0.0 # Intensity might be 0 if only 1 frame or no motion


@patch('os.path.exists', return_value=False)
def test_analyze_file_not_found(mock_exists):
    """Tests that a ValidationError is raised when the video file does not exist."""
    with pytest.raises(ValidationError, match="File not found"):
        VideoAnalysisInput(file_path='non_existent_file.mp4')
