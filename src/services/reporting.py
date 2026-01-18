"""
Reporting services for generating analysis exports.
"""
import openpyxl
from openpyxl.styles import Font, PatternFill
from typing import List, Protocol
from src.core.models import AudioAnalysisResult, VideoAnalysisResult

class IReportGenerator(Protocol):
    """Interface for report generation services."""
    def generate_report(self, audio: AudioAnalysisResult, videos: List[VideoAnalysisResult], output_path: str) -> str:
        """Generates a report and returns the file path."""
        ...

class ExcelReportGenerator:
    """Generates an Excel report from analysis results."""

    def generate_report(self, audio: AudioAnalysisResult, videos: List[VideoAnalysisResult], output_path: str) -> str:
        """
        Creates an Excel workbook with Audio and Video analysis data.
        """
        wb = openpyxl.Workbook()

        # Audio Sheet
        ws_audio = wb.active
        ws_audio.title = "Audio Analysis"

        # Styling
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")

        # Audio Data
        ws_audio.append(["Metric", "Value"])
        for cell in ws_audio[1]:
            cell.font = header_font
            cell.fill = header_fill

        ws_audio.append(["Filename", audio.filename])
        ws_audio.append(["BPM", audio.bpm])
        ws_audio.append(["Duration (s)", audio.duration])
        ws_audio.append(["Peaks Count", len(audio.peaks)])
        ws_audio.append(["Sections", ", ".join(audio.sections)])

        # Video Sheet
        ws_video = wb.create_sheet("Video Library")
        headers = ["File Path", "Duration (s)", "Intensity Score"]
        ws_video.append(headers)

        for cell in ws_video[1]:
            cell.font = header_font
            cell.fill = header_fill

        for video in videos:
            ws_video.append([video.path, video.duration, video.intensity_score])

        # Basic Auto-width
        for ws in [ws_audio, ws_video]:
            for col in ws.columns:
                max_length = 0
                column = col[0].column_letter
                for cell in col:
                    try:
                        val_len = len(str(cell.value))
                        if val_len > max_length:
                            max_length = val_len
                    except Exception:
                        pass
                ws.column_dimensions[column].width = max_length + 2

        wb.save(output_path)
        return output_path
