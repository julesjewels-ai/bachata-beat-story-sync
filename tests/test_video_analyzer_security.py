import unittest
from unittest.mock import MagicMock, patch
import cv2
from pydantic import ValidationError
from src.core.video_analyzer import VideoAnalyzer
from src.core.models import VideoAnalysisInput

class TestVideoAnalyzerSecurity(unittest.TestCase):
    def setUp(self):
        self.analyzer = VideoAnalyzer()

    @patch('cv2.VideoCapture')
    @patch('os.path.exists')
    def test_dos_vulnerability_large_video(self, mock_exists, mock_capture):
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
        with self.assertRaises(ValueError) as context:
             input_data = VideoAnalysisInput(file_path="fake_huge_video.mp4")
             self.analyzer.analyze(input_data)

        self.assertIn("exceeds maximum allowed frames", str(context.exception))

    @patch('os.path.exists')
    def test_invalid_extension(self, mock_exists):
        """Test that files with invalid extensions are rejected by Pydantic model"""
        mock_exists.return_value = True
        with self.assertRaises(ValidationError) as context:
            VideoAnalysisInput(file_path="dangerous_script.py")

        # Check that the error message mentions the extension issue
        # Note: Pydantic errors are wrapped, so we check the string representation
        self.assertIn("Unsupported extension", str(context.exception))

    @patch('os.path.exists')
    def test_path_traversal(self, mock_exists):
        """Test that paths with traversal characters are rejected."""
        mock_exists.return_value = True

        # Test basic traversal
        with self.assertRaises(ValidationError) as context:
            VideoAnalysisInput(file_path="../secret.mp4")
        self.assertIn("Path traversal attempt detected", str(context.exception))
