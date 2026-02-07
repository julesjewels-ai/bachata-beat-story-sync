import io
import openpyxl
from PIL import Image
from src.services.reporting import ExcelReportGenerator
from src.core.models import AudioAnalysisResult, VideoAnalysisResult

def test_generate_report_with_thumbnails(tmp_path):
    output_path = tmp_path / "test_report_images.xlsx"

    # Create a dummy image
    img = Image.new('RGB', (60, 30), color = 'red')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_bytes = img_byte_arr.getvalue()

    audio_data = AudioAnalysisResult(
        file_path="mock/bachata.wav",
        filename="bachata.wav", bpm=128.0, duration=180.0, peaks=[], sections=[]
    )

    video_data = [
        VideoAnalysisResult(
            path="/videos/clip1.mp4",
            intensity_score=0.8,
            duration=10.0,
            thumbnail_data=img_bytes
        ),
        VideoAnalysisResult(
            path="/videos/clip2.mp4",
            intensity_score=0.4,
            duration=15.0,
            thumbnail_data=None # Test missing image
        )
    ]

    generator = ExcelReportGenerator()
    generator.generate_report(audio_data, video_data, str(output_path))

    # Verify
    wb = openpyxl.load_workbook(output_path)
    ws = wb["Video Library"]

    # Check Header
    assert ws["D1"].value == "Thumbnail"

    # Check that images exist in the worksheet
    # Openpyxl 3.1+ stores images in ws._images
    assert hasattr(ws, '_images')
    assert len(ws._images) == 1

    # Verify row height
    # Row 2 (with image) should have height 60
    assert ws.row_dimensions[2].height == 60

    # Row 3 (no image) should not have modified height (default is usually None or ~15)
    assert ws.row_dimensions[3].height != 60
