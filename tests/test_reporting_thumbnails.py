"""
Tests for Thumbnail Embedding in Excel Reports.
"""
import openpyxl
import io
from PIL import Image
from src.services.reporting import ExcelReportGenerator
from src.core.models import AudioAnalysisResult, VideoAnalysisResult


def test_excel_report_includes_thumbnails(tmp_path):
    """
    Verifies that the generated Excel report includes embedded images.
    """
    output_path = tmp_path / "thumbnail_test_report.xlsx"

    # Create dummy image bytes
    img = Image.new('RGB', (60, 30), color='red')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    thumbnail_bytes = img_byte_arr.getvalue()

    # Mock Data
    audio_data = AudioAnalysisResult(
        filename="test_audio.wav",
        bpm=120,
        duration=60,
        peaks=[],
        sections=[]
    )

    video_data = [
        VideoAnalysisResult(
            path="v1.mp4",
            intensity_score=0.1,
            duration=5,
            thumbnail_data=thumbnail_bytes
        ),
        VideoAnalysisResult(
            path="v2.mp4",
            intensity_score=0.5,
            duration=5,
            thumbnail_data=None  # Test no image
        ),
    ]

    # Generate
    generator = ExcelReportGenerator()
    generator.generate_report(audio_data, video_data, str(output_path))

    # Verify
    wb = openpyxl.load_workbook(output_path)
    ws = wb["Video Library"]

    # Check images exist
    # openpyxl stores images in ws._images
    assert hasattr(ws, '_images')
    assert len(ws._images) == 1

    # Check text fallback
    # Row 2 has image (index 0 in list), Row 3 has None
    # Row 2 col 1 is where image is anchored. I didn't set a value there.
    # Row 3 col 1 should be "[No Image]"

    assert ws.cell(row=3, column=1).value == "[No Image]"

    # Check Headers
    assert ws.cell(row=1, column=1).value == "Thumbnail"
    assert ws.cell(row=1, column=2).value == "File Path"
