"""
Data Transfer Objects (DTOs) for Bachata Beat-Story Sync.
These models define the strict contracts for data exchange between layers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
    thumbnail_data: Optional[bytes] = Field(
        None, description="Binary data of the video thumbnail (PNG format)"
    )
    scene_changes: list[float] = Field(
        default_factory=list,
        description="Timestamps (seconds) of detected visual scene changes",
    )
    opening_intensity: float = Field(
        0.0,
        description="Average visual motion intensity in the first 2 seconds (0.0-1.0)",
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
    section_label: Optional[str] = Field(
        None,
        description="Musical section this segment belongs to"
        " (e.g. 'intro', 'high_energy')",
    )


@dataclass
class SegmentDecision:
    """Records why a particular clip was chosen for a timeline slot."""

    timeline_start: float
    clip_path: str
    intensity_score: float
    section_label: Optional[str]
    duration: float
    speed: float
    reason: str


@dataclass
class SkipDecision:
    """Records why a clip was skipped at a given point."""

    clip_path: str
    reason: str


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
        0.5, description="Opacity of the audio visualizer block (0.0 to 1.0)"
    )
    audio_overlay_position: Literal["left", "center", "right"] = Field(
        "right",
        description="Horizontal position of the audio overlay: "
        "'left', 'center', 'right'",
    )
    audio_overlay_padding: int = Field(
        10,
        description="Distance in pixels from the screen edge (FEAT-021)",
    )

    # Audio Hook Detection (FEAT-019)
    audio_start_offset: float = Field(
        0.0,
        description="Start the montage from this point in the audio (seconds). "
        "Used by smart-start to shift the audio window for shorts.",
    )

    # Decision Explainability Log (FEAT-025)
    explain: bool = Field(
        False,
        description="Emit a Markdown decision log alongside the output video",
    )

    # Intro Visual Effects (FEAT-022)
    intro_effect: str = Field(
        "none",
        description="Visual effect applied to the first segment only. "
        "Use 'none' to disable, or a registered effect name "
        "(e.g. 'bloom', 'vignette_breathe').",
    )
    intro_effect_duration: float = Field(
        1.5,
        description="Duration of the intro effect in seconds (0.5–3.0 recommended)",
    )

    # Pacing Visual Effects (FEAT-023)
    pacing_drift_zoom: bool = Field(
        False,
        description="Slow 100→105% zoom over each segment (Ken Burns drift)",
    )
    pacing_crop_tighten: bool = Field(
        False,
        description="Zoom in over first 10s of each segment, caps at 105%",
    )
    pacing_saturation_pulse: bool = Field(
        False,
        description="Brief saturation surge on each detected beat",
    )

    # Advanced Beat-Synced Effects (FEAT-024)
    pacing_micro_jitters: bool = Field(
        False,
        description="Beat-synced 2-4px random shake for rhythmic punch",
    )
    pacing_light_leaks: bool = Field(
        False,
        description="Warm amber colour sweep on key beats (200ms flash)",
    )
    pacing_warm_wash: bool = Field(
        False,
        description="Brief amber flash at transition boundaries",
    )
    pacing_alternating_bokeh: bool = Field(
        False,
        description="Subtle background blur on alternating segments",
    )

    # Dry-Run Plan Mode (FEAT-026)
    dry_run: bool = Field(
        False,
        description="Run analysis and planning only — skip FFmpeg rendering",
    )

    # Genre Preset (FEAT-027)
    genre: Optional[str] = Field(
        None,
        description="Genre preset name (e.g. 'bachata', 'salsa', 'reggaeton'). "
        "Applies tuned defaults; explicit field values still override.",
    )

    # Static Zoom / Crop Factor (FEAT-029)
    zoom_factor: float = Field(
        1.0,
        description="Static zoom/crop factor. 1.0 = full frame, 0.88 = crop center 88% and scale up.",
    )

    # Per-Track Video Clip Pools (FEAT-030)
    per_track_clips: dict[str, str] = Field(
        default_factory=dict,
        description="Per-track clip folder mapping (filename → clip folder path). "
        "Example: {'track1.wav': 'clips/track1/', 'track2.wav': 'clips/track2/'}. "
        "If specified, overrides global --video-dir for that track's per-track video and Shorts. "
        "Global pool is used for mix and fallback.",
    )

    # Per-Track Video Style Filter (FEAT-031)
    per_track_styles: dict[str, str] = Field(
        default_factory=dict,
        description="Per-track video style mapping (filename → style name). "
        "Example: {'track1.wav': 'vintage', 'track2.wav': 'bw'}. "
        "If specified, overrides global video_style for that track's per-track video and Shorts. "
        "Valid styles: 'none', 'bw', 'vintage', 'warm', 'cool', 'golden'.",
    )

    @field_validator("per_track_styles", mode="after")
    @classmethod
    def validate_per_track_styles(cls, v: dict[str, str]) -> dict[str, str]:
        """Validate that all per-track styles are valid style names (FEAT-031)."""
        valid_styles = {"none", "bw", "vintage", "warm", "cool", "golden"}
        for track_filename, style in v.items():
            if style not in valid_styles:
                raise ValueError(
                    f"Invalid video style for {track_filename}: '{style}'. "
                    f"Valid options: {', '.join(sorted(valid_styles))}"
                )
        return v


class AudioMixConfig(BaseModel):
    """
    Configuration for mixing multiple audio tracks.
    """

    model_config = ConfigDict(extra="forbid")

    crossfade_duration_seconds: float = Field(
        2.0, description="Duration in seconds for the crossfades between tracks"
    )

    # Tempo synchronisation (Phase 1)
    tempo_sync: bool = Field(
        True,
        description="Automatically match each incoming track's BPM to the "
        "current mix tempo using FFmpeg atempo filter",
    )
    sync_threshold: float = Field(
        0.10,
        description="Maximum fractional tempo shift allowed before sync is "
        "skipped to avoid audio artifacts (0.10 = ±10%)",
    )

    # Phase 2 placeholder — not yet implemented
    tempo_ramp: bool = Field(
        False,
        description="[Phase 2 — not yet active] Gradually ramp tempo within "
        "the crossfade window rather than applying a fixed stretch",
    )
