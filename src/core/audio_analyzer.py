"""
Audio analysis module for Bachata Beat-Story Sync.
"""
import os
import logging
import librosa
import numpy as np
from pydantic import BaseModel, Field, field_validator
from src.core.validation import validate_file_path
from src.core.models import AudioAnalysisResult

logger = logging.getLogger(__name__)

SUPPORTED_AUDIO_EXTENSIONS = {'.wav', '.mp3'}


class AudioAnalysisInput(BaseModel):
    """
    Input model for audio analysis validation.
    """
    file_path: str = Field(..., description="Path to the audio file")

    @field_validator('file_path')
    @classmethod
    def validate_path(cls, v: str) -> str:
        return validate_file_path(v, SUPPORTED_AUDIO_EXTENSIONS)


class AudioAnalyzer:
    """
    Analyzes audio files to extract musical features.
    """

    def analyze(self, input_data: AudioAnalysisInput) -> AudioAnalysisResult:
        """
        Analyzes an audio file to extract BPM, beats, and peaks.

        Args:
            input_data: Validated input containing the file path.

        Returns:
            AudioAnalysisResult with extracted features.
        """
        file_path = input_data.file_path

        try:
            # Load audio file
            y, sr = librosa.load(file_path, sr=None)
            duration = librosa.get_duration(y=y, sr=sr)

            # Detect BPM (tempo) and beats
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)

            # Ensure tempo is a float (librosa can return an array)
            if isinstance(tempo, np.ndarray):
                bpm = float(tempo[0]) if tempo.size > 0 else 0.0
            else:
                bpm = float(tempo)

            # Detect Onset Strength for peaks
            onset_env = librosa.onset.onset_strength(y=y, sr=sr)
            # Find peaks in onset envelope
            # Parameters tuned for typical music onset detection
            peak_frames = librosa.util.peak_pick(
                onset_env,
                pre_max=3,
                post_max=3,
                pre_avg=3,
                post_avg=5,
                delta=0.5,
                wait=10
            )
            peak_times = librosa.frames_to_time(peak_frames, sr=sr).tolist()

            return AudioAnalysisResult(
                filename=os.path.basename(file_path),
                bpm=bpm,
                duration=float(duration),
                peaks=peak_times,
                sections=["main"]
            )

        except Exception as e:
            logger.error("Error analyzing audio %s: %s", file_path, e)
            raise
