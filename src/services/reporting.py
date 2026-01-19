"""
Reporting service for Bachata Beat-Story Sync.
Handles generation of Excel reports from analysis data.
"""
import logging
from typing import List
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from src.core.models import AudioAnalysisResult, VideoAnalysisResult

logger = logging.getLogger(__name__)

class ExcelReportGenerator:
    """
    Generates structured Excel reports from analysis results.
    """

    def generate_report(self, audio_data: AudioAnalysisResult,
                        video_clips: List[VideoAnalysisResult],
                        output_path: str) -> str:
        """
        Creates an Excel file with analysis details.

        Args:
            audio_data: The audio analysis result.
            video_clips: A list of video analysis results.
            output_path: The file path to save the .xlsx report.

        Returns:
            The path to the generated Excel file.
        """
        wb = Workbook()

        # Sheet 1: Audio Analysis
        ws_audio = wb.active
        ws_audio.title = "Audio Analysis"
        self._write_audio_sheet(ws_audio, audio_data)

        # Sheet 2: Video Analysis
        ws_video = wb.create_sheet("Video Library")
        self._write_video_sheet(ws_video, video_clips)

        wb.save(output_path)
        logger.info(f"Report generated successfully at {output_path}")
        return output_path

    def _write_audio_sheet(self, ws, data: AudioAnalysisResult) -> None:
        """Populates the Audio Analysis sheet."""
        # Headers
        headers = ["Property", "Value"]
        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_num, value=header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="DDDDDD", end_color="DDDDDD", fill_type="solid")

        # Data
        rows = [
            ("Filename", data.filename),
            ("BPM", data.bpm),
            ("Duration (s)", data.duration),
            ("Emotional Peaks", ", ".join(map(str, data.peaks))),
            ("Sections", ", ".join(data.sections))
        ]

        for row_num, (prop, val) in enumerate(rows, 2):
            ws.cell(row=row_num, column=1, value=prop)
            ws.cell(row=row_num, column=2, value=val)

        # Adjust column widths
        ws.column_dimensions['A'].width = 20
        ws.column_dimensions['B'].width = 50

    def _write_video_sheet(self, ws, clips: List[VideoAnalysisResult]) -> None:
        """Populates the Video Library sheet."""
        # Headers
        headers = ["Video Path", "Duration (s)", "Intensity Score"]
        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_num, value=header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="DDDDDD", end_color="DDDDDD", fill_type="solid")

        # Data
        for row_num, clip in enumerate(clips, 2):
            ws.cell(row=row_num, column=1, value=clip.path)
            ws.cell(row=row_num, column=2, value=clip.duration)
            ws.cell(row=row_num, column=3, value=clip.intensity_score)

        # Adjust column widths
        ws.column_dimensions['A'].width = 60
        ws.column_dimensions['B'].width = 15
        ws.column_dimensions['C'].width = 15
