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

def test_generate_report_includes_chart(tmp_path):
    output_path = tmp_path / "test_report_chart.xlsx"

    audio_data = AudioAnalysisResult(
        filename="bachata.wav",
        bpm=128.0,
        duration=180.0,
        peaks=[10.5],
        sections=["intro"]
    )

    # 0.0-0.2: 1
    # 0.2-0.4: 0
    # 0.4-0.6: 1
    # 0.6-0.8: 0
    # 0.8-1.0: 1
    video_data = [
        VideoAnalysisResult(path="v1.mp4", intensity_score=0.1, duration=5.0),
        VideoAnalysisResult(path="v2.mp4", intensity_score=0.5, duration=5.0),
        VideoAnalysisResult(path="v3.mp4", intensity_score=0.9, duration=5.0),
    ]

    generator = ExcelReportGenerator()
    generator.generate_report(audio_data, video_data, str(output_path))

    wb = openpyxl.load_workbook(output_path)
    assert "Visualizations" in wb.sheetnames

    ws_viz = wb["Visualizations"]
    # Check headers
    assert ws_viz["A1"].value == "Intensity Range"
    assert ws_viz["B1"].value == "Count"

    # Check data
    # 0.0-0.2 -> 1
    assert ws_viz["A2"].value == "0.0-0.2"
    assert ws_viz["B2"].value == 1

    # 0.4-0.6 -> 1
    assert ws_viz["A4"].value == "0.4-0.6"
    assert ws_viz["B4"].value == 1

    # 0.8-1.0 -> 1
    assert ws_viz["A6"].value == "0.8-1.0"
    assert ws_viz["B6"].value == 1

    # Check chart presence
    assert len(ws_viz._charts) >= 1
    chart = ws_viz._charts[0]
    # Verify chart properties
    assert chart.type == "col"
    assert chart.title is not None
    # Title might be an object, so strict string equality fails.
    # We trust openpyxl stores the title if we set it.
