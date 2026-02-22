"""
Data Transfer Objects (DTOs) for Bachata Beat-Story Sync.
These models define the strict contracts for data exchange between layers.
"""
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class MusicalSection(BaseModel):
    """
    A detected musical section within a track.
    """
    model_config = ConfigDict(extra="forbid")

    label: str = Field(
        ..., description="Section label: 'intro', 'high_energy', "
        "'low_energy', 'buildup', 'breakdown', 'outro'"
    )
    start_time: float = Field(
        ..., description="Start timestamp in seconds"
    )
    end_time: float = Field(
        ..., description="End timestamp in seconds"
    )
    avg_intensity: float = Field(
        ..., description="Average normalised intensity (0.0-1.0)"
    )


class AudioAnalysisResult(BaseModel):
    """
    Result model for audio analysis.
    """
    model_config = ConfigDict(extra="forbid")

    filename: str = Field(..., description="Name of the audio file")
    bpm: float = Field(..., description="Beats per minute of the track")
    duration: float = Field(
        ..., description="Duration of the track in seconds"
    )
    peaks: List[float] = Field(
        ..., description="Timestamps of high intensity peaks"
    )
    sections: List[MusicalSection] = Field(
        default_factory=list,
        description="Detected musical sections with timestamps and labels"
    )
    beat_times: List[float] = Field(
        default_factory=list,
        description="Precise timestamps of each detected beat (seconds)"
    )
    intensity_curve: List[float] = Field(
        default_factory=list,
        description="Normalised RMS energy (0.0-1.0) at each beat position"
    )


class VideoAnalysisResult(BaseModel):
    """
    Result model for video analysis.
    """
    model_config = ConfigDict(extra="forbid")

    path: str = Field(..., description="Absolute path to the video file")
    intensity_score: float = Field(
        ..., description="Visual intensity score (0.0 to 1.0)"
    )
    duration: float = Field(
        ..., description="Duration of the video clip in seconds"
    )
    thumbnail_data: Optional[bytes] = Field(
        None, description="Binary data of the video thumbnail (PNG format)"
    )


class SegmentPlan(BaseModel):
    """
    One planned clip segment in the montage timeline.
    """
    model_config = ConfigDict(extra="forbid")

    video_path: str = Field(
        ..., description="Path to the source video file"
    )
    start_time: float = Field(
        ..., description="Start time in the source video (seconds)"
    )
    duration: float = Field(
        ..., description="Duration to extract (seconds)"
    )
    timeline_position: float = Field(
        ..., description="Position on the output timeline (seconds)"
    )
    intensity_level: str = Field(
        ..., description="Intensity category: 'high', 'medium', or 'low'"
    )
    speed_factor: float = Field(
        1.0, description="Playback speed multiplier (>1 = fast, <1 = slow-mo)"
    )
    section_label: Optional[str] = Field(
        None, description="Musical section this segment belongs to (e.g. 'intro', 'high_energy')"
    )


class PacingConfig(BaseModel):
    """
    Configuration for montage clip pacing.

    Controls how long clips last at each intensity level, the minimum
    clip duration, and whether durations snap to beat boundaries.
    """
    model_config = ConfigDict(extra="forbid")

    min_clip_seconds: float = Field(
        1.5, description="Hard floor — no clip shorter than this (seconds)"
    )
    high_intensity_seconds: float = Field(
        2.5, description="Target duration for high-intensity clips (seconds)"
    )
    medium_intensity_seconds: float = Field(
        4.0, description="Target duration for medium-intensity clips (seconds)"
    )
    low_intensity_seconds: float = Field(
        6.0, description="Target duration for low-intensity clips (seconds)"
    )
    snap_to_beats: bool = Field(
        True, description="Round durations to nearest beat boundary"
    )
    high_intensity_threshold: float = Field(
        0.65, description="Intensity >= this is 'high'"
    )
    low_intensity_threshold: float = Field(
        0.35, description="Intensity < this is 'low'"
    )
    speed_ramp_enabled: bool = Field(
        True, description="Enable speed ramping per intensity level"
    )
    high_intensity_speed: float = Field(
        1.2, description="Speed multiplier for high-intensity clips (>1 = fast)"
    )
    medium_intensity_speed: float = Field(
        1.0, description="Speed multiplier for medium-intensity clips"
    )
    low_intensity_speed: float = Field(
        0.7, description="Speed multiplier for low-intensity clips (<1 = slow-mo)"
    )
    max_clips: Optional[int] = Field(
        None, description="Maximum number of clip segments (None = unlimited)"
    )
    max_duration_seconds: Optional[float] = Field(
        None, description="Maximum total montage duration in seconds (None = unlimited)"
    )

    # Clip variety — randomise start offset within reused clips
    clip_variety_enabled: bool = Field(
        True, description="Randomise start offset within clips to avoid repetition"
    )

    # Section detection configuration
    section_detection_enabled: bool = Field(
        True, description="Enable musical section detection"
    )
    section_smoothing_window: int = Field(
        8, description="Number of beats to smooth intensity over for section detection"
    )
    section_change_threshold: float = Field(
        0.15, description="Minimum intensity change to trigger a section boundary"
    )

    # Transition configuration
    transition_type: str = Field(
        "none", description="FFmpeg xfade transition type: "
        "'none', 'fade', 'wipeleft', 'wiperight', 'slideup', etc."
    )
    transition_duration: float = Field(
        0.5, description="Duration of each transition in seconds"
    )

class AudioMixConfig(BaseModel):
    """
    Configuration for mixing multiple audio tracks.
    """
    model_config = ConfigDict(extra="forbid")

    crossfade_duration_seconds: float = Field(
        2.0, description="Duration in seconds for the crossfades between tracks"
    )

