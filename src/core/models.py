"""
Data Transfer Objects (DTOs) for Bachata Beat-Story Sync.
These models define the strict contracts for data exchange between layers.
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class AudioSection(BaseModel):
    """
    Represents a detected musical section within the track.
    """
    start_time: float = Field(..., description="Start time of the section in seconds")
    end_time: float = Field(..., description="End time of the section in seconds")
    duration: float = Field(..., description="Duration of the section in seconds")
    label: str = Field(..., description="Descriptive label (e.g., 'verse', 'chorus')")


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
    sections: List[AudioSection] = Field(
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
