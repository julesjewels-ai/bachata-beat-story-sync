import openpyxl
from io import BytesIO
from PIL import Image
from src.services.reporting import ExcelReportGenerator
from src.core.models import AudioAnalysisResult, VideoAnalysisResult


def test_report_includes_thumbnail(tmp_path):
    """Test that thumbnails are embedded in the report."""
    output_path = tmp_path / "thumbnail_test.xlsx"

    # Create a dummy valid JPEG image
    img = Image.new('RGB', (60, 30), color='red')
    img_byte_arr = BytesIO()
    img.save(img_byte_arr, format='JPEG')
    thumbnail_bytes = img_byte_arr.getvalue()

    video_data = [
        VideoAnalysisResult(
            path="video1.mp4",
            intensity_score=0.5,
            duration=10.0,
            thumbnail_data=thumbnail_bytes
        )
    ]

    audio_data = AudioAnalysisResult(
        filename="audio.wav",
        bpm=100,
        duration=10.0,
        peaks=[],
        sections=[]
    )

    generator = ExcelReportGenerator()
    generator.generate_report(audio_data, video_data, str(output_path))

    # Verify
    wb = openpyxl.load_workbook(output_path)
    ws = wb["Video Library"]

    # Check if image is present
    # Accessing private attribute _images is common for testing openpyxl
    # image embedding
    assert hasattr(ws, '_images')
    assert len(ws._images) == 1

    # Verify headers
    header_cell = ws.cell(row=1, column=4)
    assert header_cell.value == "Thumbnail"
