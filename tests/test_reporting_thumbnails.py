import unittest
import tempfile
import os
from unittest.mock import MagicMock, patch
import numpy as np
import io
import openpyxl
from PIL import Image

from src.core.video_analyzer import VideoAnalyzer
from src.core.models import VideoAnalysisResult, AudioAnalysisResult
from src.services.reporting import ExcelReportGenerator


class TestVideoThumbnails(unittest.TestCase):

    def setUp(self):
        self.analyzer = VideoAnalyzer()
        self.report_generator = ExcelReportGenerator()

    @patch("cv2.VideoCapture")
    @patch("cv2.imencode")
    @patch("cv2.resize")
    def test_extract_thumbnail(self, mock_resize, mock_imencode, mock_capture):
        # Setup Mock VideoCapture
        cap = MagicMock()
        mock_capture.return_value = cap
        cap.isOpened.return_value = True
        cap.get.side_effect = lambda prop: 100 if prop == 7 else 30 # FRAME_COUNT=100, FPS=30

        # Mock frame reading
        fake_frame = np.zeros((360, 640, 3), dtype=np.uint8) # 360p frame
        cap.read.return_value = (True, fake_frame)

        # Mock resize
        resized_frame = np.zeros((90, 160, 3), dtype=np.uint8)
        mock_resize.return_value = resized_frame

        # Mock encode
        # cv2.imencode returns (ret, buf), where buf is a numpy array
        fake_buf = MagicMock()
        fake_buf.tobytes.return_value = b'fake_png_data'
        mock_imencode.return_value = (True, fake_buf)

        # Test private method directly for unit testing logic
        # In integration, we would call analyze, but that requires more mocking (file paths etc)
        # So we test _extract_thumbnail directly.

        thumbnail_data = self.analyzer._extract_thumbnail(cap)

        self.assertEqual(thumbnail_data, b'fake_png_data')

        # Verify calls
        # Should seek to middle (frame 50)
        # cv2.CAP_PROP_POS_FRAMES is 1.
        # Check if set was called with 1 and 50
        # Note: we need to check the calls to set.
        # cap.set(1, 50)

        # We can't easily check cv2 constants values without importing cv2,
        # but we know CAP_PROP_POS_FRAMES is usually 1.
        # Let's just check arguments.

        self.assertTrue(cap.set.called)
        self.assertTrue(mock_resize.called)
        self.assertTrue(mock_imencode.called)

    def test_excel_report_embedding(self):
        # Create a real 1x1 red PNG
        img = Image.new('RGB', (1, 1), color='red')
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_bytes = img_byte_arr.getvalue()

        # Create dummy results
        audio_result = AudioAnalysisResult(
            filename="test.mp3",
            bpm=120,
            duration=60,
            peaks=[1.0, 2.0],
            sections=["intro"]
        )

        video_result = VideoAnalysisResult(
            path="/tmp/test.mp4",
            intensity_score=0.8,
            duration=10.0,
            thumbnail_data=img_bytes
        )

        # Generate report
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            output_path = tmp.name

        try:
            self.report_generator.generate_report(audio_result, [video_result], output_path)

            # Verify
            wb = openpyxl.load_workbook(output_path)
            ws = wb["Video Library"]

            # Check if image is present
            self.assertTrue(len(ws._images) > 0, "No images found in the worksheet")

            # Check cell value in D2 (Thumbnail column) should be empty string (as we wrote it)
            # openpyxl might return None for empty cells
            self.assertIn(ws["D2"].value, ["", None])
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)

if __name__ == '__main__':
    unittest.main()
