"""
Audio analysis module for Bachata Beat-Story Sync.
"""
import logging
import os
from typing import List
import numpy as np
import librosa
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
            bpm_val = float(np.asarray(tempo).flat[0])
            peaks_list = [float(t) for t in onset_times]

            # Perform structural segmentation
            sections = self._detect_sections(y, int(sr), duration)

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

    def _detect_sections(
        self, y: np.ndarray, sr: int, duration: float
    ) -> List[AudioSection]:
        """
        Detects musical sections using structural segmentation.
        """
        try:
            # Compute features for segmentation
            # 1. Chroma (harmonic content)
            chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
            # 2. MFCC (timbral content)
            mfcc = librosa.feature.mfcc(y=y, sr=sr)

            # Synchronize features to the shorter length
            min_frames = min(chroma.shape[1], mfcc.shape[1])
            chroma = chroma[:, :min_frames]
            mfcc = mfcc[:, :min_frames]

            # Stack vertically
            data = np.vstack([chroma, mfcc])

            # Use librosa's agglomerative clustering
            # k=8 assumes roughly 8 distinct structural components
            labels = librosa.segment.agglomerative(data, k=8)

            # Find boundaries where the label changes
            boundary_frames = [0]
            for i in range(1, len(labels)):
                if labels[i] != labels[i - 1]:
                    boundary_frames.append(i)
            # Add the final frame
            boundary_frames.append(len(labels))

            # Convert frame indices to time
            boundary_times = librosa.frames_to_time(boundary_frames, sr=sr)

            sections: List[AudioSection] = []

            for i in range(len(boundary_times) - 1):
                start_time = float(boundary_times[i])
                end_time = float(boundary_times[i + 1])

                # Clamp end_time to duration
                if end_time > duration:
                    end_time = duration

                if start_time >= duration:
                    break

                section_dur = end_time - start_time

                # Filter out very short segments (< 4s)
                if section_dur < 4.0 and sections:
                    # Merge with previous section
                    prev = sections[-1]
                    prev.end_time = end_time
                    prev.duration += section_dur
                else:
                    sections.append(
                        AudioSection(
                            start_time=start_time,
                            end_time=end_time,
                            duration=section_dur,
                            label=f"Section {len(sections) + 1}"
                        )
                    )

            # Fallback if no valid sections found
            if not sections:
                return [AudioSection(
                    start_time=0.0,
                    end_time=duration,
                    duration=duration,
                    label="full_track"
                )]

            return sections

        except Exception as e:
            logger.warning(
                "Segmentation failed: %s. Fallback to full track.", e
            )
            return [AudioSection(
                start_time=0.0,
                end_time=duration,
                duration=duration,
                label="full_track"
            )]
