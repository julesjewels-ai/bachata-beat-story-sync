"""
Data Transfer Objects (DTOs) for Bachata Beat-Story Sync.
These models define the strict contracts for data exchange between layers.
"""
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from src.core.validation import validate_file_path

SUPPORTED_VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv'}
SUPPORTED_AUDIO_EXTENSIONS = {'.wav', '.mp3'}


class VideoAnalysisInput(BaseModel):
    """
    Input model for video analysis validation.
    """
    file_path: str = Field(..., description="Path to the video file")

    @field_validator('file_path')
    @classmethod
    def validate_path(cls, v: str) -> str:
        return validate_file_path(v, SUPPORTED_VIDEO_EXTENSIONS)


class AudioAnalysisInput(BaseModel):
    """
    Input model for audio analysis validation.
    """
    file_path: str = Field(..., description="Path to the audio file")

    @field_validator('file_path')
    @classmethod
    def validate_path(cls, v: str) -> str:
        return validate_file_path(v, SUPPORTED_AUDIO_EXTENSIONS)


class AudioAnalysisResult(BaseModel):
    """
    Result model for audio analysis.
    """
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
