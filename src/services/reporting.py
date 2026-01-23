"""
Reporting service for generating analysis reports.
"""
import logging
from typing import List, Tuple
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
        self._add_visualizations(wb, video_data)

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

    def _add_visualizations(self, wb, video_data: List[VideoAnalysisResult]):
        """Adds a chart visualization of video intensity distribution."""
        ws = wb.create_sheet(title="Visualizations")

        # Calculate Histogram
        bins = self._compute_intensity_histogram(video_data)

        # Write Data
        headers = ["Intensity Range", "Count"]
        ws.append(headers)
        for label, count in bins:
            ws.append([label, count])

        # Create Chart
        chart = BarChart()
        chart.type = "col"
        chart.style = 10
        chart.title = "Video Intensity Distribution"
        chart.y_axis.title = "Count"
        chart.x_axis.title = "Intensity"

        data = Reference(ws, min_col=2, min_row=1, max_row=len(bins) + 1)
        cats = Reference(ws, min_col=1, min_row=2, max_row=len(bins) + 1)

        chart.add_data(data, titles_from_data=True)
        chart.set_categories(cats)

        ws.add_chart(chart, "E2")

    def _compute_intensity_histogram(self, video_data: List[VideoAnalysisResult]) -> List[Tuple[str, int]]:
        """
        Computes a histogram of intensity scores.
        Returns a list of (label, count) tuples.
        """
        # 5 bins: 0.0-0.2, 0.2-0.4, 0.4-0.6, 0.6-0.8, 0.8-1.0
        bins = [0] * 5
        labels = ["0.0-0.2", "0.2-0.4", "0.4-0.6", "0.6-0.8", "0.8-1.0"]

        for video in video_data:
            score = video.intensity_score
            if score < 0.2:
                bins[0] += 1
            elif score < 0.4:
                bins[1] += 1
            elif score < 0.6:
                bins[2] += 1
            elif score < 0.8:
                bins[3] += 1
            else:
                bins[4] += 1

        return list(zip(labels, bins))
