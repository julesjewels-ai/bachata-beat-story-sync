"""
Data Transfer Objects (DTOs) for Bachata Beat-Story Sync.
These models define the strict contracts for data exchange between layers.
"""
import base64
from typing import List, Optional, Any
from pydantic import BaseModel, Field, field_serializer, field_validator


class AudioAnalysisResult(BaseModel):
    """
    Result model for audio analysis.
    """
    file_path: str = Field(..., description="Absolute path to the audio file")
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

    @field_serializer('thumbnail_data')
    def serialize_thumbnail(self, v: Optional[bytes], _info: Any) -> Optional[str]:
        if v is None:
            return None
        return base64.b64encode(v).decode('utf-8')

    @field_validator('thumbnail_data', mode='before')
    @classmethod
    def validate_thumbnail(cls, v: Any) -> Optional[bytes]:
        if isinstance(v, str):
            return base64.b64decode(v)
        return v
