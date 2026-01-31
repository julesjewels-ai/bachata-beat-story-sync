"""
Data Transfer Objects (DTOs) for Bachata Beat-Story Sync.
These models define the strict contracts for data exchange between layers.
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class AudioAnalysisResult(BaseModel):
    """
    Result model for audio analysis.
    """
    filename: str = Field(..., description="Name of the audio file")
    bpm: float = Field(
        ..., description="Beats per minute of the track"
    )
    duration: float = Field(
        ..., description="Duration of the track in seconds"
    )
    peaks: List[float] = Field(
        ..., description="Timestamps of high intensity peaks"
    )
    sections: List[str] = Field(
        ..., description="Identified musical sections (e.g., intro, verse)"
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
        None, description="JPEG encoded thumbnail image bytes"
    )
