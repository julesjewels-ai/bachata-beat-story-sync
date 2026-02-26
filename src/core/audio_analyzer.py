"""
Audio analysis module for Bachata Beat-Story Sync.
"""
import gc
import logging
import os
from typing import Optional, List
import numpy as np
import librosa
from pydantic import BaseModel, Field, field_validator
from sklearn.cluster import AgglomerativeClustering
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


def segment_structure(
    y: np.ndarray,
    sr: int,
    beat_frames: np.ndarray,
    n_segments: Optional[int] = None
) -> List[int]:
    """
    Perform structural segmentation using chroma features and clustering.

    Uses Agglomerative Clustering on synchronized chroma features to find
    structural boundaries (e.g., verse/chorus changes).

    Args:
        y: Audio time series.
        sr: Sampling rate.
        beat_frames: Frame indices of detected beats.
        n_segments: Target number of segments. If None, estimated automatically
                    (roughly 1 segment per 15-30s, clamped between 4 and 12).

    Returns:
        List of frame indices representing segment boundaries.
    """
    try:
        # Extract Chroma CQT features (captures harmonic content)
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr, bins_per_octave=12)

        # Ensure we have enough beats
        if len(beat_frames) < 16:
            return []

        # Sync chroma to beats (aggregate chroma within each beat)
        beat_chroma = librosa.util.sync(chroma, beat_frames, aggregate=np.median)

        # Transpose to (n_beats, n_features) for clustering
        X = beat_chroma.T

        # Normalize features
        X = librosa.util.normalize(X, axis=1)

        # Estimate number of segments if not provided
        if n_segments is None:
            duration = librosa.get_duration(y=y, sr=sr)
            # Rough heuristic: one section every 20 seconds
            estimated = int(duration / 20)
            n_segments = max(4, min(estimated, 12))

        # Clamp n_segments to be at most n_beats
        n_segments = min(n_segments, X.shape[0])

        if n_segments < 2:
             return []

        clustering = AgglomerativeClustering(n_clusters=n_segments, linkage='ward')
        labels = clustering.fit_predict(X)

        # Find label changes to get boundaries
        # label_changes is indices in 'beat_frames'
        boundary_indices = [0]
        for i in range(1, len(labels)):
            if labels[i] != labels[i-1]:
                boundary_indices.append(i)

        return sorted(list(set(boundary_indices)))

    except Exception as e:
        logger.warning("Structural segmentation failed: %s", e)
        return []


def detect_sections(
    beat_times: list[float],
    intensity_curve: list[float],
    duration: float,
    smoothing_window: int = 8,
    change_threshold: float = 0.15,
    structural_boundaries: Optional[list[int]] = None
) -> list[MusicalSection]:
    """
    Detect musical sections combining intensity and structural analysis.

    Args:
        beat_times: Precise beat timestamps (seconds).
        intensity_curve: Normalised RMS energy (0.0-1.0) per beat.
        duration: Total track duration in seconds.
        smoothing_window: Number of beats for the moving-average kernel.
        change_threshold: Minimum absolute change in smoothed intensity
            to trigger a section boundary.
        structural_boundaries: Optional list of beat indices where structural
            changes occur (from segment_structure).

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

    curve = np.array(intensity_curve, dtype=np.float64)

    # Smooth the curve with a simple moving average
    kernel_size = max(1, min(smoothing_window, len(curve)))
    kernel = np.ones(kernel_size) / kernel_size
    smoothed = np.convolve(curve, kernel, mode="same")

    # Compute absolute gradient of the smoothed curve
    gradient = np.abs(np.diff(smoothed))

    # Find change-point indices where gradient exceeds threshold
    intensity_boundaries = list(np.where(gradient >= change_threshold)[0] + 1)

    # Combine intensity boundaries with structural boundaries
    # We prioritise structural boundaries, but keep significant intensity changes
    combined_boundaries = set(intensity_boundaries)

    if structural_boundaries:
        combined_boundaries.update(structural_boundaries)

    # Build boundary indices: [0, cp1, cp2, ..., len(curve)]
    boundaries = [0] + list(combined_boundaries) + [len(curve)]
    # Remove duplicates and sort
    boundaries = sorted(set(boundaries))

    # Merge very short sections (fewer than 4 beats) into their neighbour
    merged: list[int] = [boundaries[0]]
    for b in boundaries[1:]:
        if b - merged[-1] < 4 and b != boundaries[-1]:
            continue  # skip this boundary — section too short
        merged.append(b)
    boundaries = merged

    sections: list[MusicalSection] = []
    for i in range(len(boundaries) - 1):
        start_idx = boundaries[i]
        end_idx = boundaries[i + 1]

        start_time = beat_times[start_idx] if start_idx < len(beat_times) else duration
        end_time = beat_times[end_idx] if end_idx < len(beat_times) else duration
        avg_intensity = float(np.mean(curve[start_idx:end_idx]))

        # Label based on position and intensity
        if i == 0 and avg_intensity < 0.5:
            label = "intro"
        elif i == len(boundaries) - 2 and avg_intensity < 0.5:
            label = "outro"
        elif avg_intensity >= 0.65:
            label = "high_energy"
        elif avg_intensity < 0.35:
            label = "low_energy"
        else:
            # Check if this is a transition (rising or falling)
            if end_idx < len(smoothed) and start_idx < len(smoothed):
                delta = smoothed[min(end_idx - 1, len(smoothed) - 1)] - smoothed[start_idx]
                if delta > 0.1:
                    label = "buildup"
                elif delta < -0.1:
                    label = "breakdown"
                else:
                    label = "mid_energy"
            else:
                label = "mid_energy"

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
            # Load audio file — downsample to 22050 Hz to halve memory
            # (beat/onset detection works well at this rate)
            y, sr = librosa.load(file_path, sr=22050)

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
            curve_buffer = np.arange(len(rms))
            rms_times = librosa.frames_to_time(
                curve_buffer, sr=sr
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

            # Structural Segmentation
            # Pass pre-computed beat_frames to avoid re-computation
            struct_boundaries = segment_structure(y, sr, beat_frames)

            # Convert numpy types to python types for Pydantic
            bpm_val = float(np.asarray(tempo).flat[0])
            peaks_list = [float(t) for t in onset_times]

            # Detect musical sections from intensity envelope AND structure
            sections = detect_sections(
                beat_times=beat_times_list,
                intensity_curve=intensity_curve,
                duration=duration,
                structural_boundaries=struct_boundaries
            )

            result = AudioAnalysisResult(
                filename=os.path.basename(file_path),
                bpm=bpm_val,
                duration=duration,
                peaks=peaks_list,
                sections=sections,
                beat_times=beat_times_list,
                intensity_curve=intensity_curve,
            )

            # Eagerly release large NumPy arrays
            del y, rms, rms_times, onset_frames, onset_times
            del beat_frames, beat_times_arr, curve_buffer
            gc.collect()

            return result

        except Exception as e:
            logger.error("Failed to analyze audio file %s: %s", file_path, e)
            raise RuntimeError(f"Audio analysis failed: {e}") from e
