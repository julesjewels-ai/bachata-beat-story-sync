"""
Reporting service for generating analysis reports.
"""
import logging
from typing import List
import openpyxl
from openpyxl.chart import BarChart, Reference
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
        if ws_summary:
            ws_summary.title = "Analysis Summary"
            self._write_summary(ws_summary, audio_data, len(video_data))
        else:
            ws_summary = wb.create_sheet(title="Analysis Summary")
            self._write_summary(ws_summary, audio_data, len(video_data))

        # Sheet 2: Video Details
        ws_videos = wb.create_sheet(title="Video Library")
        self._write_video_details(ws_videos, video_data)

        # Sheet 3: Visualizations
        self._add_visualizations(wb, "Video Library", len(video_data))

        wb.save(output_path)
        logger.info(f"Report generated at: {output_path}")
        return output_path

    def _write_summary(self, ws, audio_data: AudioAnalysisResult, video_count: int):
        """Writes summary data to the worksheet."""
        headers = ["Metric", "Value"]
        data = [
            ("Audio File", audio_data.filename),
            ("BPM", audio_data.bpm),
            ("Duration (s)", audio_data.duration),
            ("Peak Count", len(audio_data.peaks)),
            ("Sections", ", ".join(audio_data.sections)),
            ("Total Videos Scanned", video_count)
        ]

        # Write Headers
        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_num, value=header)
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal="center")

        # Write Data
        for row_num, (metric, value) in enumerate(data, 2):
            ws.cell(row=row_num, column=1, value=metric).font = Font(bold=True)
            ws.cell(row=row_num, column=2, value=value)

        # Auto-width
        self._adjust_column_widths(ws)

    def _write_video_details(self, ws, video_data: List[VideoAnalysisResult]):
        """Writes detailed video analysis data."""
        headers = ["File Path", "Duration (s)", "Intensity Score"]

        # Write Headers
        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_num, value=header)
            cell.font = Font(bold=True)

        # Write Data
        for row_num, video in enumerate(video_data, 2):
            ws.cell(row=row_num, column=1, value=video.path)
            ws.cell(row=row_num, column=2, value=video.duration)
            ws.cell(row=row_num, column=3, value=video.intensity_score)

        self._adjust_column_widths(ws)

    def _adjust_column_widths(self, ws):
        """Auto-adjusts column widths based on content."""
        for column_cells in ws.columns:
            length = max(len(str(cell.value) or "") for cell in column_cells)
            length = min(length, 50) # Cap width
            ws.column_dimensions[get_column_letter(column_cells[0].column)].width = length + 2

    def _add_visualizations(self, wb, video_sheet_name: str, data_count: int):
        """
        Adds a chart to visualize video intensity.

        Args:
            wb: The openpyxl Workbook object.
            video_sheet_name: Name of the sheet containing video data.
            data_count: Number of video entries.
        """
        if data_count == 0:
            return

        ws = wb.create_sheet(title="Visualizations")

        # Create Chart
        chart = BarChart()
        chart.type = "col"
        chart.style = 10
        chart.title = "Video Intensity Distribution"
        chart.y_axis.title = "Intensity Score"
        chart.x_axis.title = "Video Clip Index"

        # Reference Data from Video Library sheet
        # Column 3 is Intensity Score. Row 1 is header.
        data = Reference(
            wb[video_sheet_name],
            min_col=3,
            min_row=1,
            max_row=data_count + 1,
            max_col=3
        )
        chart.add_data(data, titles_from_data=True)

        ws.add_chart(chart, "A1")
