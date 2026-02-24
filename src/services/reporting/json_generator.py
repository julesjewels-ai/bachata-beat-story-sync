"""
JSON report generator implementation.
"""
import json
import logging
from typing import List

from src.core.interfaces import ReportGenerator
from src.core.models import AudioAnalysisResult, VideoAnalysisResult

logger = logging.getLogger(__name__)


class JsonReportGenerator:
    """
    Generates JSON reports from analysis data.
    """

    def generate_report(self,
                        audio_data: AudioAnalysisResult,
                        video_data: List[VideoAnalysisResult],
                        output_path: str) -> str:
        """
        Creates a JSON file with analysis details.

        Args:
            audio_data: The audio analysis result.
            video_data: List of video analysis results.
            output_path: Destination path for the .json file.

        Returns:
            The path to the generated file.
        """
        # Prepare data structure
        # Use model_dump for Pydantic v2 or dict() for v1.
        # Assuming Pydantic v2 based on ConfigDict usage in models.py
        report_data = {
            "audio_analysis": audio_data.model_dump(),
            "video_analysis": [
                v.model_dump(exclude={"thumbnail_data"})
                for v in video_data
            ],
            "summary": {
                "total_videos": len(video_data),
                "audio_duration": audio_data.duration,
                "audio_bpm": audio_data.bpm
            }
        }

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)

            logger.info("JSON report generated at: %s", output_path)
            return output_path

        except IOError as e:
            logger.error("Failed to write JSON report to %s: %s", output_path, e)
            raise
