import cv2
import numpy as np
from unittest.mock import MagicMock, patch
from src.core.video_analyzer import VideoAnalyzer


def test_extract_thumbnail_success():
    """Test that a thumbnail is extracted correctly."""
    analyzer = VideoAnalyzer()
    mock_cap = MagicMock(spec=cv2.VideoCapture)

    # Mock video properties
    mock_cap.get.side_effect = (
        lambda prop: 100 if prop == cv2.CAP_PROP_FRAME_COUNT else 0
    )

    # Mock frame reading
    # Create a dummy frame (height, width, channels)
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    mock_cap.read.return_value = (True, dummy_frame)

    # Mock imencode
    # Need to patch cv2.imencode because it's a static function
    with patch("cv2.imencode") as mock_imencode:
        # cv2.imencode returns (retval, buf)
        mock_imencode.return_value = (
            True, MagicMock(tobytes=lambda: b"fake_jpeg_data")
        )

        thumbnail = analyzer._extract_thumbnail(mock_cap)

        assert thumbnail == b"fake_jpeg_data"
        # Verify seek to middle
        mock_cap.set.assert_called_with(cv2.CAP_PROP_POS_FRAMES, 50)

        # Verify resize called implicitly by checking imencode call args
        args, _ = mock_imencode.call_args
        extension = args[0]
        encoded_frame = args[1]

        assert extension == ".jpg"
        assert encoded_frame.shape[1] == 160  # Width


def test_extract_thumbnail_failure_read():
    """Test behavior when frame read fails."""
    analyzer = VideoAnalyzer()
    mock_cap = MagicMock(spec=cv2.VideoCapture)
    mock_cap.get.return_value = 100
    mock_cap.read.return_value = (False, None)

    thumbnail = analyzer._extract_thumbnail(mock_cap)
    assert thumbnail is None


def test_extract_thumbnail_failure_encode():
    """Test behavior when encoding fails."""
    analyzer = VideoAnalyzer()
    mock_cap = MagicMock(spec=cv2.VideoCapture)
    mock_cap.get.return_value = 100
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    mock_cap.read.return_value = (True, dummy_frame)

    with patch("cv2.imencode") as mock_imencode:
        mock_imencode.return_value = (False, None)
        thumbnail = analyzer._extract_thumbnail(mock_cap)
        assert thumbnail is None
