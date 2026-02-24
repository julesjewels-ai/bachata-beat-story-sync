"""
Unit tests for reporting generators and factory.
"""
import pytest
import json
import os
from unittest.mock import MagicMock, patch
from src.services.reporting.json_generator import JsonReportGenerator
from src.services.reporting.excel_generator import ExcelReportGenerator
from src.services.reporting.factory import ReportFactory
from src.services.reporting.exceptions import UnsupportedReportFormatError
from src.core.models import AudioAnalysisResult, VideoAnalysisResult, MusicalSection


@pytest.fixture
def sample_data():
    audio = AudioAnalysisResult(
        filename="test.wav",
        bpm=120.0,
        duration=60.0,
        peaks=[1.0, 2.0],
        sections=[MusicalSection(label="intro", start_time=0.0, end_time=10.0, avg_intensity=0.5)],
        beat_times=[0.5, 1.0],
        intensity_curve=[0.1, 0.2]
    )
    video = [
        VideoAnalysisResult(
            path="/tmp/vid1.mp4",
            intensity_score=0.8,
            duration=10.0,
            is_vertical=False,
            thumbnail_data=b"fake_png"
        )
    ]
    return audio, video


def test_json_generator(sample_data, tmp_path):
    """Test JSON report generation."""
    audio, video = sample_data
    generator = JsonReportGenerator()
    out_path = tmp_path / "report.json"

    result_path = generator.generate_report(audio, video, str(out_path))

    assert result_path == str(out_path)
    assert out_path.exists()

    with open(out_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    assert data["audio_analysis"]["filename"] == "test.wav"
    assert data["summary"]["total_videos"] == 1
    # Check thumbnail exclusion - dict should not contain the key
    assert "thumbnail_data" not in data["video_analysis"][0]


def test_factory_get_generator():
    """Test factory returns correct generator instances."""
    json_gen = ReportFactory.get_generator("json")
    assert isinstance(json_gen, JsonReportGenerator)

    excel_gen = ReportFactory.get_generator("excel")
    assert isinstance(excel_gen, ExcelReportGenerator)


def test_factory_invalid_format():
    """Test factory raises error for unknown formats."""
    with pytest.raises(UnsupportedReportFormatError):
        ReportFactory.get_generator("invalid_format")


def test_factory_case_insensitive():
    """Test factory handles case insensitivity."""
    gen = ReportFactory.get_generator("JSON")
    assert isinstance(gen, JsonReportGenerator)


@patch("src.services.reporting.excel_generator.openpyxl.Workbook")
def test_excel_generator_structure(mock_workbook, sample_data):
    """Test Excel generator calls openpyxl correctly."""
    audio, video = sample_data
    generator = ExcelReportGenerator()

    # Mock the workbook and active sheet
    wb = mock_workbook.return_value
    ws = MagicMock()
    wb.active = ws
    wb.create_sheet.return_value = ws

    generator.generate_report(audio, video, "dummy.xlsx")

    # Verify workbook was saved
    wb.save.assert_called_with("dummy.xlsx")
    # Verify sheets were created/accessed
    assert wb.create_sheet.call_count >= 1
