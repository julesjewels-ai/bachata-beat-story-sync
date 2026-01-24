"""
Reporting service for generating analysis reports.
"""
import logging
from typing import List, Any
import openpyxl
from openpyxl.styles import Font, Alignment
from openpyxl.utils import get_column_letter

from src.core.models import AudioAnalysisResult, VideoAnalysisResult

logger = logging.getLogger(__name__)

class ExcelReportGenerator:
    """
    Generates Excel reports from analysis data.
    """

    def generate_report(self,
                        audio_data: AudioAnalysisResult,
                        video_data: List[VideoAnalysisResult],
                        output_path: str) -> str:
        """
        Creates an Excel file with analysis details.

        Args:
            audio_data: The audio analysis result.
            video_data: List of video analysis results.
            output_path: Destination path for the .xlsx file.

        Returns:
            The path to the generated file.
        """
        wb = openpyxl.Workbook()

        # Sheet 1: Summary
        ws_summary = wb.active
        # wb.active is always set for a new Workbook
        ws_summary.title = "Analysis Summary"  # type: ignore
        self._write_summary(ws_summary, audio_data, len(video_data))

        # Sheet 2: Video Details
        ws_videos = wb.create_sheet(title="Video Library")
        self._write_video_details(ws_videos, video_data)

        wb.save(output_path)
        logger.info(f"Report generated at: {output_path}")
        return output_path

    def _write_summary(self, ws, audio_data: AudioAnalysisResult, video_count: int):
        """Writes summary data to the worksheet."""
        headers = ["Metric", "Value"]
        data: List[List[Any]] = [
            ["Audio File", audio_data.filename],
            ["BPM", audio_data.bpm],
            ["Duration (s)", audio_data.duration],
            ["Peak Count", len(audio_data.peaks)],
            ["Sections", ", ".join(audio_data.sections)],
            ["Total Videos Scanned", video_count]
        ]
        self._write_table(ws, headers, data, bold_first_col=True)

    def _write_video_details(self, ws, video_data: List[VideoAnalysisResult]):
        """Writes detailed video analysis data."""
        headers = ["File Path", "Duration (s)", "Intensity Score"]
        data = [
            [video.path, video.duration, video.intensity_score]
            for video in video_data
        ]
        self._write_table(ws, headers, data, bold_first_col=False)

    def _write_table(self, ws, headers: List[str], data: List[List[Any]], bold_first_col: bool = False):
        """Helper to write a standardized table with headers and auto-width."""
        # Write Headers
        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_num, value=header)
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal="center")

        # Write Data
        for row_num, row_data in enumerate(data, 2):
            for col_num, value in enumerate(row_data, 1):
                cell = ws.cell(row=row_num, column=col_num, value=value)
                if bold_first_col and col_num == 1:
                    cell.font = Font(bold=True)

        self._adjust_column_widths(ws)

    def _adjust_column_widths(self, ws):
        """Auto-adjusts column widths based on content."""
        for column_cells in ws.columns:
            length = max(len(str(cell.value) or "") for cell in column_cells)
            length = min(length, 50) # Cap width
            ws.column_dimensions[get_column_letter(column_cells[0].column)].width = length + 2
