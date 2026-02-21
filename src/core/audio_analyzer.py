"""
Audio analysis module for Bachata Beat-Story Sync.
"""
import gc
import logging
import os
import numpy as np
import librosa
import librosa.feature
import librosa.segment
import sklearn.cluster  # type: ignore
from typing import Optional
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


def _determine_section_label(
    avg_intensity: float,
    start_idx: int,
    end_idx: int,
    smoothed_curve: np.ndarray,
    is_first: bool = False,
    is_last: bool = False
) -> str:
    """
    Determine the label for a section based on intensity and position.
    """
    if is_first and avg_intensity < 0.5:
        return "intro"
    if is_last and avg_intensity < 0.5:
        return "outro"

    if avg_intensity >= 0.65:
        return "high_energy"
    if avg_intensity < 0.35:
        return "low_energy"

    # Check for transition
    if end_idx < len(smoothed_curve) and start_idx < len(smoothed_curve):
        # Use safe indices for delta calculation
        safe_end = min(end_idx - 1, len(smoothed_curve) - 1)
        safe_start = start_idx
        delta = smoothed_curve[safe_end] - smoothed_curve[safe_start]

        if delta > 0.1:
            return "buildup"
        if delta < -0.1:
            return "breakdown"

    return "mid_energy"


def segment_structure(
    y: np.ndarray,
    sr: int,
    beat_frames: np.ndarray,
    n_segments: int = 8
) -> list[int]:
    """
    Perform structural segmentation using recurrence matrix and clustering.

    Args:
        y: Audio time series.
        sr: Sampling rate.
        beat_frames: Beat locations in frames.
        n_segments: Target number of segments for clustering.

    Returns:
        List of beat indices where structural changes occur.
    """
    try:
        # Compute chroma features synchronized to beats
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        chroma_sync = librosa.util.sync(chroma, beat_frames, aggregate=np.median)  # type: ignore

        # Compute recurrence matrix
        rec = librosa.segment.recurrence_matrix(
            chroma_sync, mode='connectivity', metric='cosine', sparse=True
        )

        # Cluster segments
        clustering = sklearn.cluster.AgglomerativeClustering(
            n_clusters=n_segments, connectivity=rec
        )
        labels = clustering.fit_predict(chroma_sync.T)

        # Find boundaries where labels change
        boundaries = [0]
        for i in range(1, len(labels)):
            if labels[i] != labels[i-1]:
                boundaries.append(i)
        boundaries.append(len(labels))

        return sorted(list(set(boundaries)))

    except Exception as e:
        logger.warning(f"Structural segmentation failed: {e}. Falling back to intensity only.")
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
    Detect musical sections from intensity envelope and structural boundaries.

    Args:
        beat_times: Precise beat timestamps (seconds).
        intensity_curve: Normalised RMS energy (0.0-1.0) per beat.
        duration: Total track duration in seconds.
        smoothing_window: Number of beats for the moving-average kernel.
        change_threshold: Minimum absolute change in smoothed intensity.
        structural_boundaries: Optional list of beat indices from structural analysis.

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

    # Smooth the curve
    kernel_size = max(1, min(smoothing_window, len(curve)))
    kernel = np.ones(kernel_size) / kernel_size
    smoothed = np.convolve(curve, kernel, mode="same")

    # Compute intensity change points
    gradient = np.abs(np.diff(smoothed))
    change_points = list(np.where(gradient >= change_threshold)[0] + 1)

    # Combine with structural boundaries if provided
    boundaries = [0] + change_points
    if structural_boundaries:
        boundaries.extend(structural_boundaries)
    boundaries.append(len(curve))

    # Remove duplicates and sort
    boundaries = sorted(list(set(boundaries)))

    # Merge very short sections (fewer than 3 beats) into their neighbour
    merged: list[int] = [boundaries[0]]
    for b in boundaries[1:]:
        if b - merged[-1] < 3 and b != boundaries[-1]:
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

        label = _determine_section_label(
            avg_intensity=avg_intensity,
            start_idx=start_idx,
            end_idx=end_idx,
            smoothed_curve=smoothed,
            is_first=(i == 0),
            is_last=(i == len(boundaries) - 2)
        )

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
            y, sr = librosa.load(file_path, sr=22050)

            # Extract features
            duration = float(librosa.get_duration(y=y, sr=sr))

            # beat_track returns tempo (float) and beat_frames (ndarray)
            tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)

            # Convert beat frames to precise timestamps
            beat_times_arr = librosa.frames_to_time(beat_frames, sr=sr)
            beat_times_list = [float(t) for t in beat_times_arr]

            # Structural segmentation
            structural_boundaries = segment_structure(y, int(sr), beat_frames)

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

            # Convert numpy types to python types for Pydantic
            bpm_val = float(np.asarray(tempo).flat[0])
            peaks_list = [float(t) for t in onset_times]

            # Detect musical sections from intensity envelope and structural boundaries
            sections = detect_sections(
                beat_times=beat_times_list,
                intensity_curve=intensity_curve,
                duration=duration,
                structural_boundaries=structural_boundaries
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
