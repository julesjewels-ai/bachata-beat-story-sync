"""
Core business logic for Bachata Beat-Story Sync.
Handles audio analysis logic and video synchronization algorithms.
"""

import logging
import os

from pydantic import ValidationError

from src.core.interfaces import ProgressObserver, VideoAnalyzerProtocol
from src.core.models import AudioAnalysisResult, PacingConfig, VideoAnalysisResult
from src.core.montage import MontageGenerator
from src.core.video_analyzer import (
    SUPPORTED_VIDEO_EXTENSIONS,
    VideoAnalysisInput,
)

logger = logging.getLogger(__name__)


class BachataSyncEngine:
    """
    The main engine responsible for syncing video segments to audio.
    """

    def __init__(self, video_analyzer: VideoAnalyzerProtocol) -> None:
        self.video_analyzer = video_analyzer
        self.montage_generator = MontageGenerator()

    def scan_video_library(
        self,
        directory: str,
        exclude_dirs: list[str] | None = None,
        observer: ProgressObserver | None = None,
    ) -> list[VideoAnalysisResult]:
        """
        Scans a directory for video files and assigns a visual intensity score.
        """
        if not os.path.exists(directory):
            raise FileNotFoundError(f"Video directory not found: {directory}")

        files_to_process = self._collect_video_files(directory, exclude_dirs)
        total_files = len(files_to_process)
        clips = []

        # Process files with progress reporting
        try:
            for i, video_path in enumerate(files_to_process):
                filename = os.path.basename(video_path)
                if observer:
                    observer.on_progress(i, total_files, f"Scanning {filename}...")

                if result := self._process_video_file(video_path):
                    clips.append(result)
        finally:
            if observer:
                observer.on_progress(total_files, total_files, "Scan complete.")

        return clips

    def _collect_video_files(
        self, directory: str, exclude_dirs: list[str] | None = None
    ) -> list[str]:
        """Recursively collects all supported video files in a directory."""
        exclude_dirs = (
            [os.path.abspath(d) for d in exclude_dirs] if exclude_dirs else []
        )
        collected = []
        for root, dirs, files in os.walk(directory):
            # Skip excluded directories
            if any(os.path.abspath(root).startswith(ex_dir) for ex_dir in exclude_dirs):
                # Don't mutate dirs here, just skip the files
                continue

            # Optionally mutate dirs to prevent os.walk from going deeper into excluded dirs
            dirs[:] = [
                d
                for d in dirs
                if not any(
                    os.path.abspath(os.path.join(root, d)).startswith(ex_dir)
                    for ex_dir in exclude_dirs
                )
            ]

            for file in files:
                if os.path.splitext(file)[1].lower() in SUPPORTED_VIDEO_EXTENSIONS:
                    collected.append(os.path.join(root, file))
        return collected

    def _process_video_file(self, video_path: str) -> VideoAnalysisResult | None:
        """Helper to process a single video file."""
        try:
            input_data = VideoAnalysisInput(file_path=video_path)
            return self.video_analyzer.analyze(input_data)
        except (ValidationError, ValueError) as e:
            logger.warning("Skipping invalid video %s: %s", video_path, e)
        except Exception as e:
            logger.error("Error processing %s: %s", video_path, e)

        return None

    def generate_story(
        self,
        audio_data: AudioAnalysisResult,
        video_clips: list[VideoAnalysisResult],
        output_path: str,
        broll_clips: list[VideoAnalysisResult] | None = None,
        audio_path: str | None = None,
        observer: ProgressObserver | None = None,
        pacing: PacingConfig | None = None,
    ) -> str:
        """
        Syncs clips to audio data and generates a montage video.

        Args:
            audio_data: Analyzed audio features.
            video_clips: Analyzed video clips with intensity scores.
            output_path: Path for the final output video.
            broll_clips: Optional list of B-roll video clips.
            audio_path: Optional path to audio file to overlay.
            observer: Optional progress observer for status updates.
            pacing: Optional pacing configuration (e.g. test mode limits).

        Returns:
            Path to the generated output video.
        """
        logger.info(
            "Synthesizing %d clips against %s BPM audio...",
            len(video_clips),
            audio_data.bpm,
        )

        return self.montage_generator.generate(
            audio_data,
            video_clips,
            output_path,
            audio_path=audio_path,
            broll_clips=broll_clips,
            observer=observer,
            pacing=pacing,
        )
