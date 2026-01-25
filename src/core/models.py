"""
Data Transfer Objects (DTOs) for Bachata Beat-Story Sync.
These models define the strict contracts for data exchange between layers.
"""
from typing import List
from pydantic import BaseModel, Field, field_validator
from src.core.validation import validate_file_path
from src.core.constants import SUPPORTED_AUDIO_EXTENSIONS, SUPPORTED_VIDEO_EXTENSIONS

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
    duration: float = Field(..., description="Duration of the track in seconds")
    peaks: List[float] = Field(..., description="Timestamps of high intensity peaks")
    sections: List[str] = Field(..., description="Identified musical sections (e.g., intro, verse)")

class VideoAnalysisInput(BaseModel):
    """
    Input model for video analysis validation.
    """
    file_path: str = Field(..., description="Path to the video file")

    @field_validator('file_path')
    @classmethod
    def validate_path(cls, v: str) -> str:
        return validate_file_path(v, SUPPORTED_VIDEO_EXTENSIONS)

class VideoAnalysisResult(BaseModel):
    """
    Result model for video analysis.
    """
    path: str = Field(..., description="Absolute path to the video file")
    intensity_score: float = Field(..., description="Visual intensity score (0.0 to 1.0)")
    duration: float = Field(..., description="Duration of the video clip in seconds")
