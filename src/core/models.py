"""
Data Transfer Objects (DTOs) for Bachata Beat-Story Sync.
"""
from typing import List
from pydantic import BaseModel, Field

class AudioAnalysisResult(BaseModel):
    """
    Result model for audio analysis.
    """
    filename: str = Field(..., description="Name of the audio file")
    bpm: float = Field(..., description="Beats per minute")
    duration: float = Field(..., description="Duration in seconds")
    peaks: List[float] = Field(..., description="List of timestamps for emotional peaks")
    sections: List[str] = Field(..., description="List of musical sections (e.g., intro, verse)")

class VideoAnalysisResult(BaseModel):
    """
    Result model for video analysis.
    """
    path: str = Field(..., description="Path to the video file")
    intensity_score: float = Field(..., description="Visual intensity score (normalized 0-1)")
    duration: float = Field(..., description="Duration in seconds")
