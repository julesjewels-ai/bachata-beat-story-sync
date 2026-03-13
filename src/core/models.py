"""
Data Transfer Objects (DTOs) for Bachata Beat-Story Sync.
These models define the strict contracts for data exchange between layers.
"""


from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MusicalSection(BaseModel):
    """
    A detected musical section within a track.
    """

    model_config = ConfigDict(extra="forbid")

    label: str = Field(
        ...,
        description="Section label: 'intro', 'high_energy', "
        "'low_energy', 'buildup', 'breakdown', 'outro'",
    )
    start_time: float = Field(..., description="Start timestamp in seconds")
    end_time: float = Field(..., description="End timestamp in seconds")
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
    duration: float = Field(..., description="Duration of the track in seconds")
    peaks: list[float] = Field(..., description="Timestamps of high intensity peaks")
    sections: list[MusicalSection] = Field(
        default_factory=list,
        description="Detected musical sections with timestamps and labels",
    )
    beat_times: list[float] = Field(
        default_factory=list,
        description="Precise timestamps of each detected beat (seconds)",
    )
    intensity_curve: list[float] = Field(
        default_factory=list,
        description="Normalised RMS energy (0.0-1.0) at each beat position",
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
    duration: float = Field(..., description="Duration of the video clip in seconds")
    is_vertical: bool = Field(
        False, description="Whether the video is vertical (height > width)"
    )
    thumbnail_data: bytes | None = Field(
        None, description="Binary data of the video thumbnail (PNG format)"
    )


class SegmentPlan(BaseModel):
    """
    One planned clip segment in the montage timeline.
    """

    model_config = ConfigDict(extra="forbid")

    video_path: str = Field(..., description="Path to the source video file")
    start_time: float = Field(
        ..., description="Start time in the source video (seconds)"
    )
    duration: float = Field(..., description="Duration to extract (seconds)")
    timeline_position: float = Field(
        ..., description="Position on the output timeline (seconds)"
    )
    intensity_level: str = Field(
        ..., description="Intensity category: 'high', 'medium', or 'low'"
    )
    speed_factor: float = Field(
        1.0, description="Playback speed multiplier (>1 = fast, <1 = slow-mo)"
    )
    section_label: str | None = Field(
        None,
        description="Musical section this segment belongs to"
        " (e.g. 'intro', 'high_energy')",
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
        0.9, description="Speed multiplier for low-intensity clips (<1 = slow-mo)"
    )
    max_clips: int | None = Field(
        None, description="Maximum number of clip segments (None = unlimited)"
    )
    max_duration_seconds: float | None = Field(
        None, description="Maximum total montage duration in seconds (None = unlimited)"
    )

    # Clip variety — randomise start offset within reused clips
    clip_variety_enabled: bool = Field(
        True, description="Randomise start offset within clips to avoid repetition"
    )

    # B-Roll settings (FEAT-011)
    broll_interval_seconds: float = Field(
        13.5, description="Target interval between B-roll clips in seconds"
    )
    broll_interval_variance: float = Field(
        1.5, description="Allowed variance in B-roll intervals (± seconds)"
    )

    # Shorts Generator Configs
    is_shorts: bool = Field(False, description="Generate a vertical 9:16 short")
    seed: str = Field(
        "", description="Seed for deterministic stochasticity in unique generation"
    )
    accelerate_pacing: bool = Field(
        False,
        description="Gradually decrease clip durations towards the end (Dynamic Flow)",
    )
    randomize_speed_ramps: bool = Field(
        False, description="Apply random variance to speed ramps for a human touch"
    )
    abrupt_ending: bool = Field(
        False, description="End sharply to create a cliffhanger effect"
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
        "none",
        description="FFmpeg xfade transition type: "
        "'none', 'fade', 'wipeleft', 'wiperight', 'slideup', etc.",
    )
    transition_duration: float = Field(
        0.5, description="Duration of each transition in seconds"
    )

    # Frame Interpolation for Slow Motion (FEAT-010)
    interpolation_method: str = Field(
        "blend",
        description="Frame interpolation method for slow"
        " motion (<1.0x). Options: 'none', 'blend', 'mci'",
    )

    # Video Style / Color Grading (FEAT-012)
    video_style: Literal["none", "bw", "vintage", "warm", "cool", "golden"] = Field(
        "none",
        description="Color grading style applied to all segments. "
        "Options: 'none', 'bw', 'vintage', 'warm', 'cool', 'golden'",
    )

    # Per-Track Intro Variety (FEAT-017)
    prefix_offset: int = Field(
        0,
        description="Rotate the forced prefix clip list by this many positions. "
        "Pipeline sets this to track_index to vary intros across videos.",
    )

    # Audio Overlay (FEAT-013)
    audio_overlay: Literal["none", "waveform", "bars"] = Field(
        "none",
        description="Music-synced visualizer pattern. "
        "Options: 'none', 'waveform' (lines), 'bars' (frequency bars)",
    )
    audio_overlay_opacity: float = Field(
        0.5,
        description="Opacity of the audio visualizer block (0.0 to 1.0)"
    )
    audio_overlay_position: Literal["left", "center", "right"] = Field(
        "right",
        description="Horizontal position of the audio overlay: "
        "'left', 'center', 'right'",
    )

    # Audio Hook Detection (FEAT-019)
    audio_start_offset: float = Field(
        0.0,
        description="Start the montage from this point in the audio (seconds). "
        "Used by smart-start to shift the audio window for shorts.",
    )


class AudioMixConfig(BaseModel):
    """
    Configuration for mixing multiple audio tracks.
    """

    model_config = ConfigDict(extra="forbid")

    crossfade_duration_seconds: float = Field(
        2.0, description="Duration in seconds for the crossfades between tracks"
    )
