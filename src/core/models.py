"""
Data Transfer Objects (DTOs) for audio and video analysis results.
"""
from typing import List
from pydantic import BaseModel

class AudioAnalysisResult(BaseModel):
    """Result model for audio analysis."""
    filename: str
    bpm: float
    duration: float
    peaks: List[float]
    sections: List[str]

class VideoAnalysisResult(BaseModel):
    """Result model for video analysis."""
    path: str
    intensity_score: float
    duration: float
