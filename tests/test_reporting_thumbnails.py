import pytest
import os
import io
import openpyxl
from src.services.reporting import ExcelReportGenerator
from src.core.models import AudioAnalysisResult, VideoAnalysisResult
from PIL import Image as PILImage

def test_generate_report_with_thumbnails(tmp_path):
    output_path = tmp_path / "test_report_images.xlsx"

    # Create a dummy image bytes
    img = PILImage.new('RGB', (60, 30), color = 'red')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    thumbnail_bytes = buf.getvalue()

    audio_data = AudioAnalysisResult(
        filename="bachata.wav",
        bpm=128.0,
        duration=180.0,
        peaks=[10.5],
        sections=["intro"]
    )

    video_data = [
        VideoAnalysisResult(
            path="/videos/clip1.mp4",
            intensity_score=0.8,
            duration=10.0,
            thumbnail_data=thumbnail_bytes
        )
    ]

    generator = ExcelReportGenerator()
    result = generator.generate_report(audio_data, video_data, str(output_path))

    assert os.path.exists(result)

    wb = openpyxl.load_workbook(result)
    ws_videos = wb["Video Library"]

    # Check if images are present
    images = getattr(ws_videos, '_images', getattr(ws_videos, 'images', []))
    assert len(images) == 1
