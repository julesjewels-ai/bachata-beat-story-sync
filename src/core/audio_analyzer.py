"""
Audio analysis module for Bachata Beat-Story Sync.
"""
import logging
import os
import numpy as np
import librosa
from src.core.models import AudioAnalysisInput, AudioAnalysisResult

logger = logging.getLogger(__name__)


class AudioAnalyzer:
    """
    Analyzes audio files to extract rhythm, beats, and intensity features.
    """

    def analyze(self, input_data: AudioAnalysisInput) -> AudioAnalysisResult:
        """
        Analyzes a Bachata track to find BPM, beats, and intensity drops.
        """
        file_path = input_data.file_path

        try:
            # Load audio file
            # sr=None preserves the native sampling rate
            y, sr = librosa.load(file_path, sr=None)

            # Extract features
            duration = float(librosa.get_duration(y=y, sr=sr))

            # beat_track returns tempo (float) and beat_frames (ndarray)
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)

            # onset_detect returns onset_frames (ndarray)
            onset_frames = librosa.onset.onset_detect(y=y, sr=sr)
            onset_times = librosa.frames_to_time(onset_frames, sr=sr)

            # Convert numpy types to python types for Pydantic
            bpm_val = float(tempo) if np.ndim(tempo) == 0 else float(tempo[0])  # type: ignore
            peaks_list = [float(t) for t in onset_times]

            # Placeholder for segmentation (requires more complex analysis)
            sections = ["full_track"]

            return AudioAnalysisResult(
                file_path=file_path,
                filename=os.path.basename(file_path),
                bpm=bpm_val,
                duration=duration,
                peaks=peaks_list,
                sections=sections
            )

        except Exception as e:
            logger.error(f"Failed to analyze audio file {file_path}: {e}")
            raise RuntimeError(f"Audio analysis failed: {e}") from e
