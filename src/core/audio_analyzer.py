"""
Audio analysis module for Bachata Beat-Story Sync.
"""
import logging
import os
import numpy as np
import librosa
import librosa.feature
import librosa.segment
from typing import List
from pydantic import BaseModel, Field, field_validator
from src.core.validation import validate_file_path
from src.core.models import AudioAnalysisResult, AudioSection

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
            bpm_val = float(tempo) if np.ndim(tempo) == 0 else float(tempo[0])
            peaks_list = [float(t) for t in onset_times]

            # Detect musical sections
            sections = self._detect_sections(y, sr, duration)

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
            logger.error(f"Failed to analyze audio file {file_path}: {e}")
            raise RuntimeError(f"Audio analysis failed: {e}") from e

    def _detect_sections(self, y: np.ndarray, sr: int, duration: float) -> List[AudioSection]:
        """
        Detects musical structure (sections) using recurrence analysis.
        """
        try:
            # 1. Compute features (Chromagram + MFCC) for structure analysis
            hop_length = 512
            # Use chroma_cqt for better musical structure detection
            # Note: chroma_cqt can be slow, but it's more accurate.
            # Fallback to chroma_stft if cqt fails or for speed?
            # Let's use chroma_cqt.
            chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop_length)

            # Stack MFCCs to capture timbre
            mfcc = librosa.feature.mfcc(y=y, sr=sr, hop_length=hop_length)

            # Ensure they have same number of frames
            min_frames = min(chroma.shape[1], mfcc.shape[1])
            chroma = chroma[:, :min_frames]
            mfcc = mfcc[:, :min_frames]

            features = np.vstack([chroma, mfcc])

            # 2. Compute recurrence matrix
            # Use 'affinity' mode for clustering
            R = librosa.segment.recurrence_matrix(features, mode='affinity', sym=True)

            # 3. Agglomerative clustering
            # Estimate number of sections: ~1 section per 30s, capped at 8
            n_sections = max(2, int(duration / 30))
            n_sections = min(n_sections, 8)

            # Use librosa's wrapper for agglomerative clustering
            labels = librosa.segment.agglomerative(R, k=n_sections)

            # 4. Convert frame labels to time intervals
            sections: List[AudioSection] = []
            frames = librosa.frames_to_time(np.arange(len(labels)), sr=sr, hop_length=hop_length)

            if len(labels) == 0:
                 return [AudioSection(
                    start_time=0.0,
                    end_time=duration,
                    duration=duration,
                    label="Full Track"
                )]

            current_label = labels[0]
            start_time = 0.0

            for i, label in enumerate(labels):
                if label != current_label:
                    end_time = float(frames[i])
                    sections.append(AudioSection(
                        start_time=start_time,
                        end_time=end_time,
                        duration=end_time - start_time,
                        label=f"Section {len(sections) + 1}"
                    ))
                    start_time = end_time
                    current_label = label

            # Add the last section
            end_time = duration
            sections.append(AudioSection(
                start_time=start_time,
                end_time=end_time,
                duration=end_time - start_time,
                label=f"Section {len(sections) + 1}"
            ))

            return sections

        except Exception as e:
            logger.warning(f"Structural segmentation failed: {e}. Fallback to full track.")
            return [AudioSection(
                start_time=0.0,
                end_time=duration,
                duration=duration,
                label="Full Track"
            )]
