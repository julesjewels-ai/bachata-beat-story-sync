import pytest
import os
import openpyxl
from src.core.models import AudioAnalysisResult, VideoAnalysisResult
from src.services.reporting import ExcelReportGenerator

def test_excel_report_generation(tmp_path):
    audio_data = AudioAnalysisResult(
        filename="bachata.wav",
        bpm=128,
        duration=180.0,
        peaks=[10.5, 20.0],
        sections=["Intro", "Verse"]
    )

    video_data = [
        VideoAnalysisResult(path="clip1.mp4", intensity_score=0.8, duration=5.0),
        VideoAnalysisResult(path="clip2.mp4", intensity_score=0.2, duration=10.0)
    ]

    output_file = tmp_path / "report.xlsx"

    service = ExcelReportGenerator()
    result_path = service.generate_report(audio_data, video_data, str(output_file))

    assert os.path.exists(result_path)

    # Verify content
    wb = openpyxl.load_workbook(result_path)
    assert "Audio Analysis" in wb.sheetnames
    assert "Video Library" in wb.sheetnames

    ws_audio = wb["Audio Analysis"]
    # Check if we can find the keys in the first column and values in the second
    # Since we used append, rows are sequential.
    # Row 1: Metric, Value
    # Row 2: Filename, bachata.wav
    assert ws_audio["A2"].value == "Filename"
    assert ws_audio["B2"].value == "bachata.wav"
    assert ws_audio["B3"].value == 128

    ws_video = wb["Video Library"]
    assert ws_video["A2"].value == "clip1.mp4"
    assert ws_video["C2"].value == 0.8
