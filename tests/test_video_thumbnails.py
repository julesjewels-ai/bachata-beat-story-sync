import unittest
from unittest.mock import MagicMock, patch
import cv2
import numpy as np
from src.core.video_analyzer import VideoAnalyzer

class TestVideoThumbnails(unittest.TestCase):
    def setUp(self):
        self.analyzer = VideoAnalyzer()

    @patch('cv2.resize')
    @patch('cv2.imencode')
    def test_extract_thumbnail_success(self, mock_imencode, mock_resize):
        # Setup Mock Capture
        mock_cap = MagicMock()

        # Frame count = 100
        mock_cap.get.side_effect = lambda prop: 100 if prop == cv2.CAP_PROP_FRAME_COUNT else 0

        # Read returns a dummy frame (100x200)
        # Height 100, Width 200
        dummy_frame = np.zeros((100, 200, 3), dtype=np.uint8)
        mock_cap.read.return_value = (True, dummy_frame)

        # Resize mock
        resized_frame = np.zeros((80, 160, 3), dtype=np.uint8)
        mock_resize.return_value = resized_frame

        # Imencode mock
        mock_buffer = MagicMock()
        mock_buffer.tobytes.return_value = b'fake_png_data'
        mock_imencode.return_value = (True, mock_buffer)

        # Call
        result = self.analyzer._extract_thumbnail(mock_cap)

        # Verify
        # Should seek to frame 50
        mock_cap.set.assert_called_with(cv2.CAP_PROP_POS_FRAMES, 50)

        # Should resize (200 width > 160 max)
        mock_resize.assert_called()

        # Should encode
        mock_imencode.assert_called_with(".png", resized_frame)

        # Should return bytes
        self.assertEqual(result, b'fake_png_data')

    def test_extract_thumbnail_empty(self):
        mock_cap = MagicMock()
        mock_cap.get.return_value = 0 # 0 frames

        result = self.analyzer._extract_thumbnail(mock_cap)
        self.assertIsNone(result)

    def test_extract_thumbnail_read_fail(self):
        mock_cap = MagicMock()
        mock_cap.get.return_value = 100
        mock_cap.read.return_value = (False, None)

        result = self.analyzer._extract_thumbnail(mock_cap)
        self.assertIsNone(result)
