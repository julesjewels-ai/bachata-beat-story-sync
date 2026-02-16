"""
Audio analysis module for Bachata Beat-Story Sync.
"""
import logging
import os
import numpy as np
import librosa
from src.core.models import (
    AudioAnalysisResult, AudioAnalysisInput
)

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
            tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)

            # Convert beat frames to precise timestamps
            beat_times_arr = librosa.frames_to_time(beat_frames, sr=sr)
            beat_times_list = [float(t) for t in beat_times_arr]

            # onset_detect returns onset_frames (ndarray)
            onset_frames = librosa.onset.onset_detect(y=y, sr=sr)
            onset_times = librosa.frames_to_time(onset_frames, sr=sr)

            # Compute per-beat intensity (RMS energy at each beat position)
            rms = librosa.feature.rms(y=y)[0]
            rms_times = librosa.frames_to_time(
                np.arange(len(rms)), sr=sr
            )

            # Normalise RMS to 0.0-1.0
            rms_max = float(np.max(rms)) if len(rms) > 0 else 1.0
            if rms_max == 0.0:
                rms_max = 1.0

            intensity_curve = []
            for bt in beat_times_arr:
                # Find closest RMS frame to this beat
                idx = int(np.argmin(np.abs(rms_times - bt)))
                intensity_curve.append(
                    float(rms[idx] / rms_max)
                )

            # Convert numpy types to python types for Pydantic
            bpm_val = float(np.asarray(tempo).flat[0])
            peaks_list = [float(t) for t in onset_times]

            # Placeholder for segmentation (requires more complex analysis)
            sections = ["full_track"]

            return AudioAnalysisResult(
                filename=os.path.basename(file_path),
                bpm=bpm_val,
                duration=duration,
                peaks=peaks_list,
                sections=sections,
                beat_times=beat_times_list,
                intensity_curve=intensity_curve,
            )

        except Exception as e:
            logger.error("Failed to analyze audio file %s: %s", file_path, e)
            raise RuntimeError(f"Audio analysis failed: {e}") from e
