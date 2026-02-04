import unittest
from unittest.mock import MagicMock, patch, call
import cv2
import numpy as np
from src.core.video_analyzer import VideoAnalyzer, VideoAnalysisInput, THUMBNAIL_MAX_WIDTH

class TestVideoThumbnails(unittest.TestCase):
    def setUp(self):
        self.analyzer = VideoAnalyzer()

    @patch('cv2.resize')
    @patch('cv2.imencode')
    @patch('cv2.VideoCapture')
    @patch('os.path.exists')
    def test_extract_thumbnail_success(self, mock_exists, mock_capture, mock_imencode, mock_resize):
        """Test successful thumbnail extraction and resizing."""
        mock_exists.return_value = True

        # Mock VideoCapture
        mock_cap_instance = MagicMock()
        mock_capture.return_value = mock_cap_instance
        mock_cap_instance.isOpened.return_value = True

        # Mock properties
        def get_prop(prop):
            if prop == cv2.CAP_PROP_FPS: return 30.0
            if prop == cv2.CAP_PROP_FRAME_COUNT: return 100
            return 0
        mock_cap_instance.get.side_effect = get_prop

        # Create frames
        large_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        small_frame = np.zeros((100, 100, 3), dtype=np.uint8)

        # Mock read side effects:
        # 1. Thumbnail read -> Success
        # 2. Intensity Loop Frame 1 -> Success
        # 3. Intensity Loop End -> Failure
        mock_cap_instance.read.side_effect = [
            (True, large_frame),
            (True, small_frame),
            (False, None)
        ]

        # Mock resize to return a smaller frame
        resized_frame = np.zeros((90, 160, 3), dtype=np.uint8)
        mock_resize.return_value = resized_frame

        # Mock imencode
        # Must return (retval, buffer) where buffer has .tobytes()
        mock_buffer = MagicMock()
        mock_buffer.tobytes.return_value = b'fake_jpg_bytes'
        mock_imencode.return_value = (True, mock_buffer)

        input_data = VideoAnalysisInput(file_path="test_video.mp4")
        result = self.analyzer.analyze(input_data)

        # Verify thumbnail
        self.assertEqual(result.thumbnail, b'fake_jpg_bytes')

        # Verify resize was called
        # large_frame is 1920 width. MAX is 160.
        # Should be resized.
        mock_resize.assert_called_once()

        # Verify seeking
        # Expected calls to set:
        # 1. Seek to 50 (middle)
        # 2. Reset to 0 (after thumbnail)
        # Note: _yield_frames doesn't seek, it just reads.

        # Check calls to set
        # We look for call(cv2.CAP_PROP_POS_FRAMES, 50) and call(cv2.CAP_PROP_POS_FRAMES, 0)
        self.assertIn(call(cv2.CAP_PROP_POS_FRAMES, 50), mock_cap_instance.set.mock_calls)
        self.assertIn(call(cv2.CAP_PROP_POS_FRAMES, 0), mock_cap_instance.set.mock_calls)

    @patch('cv2.VideoCapture')
    @patch('os.path.exists')
    def test_extract_thumbnail_failure(self, mock_exists, mock_capture):
        """Test behavior when thumbnail extraction fails."""
        mock_exists.return_value = True

        mock_cap_instance = MagicMock()
        mock_capture.return_value = mock_cap_instance
        mock_cap_instance.isOpened.return_value = True

        mock_cap_instance.get.side_effect = lambda p: 100 if p == cv2.CAP_PROP_FRAME_COUNT else 30.0

        # Mock read side effects:
        # 1. Thumbnail read -> Fail
        # 2. Intensity Loop Frame 1 -> Success (so analysis succeeds)
        # 3. Intensity Loop End -> Failure

        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_cap_instance.read.side_effect = [
            (False, None), # Thumbnail fail
            (True, frame), # Analysis frame
            (False, None)  # End analysis
        ]

        input_data = VideoAnalysisInput(file_path="test_video.mp4")
        result = self.analyzer.analyze(input_data)

        # Thumbnail should be None
        self.assertIsNone(result.thumbnail)

        # Intensity score should be calculated (non-zero ideally, but mock frame is black so 0 diff)
        # But we check that result exists
        self.assertIsNotNone(result)

        # Verify we still reset to 0 even if thumbnail failed
        self.assertIn(call(cv2.CAP_PROP_POS_FRAMES, 0), mock_cap_instance.set.mock_calls)
