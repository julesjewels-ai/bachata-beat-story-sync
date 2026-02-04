import unittest
import io
import openpyxl
import tempfile
import os
from src.services.reporting import ExcelReportGenerator
from src.core.models import AudioAnalysisResult, VideoAnalysisResult
from PIL import Image

class TestReportingThumbnails(unittest.TestCase):
    def test_report_with_thumbnails(self):
        """Test generating report with thumbnails."""
        generator = ExcelReportGenerator()

        # Create dummy thumbnail bytes (valid JPEG)
        img = Image.new('RGB', (10, 10), color='red')
        byte_arr = io.BytesIO()
        img.save(byte_arr, format='JPEG')
        thumbnail_bytes = byte_arr.getvalue()

        audio_data = AudioAnalysisResult(
            filename="song.wav",
            bpm=120,
            duration=60,
            peaks=[],
            sections=[]
        )

        video_data = [
            VideoAnalysisResult(
                path="video1.mp4",
                intensity_score=0.5,
                duration=10,
                thumbnail=thumbnail_bytes
            ),
            VideoAnalysisResult(
                path="video2.mp4",
                intensity_score=0.6,
                duration=10,
                thumbnail=None # No thumbnail
            )
        ]

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            output_path = tmp.name

        # Close the file handle so openpyxl can save to it (Windows compat, though strictly linux env here)

        try:
            generator.generate_report(audio_data, video_data, output_path)

            # Load back
            wb = openpyxl.load_workbook(output_path)
            ws = wb["Video Library"]

            # Check headers
            self.assertEqual(ws["A1"].value, "Thumbnail")
            self.assertEqual(ws["B1"].value, "File Path")

            # Check data
            self.assertEqual(ws["B2"].value, "video1.mp4")
            self.assertEqual(ws["B3"].value, "video2.mp4")

            # Verify images present
            # openpyxl 3.x stores images in ws._images
            self.assertTrue(hasattr(ws, '_images'))
            self.assertGreaterEqual(len(ws._images), 1)

        finally:
            if os.path.exists(output_path):
                os.remove(output_path)

    def test_report_thumbnail_error_handling(self):
        """Test that invalid thumbnail bytes don't crash report generation."""
        generator = ExcelReportGenerator()

        audio_data = AudioAnalysisResult(
            filename="song.wav", bpm=120, duration=60, peaks=[], sections=[]
        )

        video_data = [
            VideoAnalysisResult(
                path="video1.mp4",
                intensity_score=0.5,
                duration=10,
                thumbnail=b'invalid_garbage_bytes'
            )
        ]

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            output_path = tmp.name

        try:
            # Should not raise exception
            generator.generate_report(audio_data, video_data, output_path)

            wb = openpyxl.load_workbook(output_path)
            ws = wb["Video Library"]

            # Check that it fell back to error text (column 1, row 2)
            self.assertEqual(ws["A2"].value, "[Error]")

        finally:
             if os.path.exists(output_path):
                os.remove(output_path)
