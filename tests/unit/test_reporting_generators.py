"""
Unit tests for reporting generators and factory.
"""
import json
import pytest
from src.core.models import AudioAnalysisResult, VideoAnalysisResult, MusicalSection
from src.services.reporting import (
    JsonReportGenerator,
    ExcelReportGenerator,
    ReportFactory,
    ReportingError,
    UnsupportedReportFormatError
)


@pytest.fixture
def sample_data():
    audio = AudioAnalysisResult(
        filename="test.wav",
        bpm=120.0,
        duration=60.0,
        peaks=[10.0, 20.0],
        sections=[MusicalSection(label="intro", start_time=0.0, end_time=10.0, avg_intensity=0.5)],
        beat_times=[0.5, 1.0, 1.5],
        intensity_curve=[0.1, 0.2, 0.3]
    )
    video = VideoAnalysisResult(
        path="/path/to/video.mp4",
        intensity_score=0.8,
        duration=5.0,
        thumbnail_data=b"fake_png_data"
    )
    return audio, [video]


def test_json_generator_success(tmp_path, sample_data):
    audio, videos = sample_data
    output_path = tmp_path / "report.json"

    generator = JsonReportGenerator()
    result = generator.generate(audio, videos, str(output_path))

    assert result == str(output_path)
    assert output_path.exists()

    with open(output_path) as f:
        data = json.load(f)

    assert data["audio"]["filename"] == "test.wav"
    assert len(data["videos"]) == 1
    assert data["videos"][0]["path"] == "/path/to/video.mp4"
    # Verify thumbnail_data is excluded
    assert "thumbnail_data" not in data["videos"][0]


def test_json_generator_error(tmp_path, sample_data):
    audio, videos = sample_data
    # Use a directory as output path to trigger IOError
    output_path = tmp_path

    generator = JsonReportGenerator()
    with pytest.raises(ReportingError):
        generator.generate(audio, videos, str(output_path))


def test_factory_xlsx():
    gen = ReportFactory.get_generator("report.xlsx")
    assert isinstance(gen, ExcelReportGenerator)


def test_factory_json():
    gen = ReportFactory.get_generator("report.json")
    assert isinstance(gen, JsonReportGenerator)


def test_factory_unsupported():
    with pytest.raises(UnsupportedReportFormatError):
        ReportFactory.get_generator("report.txt")


def test_factory_case_insensitive():
    gen = ReportFactory.get_generator("report.JSON")
    assert isinstance(gen, JsonReportGenerator)
