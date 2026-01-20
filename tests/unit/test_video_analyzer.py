"""
Unit tests for the VideoAnalyzer module.
"""
import unittest
from unittest.mock import patch, MagicMock
import numpy as np
from pydantic import ValidationError
from src.core.video_analyzer import VideoAnalyzer, VideoAnalysisInput

class TestVideoAnalyzer(unittest.TestCase):
    """
    Test suite for the VideoAnalyzer class.
    """

    @patch('os.path.exists', return_value=True)
    @patch('cv2.VideoCapture')
    def test_analyze_video(self, mock_video_capture, mock_exists):
        """
        Tests the video analysis logic with a mock video.
        """
        # Mock the video capture object
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = [30.0, 300]  # FPS, Frame Count
        mock_cap.read.side_effect = [
            (True, np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)),
            (True, np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)),
            (False, None)
        ]
        mock_video_capture.return_value = mock_cap

        analyzer = VideoAnalyzer()
        # FIX: Wrap input in VideoAnalysisInput
        input_data = VideoAnalysisInput(file_path='dummy_path.mp4')
        result = analyzer.analyze(input_data)

        self.assertEqual(result.path, 'dummy_path.mp4')
        self.assertAlmostEqual(result.duration, 10.0)
        self.assertGreater(result.intensity_score, 0.0)

    @patch('os.path.exists', return_value=False)
    def test_analyze_file_not_found(self, mock_exists):
        """
        Tests that a ValueError is raised when the video file does not exist.
        (Changed from FileNotFoundError because Pydantic validator raises ValueError)
        """
        with self.assertRaises(ValidationError) as context:
             VideoAnalysisInput(file_path='non_existent_file.mp4')
        self.assertIn("File not found", str(context.exception))

if __name__ == '__main__':
    unittest.main()
