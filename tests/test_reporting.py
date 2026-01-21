"""
Tests for the ExcelReportGenerator.
"""
import pytest
import os
import openpyxl
from src.services.reporting import ExcelReportGenerator
from src.core.models import AudioAnalysisResult, VideoAnalysisResult

def test_generate_report(tmp_path):
    output_path = tmp_path / "test_report.xlsx"

    audio_data = AudioAnalysisResult(
        filename="bachata.wav",
        bpm=128.0,
        duration=180.0,
        peaks=[10.5, 20.0],
        sections=["intro", "verse"]
    )

    video_data = [
        VideoAnalysisResult(
            path="/videos/clip1.mp4",
            intensity_score=0.8,
            duration=10.0
        ),
        VideoAnalysisResult(
            path="/videos/clip2.mp4",
            intensity_score=0.4,
            duration=15.0
        )
    ]

    generator = ExcelReportGenerator()
    result = generator.generate_report(audio_data, video_data, str(output_path))

    assert result == str(output_path)
    assert os.path.exists(output_path)

    # Verify Content
    wb = openpyxl.load_workbook(output_path)
    assert "Analysis Summary" in wb.sheetnames
    assert "Video Library" in wb.sheetnames

    ws_summary = wb["Analysis Summary"]
    assert ws_summary["B2"].value == "bachata.wav"
    assert ws_summary["B3"].value == 128.0

    ws_videos = wb["Video Library"]
    assert ws_videos["A2"].value == "/videos/clip1.mp4"
    assert ws_videos["C2"].value == 0.8
