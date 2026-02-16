"""
Data Transfer Objects (DTOs) for Bachata Beat-Story Sync.
These models define the strict contracts for data exchange between layers.
"""
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from src.core.validation import validate_file_path

SUPPORTED_VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv'}
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


class VideoAnalysisInput(BaseModel):
    """
    Input model for video analysis validation.
    """
    file_path: str = Field(..., description="Path to the video file")

    @field_validator('file_path')
    @classmethod
    def validate_path(cls, v: str) -> str:
        return validate_file_path(v, SUPPORTED_VIDEO_EXTENSIONS)


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
    sections: List[str] = Field(
        ..., description="Identified musical sections (e.g., intro, verse)"
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
