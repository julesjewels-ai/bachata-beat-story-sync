"""
JSON report generator service.
"""
import json
import logging
from typing import List, Any, Dict
from src.core.models import AudioAnalysisResult, VideoAnalysisResult
from src.services.reporting.exceptions import ReportingError

logger = logging.getLogger(__name__)


class JsonReportGenerator:
    """
    Generates JSON reports from analysis data.
    Useful for integration with other tools or web frontends.
    """

    def generate(self,
                 audio_data: AudioAnalysisResult,
                 video_data: List[VideoAnalysisResult],
                 output_path: str) -> str:
        """
        Creates a JSON file with analysis details.

        Note: thumbnail_data is excluded from the JSON report to keep file size manageable.

        Args:
            audio_data: The audio analysis result.
            video_data: List of video analysis results.
            output_path: Destination path for the .json file.

        Returns:
            The path to the generated file.

        Raises:
            ReportingError: If the report cannot be saved.
        """
        try:
            # serialization
            # We explicitly exclude thumbnail_data to prevent massive JSON files
            videos_json = [
                v.model_dump(mode='json', exclude={'thumbnail_data'})
                for v in video_data
            ]

            report_data = {
                "audio": audio_data.model_dump(mode='json'),
                "videos": videos_json,
                "metadata": {
                    "video_count": len(video_data),
                    "audio_bpm": audio_data.bpm,
                    "audio_duration": audio_data.duration
                }
            }

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2)

            logger.info("JSON Report generated at: %s", output_path)
            return output_path

        except IOError as e:
            raise ReportingError(f"Failed to save JSON report to {output_path}: {e}")
        except Exception as e:
            raise ReportingError(f"Error generating JSON report: {e}")
