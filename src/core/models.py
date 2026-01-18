"""
Domain models and DTOs for Bachata Beat-Story Sync.
"""
from typing import List, Optional
from pydantic import BaseModel, Field

class AudioAnalysisResult(BaseModel):
    """
    Result of audio analysis containing rhythm and structure data.
    """
    filename: str = Field(..., description="Name of the audio file")
    bpm: float = Field(..., description="Beats per minute")
    duration: float = Field(..., description="Duration in seconds")
    peaks: List[float] = Field(default_factory=list, description="Timestamps of high intensity moments")
    sections: List[str] = Field(default_factory=list, description="Musical sections (intro, verse, etc.)")

class VideoAnalysisResult(BaseModel):
    """
    Result of video analysis containing visual metrics.
    """
    path: str = Field(..., description="Full path to the video file")
    intensity_score: float = Field(..., description="Calculated visual intensity score (0-1)")
    duration: float = Field(..., description="Duration in seconds")
