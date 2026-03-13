"""
Audio analysis module for Bachata Beat-Story Sync.
"""

import gc
import logging
import os

import librosa
import numpy as np
from pydantic import BaseModel, Field, field_validator

from src.core.models import AudioAnalysisResult, MusicalSection
from src.core.validation import validate_file_path

logger = logging.getLogger(__name__)

SUPPORTED_AUDIO_EXTENSIONS = {".wav", ".mp3"}


class AudioAnalysisInput(BaseModel):
    """
    Input model for audio analysis validation.
    """

    file_path: str = Field(..., description="Path to the audio file")

    @field_validator("file_path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        return validate_file_path(v, SUPPORTED_AUDIO_EXTENSIONS)


def _merge_short_boundaries(boundaries: list[int]) -> list[int]:
    """Merge very short sections (fewer than 3 beats) into their neighbour."""
    if not boundaries:
        return []

    merged: list[int] = [boundaries[0]]
    for b in boundaries[1:]:
        if b - merged[-1] < 3 and b != boundaries[-1]:
            continue  # skip this boundary — section too short
        merged.append(b)
    return merged


def _determine_section_label(
    i: int,
    total_sections: int,
    avg_intensity: float,
    start_idx: int,
    end_idx: int,
    smoothed: np.ndarray,
) -> str:
    """Determine the musical section label using position and intensity."""
    if i == 0 and avg_intensity < 0.5:
        return "intro"
    if i == total_sections - 2 and avg_intensity < 0.5:
        return "outro"
    if avg_intensity >= 0.65:
        return "high_energy"
    if avg_intensity < 0.35:
        return "low_energy"

    # Check if this is a transition (rising or falling)
    if end_idx < len(smoothed) and start_idx < len(smoothed):
        delta = smoothed[min(end_idx - 1, len(smoothed) - 1)] - smoothed[start_idx]
        if delta > 0.1:
            return "buildup"
        if delta < -0.1:
            return "breakdown"

    return "mid_energy"


def detect_sections(
    beat_times: list[float],
    intensity_curve: list[float],
    duration: float,
    smoothing_window: int = 8,
    change_threshold: float = 0.15,
) -> list[MusicalSection]:
    """
    Detect musical sections from the intensity envelope.

    Smooths the per-beat intensity curve, finds change-points where the
    smoothed gradient exceeds a threshold, and labels each resulting
    section by its average energy level.

    Args:
        beat_times: Precise beat timestamps (seconds).
        intensity_curve: Normalised RMS energy (0.0-1.0) per beat.
        duration: Total track duration in seconds.
        smoothing_window: Number of beats for the moving-average kernel.
        change_threshold: Minimum absolute change in smoothed intensity
            to trigger a section boundary.

    Returns:
        List of MusicalSection objects covering the full track.
    """
    if len(beat_times) < 2 or len(intensity_curve) < 2:
        # Not enough data — return single full-track section
        label = "full_track"
        avg = float(np.mean(intensity_curve)) if intensity_curve else 0.5
        return [
            MusicalSection(
                label=label,
                start_time=0.0,
                end_time=duration,
                avg_intensity=avg,
            )
        ]

    curve = np.array(intensity_curve, dtype=np.float64)

    # Smooth the curve with a simple moving average
    kernel_size = max(1, min(smoothing_window, len(curve)))
    kernel = np.ones(kernel_size) / kernel_size
    smoothed = np.convolve(curve, kernel, mode="same")

    # Compute absolute gradient of the smoothed curve
    gradient = np.abs(np.diff(smoothed))

    # Find change-point indices where gradient exceeds threshold
    change_points = list(np.where(gradient >= change_threshold)[0] + 1)

    # Build boundary indices: [0, cp1, cp2, ..., len(curve)]
    boundaries = [0] + change_points + [len(curve)]
    # Remove duplicates and sort
    boundaries = sorted(set(boundaries))

    boundaries = _merge_short_boundaries(boundaries)

    sections: list[MusicalSection] = []
    for i in range(len(boundaries) - 1):
        start_idx = boundaries[i]
        end_idx = boundaries[i + 1]

        start_time = beat_times[start_idx] if start_idx < len(beat_times) else duration
        end_time = beat_times[end_idx] if end_idx < len(beat_times) else duration
        avg_intensity = float(np.mean(curve[start_idx:end_idx]))

        label = _determine_section_label(
            i, len(boundaries), avg_intensity, start_idx, end_idx, smoothed
        )

        sections.append(
            MusicalSection(
                label=label,
                start_time=round(start_time, 3),
                end_time=round(end_time, 3),
                avg_intensity=round(avg_intensity, 3),
            )
        )

    return (
        sections
        if sections
        else [
            MusicalSection(
                label="full_track",
                start_time=0.0,
                end_time=duration,
                avg_intensity=float(np.mean(curve)),
            )
        ]
    )


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
            rms_times = librosa.frames_to_time(curve_buffer, sr=sr)

            # Normalise RMS to 0.0-1.0
            rms_max = float(np.max(rms)) if len(rms) > 0 else 1.0
            if rms_max == 0.0:
                rms_max = 1.0

            intensity_curve = []
            for bt in beat_times_arr:
                # Find closest RMS frame to this beat
                idx = int(np.argmin(np.abs(rms_times - bt)))
                intensity_curve.append(float(rms[idx] / rms_max))

            # Convert numpy types to python types for Pydantic
            bpm_val = float(np.asarray(tempo).flat[0])
            peaks_list = [float(t) for t in onset_times]

            # Detect musical sections from intensity envelope
            sections = detect_sections(
                beat_times=beat_times_list,
                intensity_curve=intensity_curve,
                duration=duration,
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


# ------------------------------------------------------------------
# FEAT-019: Audio Hook Scoring for Smart Start Selection
# ------------------------------------------------------------------

def find_audio_hooks(
    audio_data: AudioAnalysisResult,
    short_duration: float,
    count: int,
    hook_window: float = 2.0,
    pace_target: float = 4.0,
    pace_tolerance: float = 1.0,
) -> list[float]:
    """Score candidate start positions and return the top *count*.

    Scoring formula per candidate beat::

        hook_score  = 0.3 × intensity + 0.3 × peak_proximity
        pace_score  = 0.2 × intensity_delta + 0.2 × section_bonus
        total       = hook_score + pace_score

    Args:
        audio_data: Analysed audio with beat_times, intensity_curve,
            peaks, sections, and duration.
        short_duration: Target length of each short in seconds.
        count: Number of hooks to return.
        hook_window: Seconds after start to evaluate hook quality.
        pace_target: Seconds after start where a pace shift is desired.
        pace_tolerance: ± tolerance around *pace_target* for section
            boundary detection.

    Returns:
        List of start-time floats (length ≤ *count*), sorted by score
        descending.  May be shorter than *count* if there aren't enough
        viable, non-overlapping candidates.
    """
    import bisect

    beat_times = audio_data.beat_times
    intensity = audio_data.intensity_curve
    peaks = sorted(audio_data.peaks)
    sections = audio_data.sections
    duration = audio_data.duration

    if not beat_times or not intensity:
        return [0.0] * min(count, 1)

    # ---- score every candidate beat --------------------------------
    scored: list[tuple[float, float]] = []  # (score, start_time)

    for idx, beat_t in enumerate(beat_times):
        # Filter: skip first 1s (count-in) and tail that can't fit
        if beat_t < 1.0:
            continue
        if beat_t + short_duration > duration:
            break

        # 1. Beat intensity (0.3)
        beat_intensity = intensity[idx] if idx < len(intensity) else 0.0

        # 2. Peak proximity bonus (0.3) — 1.0 if any peak within
        #    ±0.5s of start, decaying to 0.0
        peak_bonus = 0.0
        pi = bisect.bisect_left(peaks, beat_t - 0.5)
        while pi < len(peaks) and peaks[pi] <= beat_t + hook_window:
            dist = abs(peaks[pi] - beat_t)
            if dist <= 0.5:
                peak_bonus = max(peak_bonus, 1.0 - dist * 2.0)
            pi += 1

        # 3. Intensity delta near pace_target (0.2)
        target_time = beat_t + pace_target
        target_idx = bisect.bisect_left(beat_times, target_time)
        target_idx = min(target_idx, len(intensity) - 1)
        delta = abs(intensity[target_idx] - beat_intensity) if target_idx < len(intensity) else 0.0

        # 4. Section boundary bonus near pace_target (0.2)
        section_bonus = 0.0
        for sec in sections:
            if abs(sec.start_time - target_time) <= pace_tolerance:
                section_bonus = 1.0
                break

        total = (
            0.3 * beat_intensity
            + 0.3 * peak_bonus
            + 0.2 * delta
            + 0.2 * section_bonus
        )
        scored.append((total, beat_t))

    if not scored:
        return [0.0] * min(count, 1)

    # ---- select top-N with minimum separation ----------------------
    scored.sort(key=lambda x: x[0], reverse=True)
    min_sep = short_duration * 0.5
    selected: list[float] = []

    for score, start in scored:
        if len(selected) >= count:
            break
        if all(abs(start - s) >= min_sep for s in selected):
            selected.append(start)

    # Fallback: if best score is very low, ensure at least one hook
    if not selected:
        selected.append(0.0)

    return selected
