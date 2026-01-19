"""
Tests for the Reporting Service.
"""
import unittest
import os
from openpyxl import load_workbook
from src.core.models import AudioAnalysisResult, VideoAnalysisResult
from src.services.reporting import ExcelReportGenerator

class TestExcelReportGenerator(unittest.TestCase):
    """
    Test suite for the ExcelReportGenerator.
    """

    def setUp(self):
        self.report_generator = ExcelReportGenerator()
        self.output_path = "test_report.xlsx"

    def tearDown(self):
        if os.path.exists(self.output_path):
            os.remove(self.output_path)

    def test_generate_report(self):
        """
        Ensures the Excel report is generated with correct data.
        """
        # Mock Data
        audio_data = AudioAnalysisResult(
            filename="bachata_track.wav",
            bpm=130,
            duration=200.0,
            peaks=[10.5, 50.0],
            sections=["intro", "chorus"]
        )

        video_clips = [
            VideoAnalysisResult(
                path="/video/clip1.mp4",
                intensity_score=0.8,
                duration=15.0
            ),
            VideoAnalysisResult(
                path="/video/clip2.mp4",
                intensity_score=0.4,
                duration=12.0
            )
        ]

        # Action
        result_path = self.report_generator.generate_report(
            audio_data, video_clips, self.output_path
        )

        # Verification
        self.assertEqual(result_path, self.output_path)
        self.assertTrue(os.path.exists(self.output_path))

        # Check content using openpyxl
        wb = load_workbook(self.output_path)

        # Check Sheet 1: Audio Analysis
        ws_audio = wb["Audio Analysis"]
        self.assertEqual(ws_audio["B2"].value, "bachata_track.wav")
        self.assertEqual(ws_audio["B3"].value, 130)

        # Check Sheet 2: Video Library
        ws_video = wb["Video Library"]
        self.assertEqual(ws_video["A2"].value, "/video/clip1.mp4")
        self.assertEqual(ws_video["C2"].value, 0.8)
        self.assertEqual(ws_video["A3"].value, "/video/clip2.mp4")

        wb.close()

if __name__ == '__main__':
    unittest.main()
