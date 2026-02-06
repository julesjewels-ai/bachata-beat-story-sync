"""
Core business logic for Bachata Beat-Story Sync.
Handles audio analysis logic and video synchronization algorithms.
"""
import logging
import os
from typing import List, Optional
from pydantic import ValidationError
from src.core.video_analyzer import (
    VideoAnalyzer, VideoAnalysisInput, SUPPORTED_VIDEO_EXTENSIONS
)
from src.core.montage import MontageGenerator
from src.core.models import AudioAnalysisResult, VideoAnalysisResult
from src.core.interfaces import ProgressObserver

logger = logging.getLogger(__name__)


class BachataSyncEngine:
    """
    The main engine responsible for syncing video segments to audio.
    """

    def __init__(self) -> None:
        self.video_analyzer = VideoAnalyzer()
        self.montage_generator = MontageGenerator()

    def scan_video_library(
        self, directory: str, observer: Optional[ProgressObserver] = None
    ) -> List[VideoAnalysisResult]:
        """
        Scans a directory for video files and assigns a visual intensity score.
        """
        if not os.path.exists(directory):
            raise FileNotFoundError(f"Video directory not found: {directory}")

        files_to_process = self._collect_video_files(directory)
        total_files = len(files_to_process)
        clips = []

        # Process files with progress reporting
        try:
            for i, video_path in enumerate(files_to_process):
                filename = os.path.basename(video_path)
                if observer:
                    observer.on_progress(
                        i, total_files, f"Scanning {filename}..."
                    )

                if result := self._process_video_file(video_path):
                    clips.append(result)
        finally:
            if observer:
                observer.on_progress(
                    total_files, total_files, "Scan complete."
                )

        return clips

    def _collect_video_files(self, directory: str) -> List[str]:
        """Recursively collects all supported video files in a directory."""
        return [
            os.path.join(root, file)
            for root, _, files in os.walk(directory)
            for file in files
            if os.path.splitext(file)[1].lower() in SUPPORTED_VIDEO_EXTENSIONS
        ]

    def _process_video_file(
        self, video_path: str
    ) -> Optional[VideoAnalysisResult]:
        """Helper to process a single video file."""
        try:
            input_data = VideoAnalysisInput(file_path=video_path)
            return self.video_analyzer.analyze(input_data)
        except (ValidationError, ValueError) as e:
            logger.warning(f"Skipping invalid video {video_path}: {e}")
        except Exception as e:
            logger.error(f"Error processing {video_path}: {e}")

        return None

    def generate_story(self, audio_data: AudioAnalysisResult,
                       video_clips: List[VideoAnalysisResult],
                       output_path: str) -> str:
        """
        Syncs clips to audio data and exports the timeline.
        """
        # Logic to match audio.peaks with video.intensity_score
        logger.info(
            f"Synthesizing {len(video_clips)} clips against "
            f"{audio_data.bpm} BPM audio..."
        )

        return self.montage_generator.generate(
            audio_data, video_clips, output_path
        )
