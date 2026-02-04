"""
Tests for Chart Generation in Excel Reports.
"""
import openpyxl
from openpyxl.chart import BarChart
from src.services.reporting import ExcelReportGenerator
from src.core.models import AudioAnalysisResult, VideoAnalysisResult


def test_excel_report_includes_chart(tmp_path):
    """
    Verifies that the generated Excel report includes a 'Visualizations' sheet
    with a BarChart of intensity scores.
    """
    output_path = tmp_path / "chart_test_report.xlsx"

    # Mock Data
    audio_data = AudioAnalysisResult(
        filename="test_audio.wav",
        bpm=120,
        duration=60,
        peaks=[],
        sections=[]
    )

    video_data = [
        VideoAnalysisResult(path="v1.mp4", intensity_score=0.1, duration=5),
        VideoAnalysisResult(path="v2.mp4", intensity_score=0.5, duration=5),
        VideoAnalysisResult(path="v3.mp4", intensity_score=0.9, duration=5),
    ]

    # Generate
    generator = ExcelReportGenerator()
    generator.generate_report(audio_data, video_data, str(output_path))

    # Verify
    wb = openpyxl.load_workbook(output_path)

    # Check Sheet Existence
    assert "Visualizations" in wb.sheetnames
    ws_viz = wb["Visualizations"]

    # Check Chart Existence
    # Note: Accessing private attribute _charts is common for testing openpyxl
    assert len(ws_viz._charts) > 0  # type: ignore[attr-defined]
    chart = ws_viz._charts[0]  # type: ignore[attr-defined]

    assert isinstance(chart, BarChart)
    assert chart.type == "col"
    # Verify title is not None (content verification depends on openpyxl
    # version internals)
    assert chart.title is not None
