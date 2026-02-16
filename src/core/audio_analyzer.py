"""
Audio analysis module for Bachata Beat-Story Sync.
"""
import logging
import os
import numpy as np
import librosa
import sklearn.cluster  # type: ignore
from pydantic import BaseModel, Field, field_validator
from src.core.validation import validate_file_path
from src.core.models import AudioAnalysisResult, MusicalSection

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


def detect_sections(
    y: np.ndarray,
    sr: int,
    beat_times: list[float],
    intensity_curve: list[float],
    duration: float,
) -> list[MusicalSection]:
    """
    Detect musical sections using structural analysis (Chroma + MFCC).

    Uses recurrence and agglomerative clustering to find structural boundaries,
    then labels each section based on its average intensity.

    Args:
        y: Audio time series.
        sr: Sampling rate.
        beat_times: Precise beat timestamps (seconds).
        intensity_curve: Normalised RMS energy (0.0-1.0) per beat.
        duration: Total track duration in seconds.

    Returns:
        List of MusicalSection objects covering the full track.
    """
    if len(beat_times) < 2 or len(intensity_curve) < 2:
        # Not enough data — return single full-track section
        label = "full_track"
        avg = float(np.mean(intensity_curve)) if intensity_curve else 0.5
        return [MusicalSection(
            label=label, start_time=0.0, end_time=duration,
            avg_intensity=avg,
        )]

    try:
        # 1. Feature Extraction
        # Chroma (harmonic content)
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr, bins_per_octave=12)
        # MFCC (timbral content)
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)

        # 2. Sync features to beats
        # Convert beat times to frames
        beat_frames = librosa.time_to_frames(beat_times, sr=sr)

        # Ensure beat_frames is not empty and within bounds
        if len(beat_frames) == 0:
            raise ValueError("No beat frames detected")

        # Cast to list of ints for compatibility with librosa.util.sync
        beat_frames_idx = [int(f) for f in beat_frames]

        chroma_sync = librosa.util.sync(chroma, beat_frames_idx, aggregate=np.median)
        mfcc_sync = librosa.util.sync(mfcc, beat_frames_idx, aggregate=np.median)

        # 3. Stack features
        features = np.vstack([chroma_sync, mfcc_sync])

        # 4. Structural Segmentation using Agglomerative Clustering
        # Determine number of segments (k).
        # Heuristic: duration / 15 seconds, clamped between 4 and 16
        k = max(4, min(16, int(duration / 15)))

        # Build recurrence matrix for connectivity
        # Use mode='affinity' for similarity, self=True to ensure diagonal
        rec = librosa.segment.recurrence_matrix(features, mode='affinity', self=True, sym=True)

        # Use sklearn's AgglomerativeClustering
        # Transpose features to (n_samples, n_features) as expected by sklearn
        agg = sklearn.cluster.AgglomerativeClustering(n_clusters=k, connectivity=rec, linkage='ward')
        agg.fit(features.T)

        labels = agg.labels_

        # Find boundaries where labels change
        # Boundary indices refer to beat indices
        boundaries_frames = [0]
        for i in range(1, len(labels)):
            if labels[i] != labels[i-1]:
                boundaries_frames.append(i)

        # Convert boundary indices (which are beat indices) back to beat times
        boundary_times = [0.0]  # Start at 0
        for b_idx in boundaries_frames:
             if 0 <= b_idx < len(beat_times):
                 boundary_times.append(beat_times[b_idx])
        boundary_times.append(duration) # End at duration

        # Remove duplicates and sort
        boundary_times = sorted(list(set(boundary_times)))

        # 5. Create Sections and Label
        sections: list[MusicalSection] = []
        curve = np.array(intensity_curve, dtype=np.float64)

        for i in range(len(boundary_times) - 1):
            start_time = boundary_times[i]
            end_time = boundary_times[i + 1]

            # Find intensity indices corresponding to this time range
            # We use beat indices because intensity_curve is per-beat
            start_beat_idx = 0
            end_beat_idx = len(beat_times)

            for b_i, t in enumerate(beat_times):
                if t >= start_time:
                    start_beat_idx = b_i
                    break

            for b_i, t in enumerate(beat_times):
                if t >= end_time:
                    end_beat_idx = b_i
                    break

            # Clamp indices
            start_beat_idx = max(0, min(start_beat_idx, len(curve) - 1))
            end_beat_idx = max(start_beat_idx + 1, min(end_beat_idx, len(curve)))

            # Compute average intensity
            if start_beat_idx < end_beat_idx:
                segment_intensity = curve[start_beat_idx:end_beat_idx]
                avg_intensity = float(np.mean(segment_intensity))
            else:
                avg_intensity = 0.5 # Default if no beats found in segment

            # Labeling Logic (adapted from original)
            label = "mid_energy"
            if i == 0 and avg_intensity < 0.5:
                label = "intro"
            elif i == len(boundary_times) - 2 and avg_intensity < 0.5:
                label = "outro"
            elif avg_intensity >= 0.65:
                label = "high_energy"
            elif avg_intensity < 0.35:
                label = "low_energy"
            else:
                 # Check for transitions if we have enough context
                 pass # Could check slope here if needed, but structure implies sections are somewhat homogeneous

            sections.append(MusicalSection(
                label=label,
                start_time=round(start_time, 3),
                end_time=round(end_time, 3),
                avg_intensity=round(avg_intensity, 3),
            ))

        return sections if sections else [MusicalSection(
            label="full_track", start_time=0.0, end_time=duration,
            avg_intensity=float(np.mean(curve)),
        )]

    except Exception as e:
        logger.warning(f"Structural segmentation failed: {e}. Falling back to single section.")
        avg = float(np.mean(intensity_curve)) if intensity_curve else 0.5
        return [MusicalSection(
            label="full_track", start_time=0.0, end_time=duration,
            avg_intensity=avg,
        )]


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

            # Detect musical sections
            sections = detect_sections(
                y=y,
                sr=int(sr),  # Cast to int for type safety
                beat_times=beat_times_list,
                intensity_curve=intensity_curve,
                duration=duration,
            )

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
