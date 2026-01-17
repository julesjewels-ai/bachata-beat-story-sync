"""
Data Transfer Objects (DTOs) for the Bachata Beat-Story Sync application.
"""
from typing import Protocol
from pydantic import BaseModel, Field

class SimulationRequest(BaseModel):
    """
    Request model for running a simulation of the syncing process.
    """
    track_name: str = Field(..., min_length=1, description="Name of the mock track")
    duration: int = Field(180, ge=10, le=600, description="Duration in seconds")
    clip_count: int = Field(5, ge=1, le=50, description="Number of clips to simulate")

class ProgressCallback(Protocol):
    """
    Protocol for reporting progress updates.
    """
    def __call__(self, progress: float, message: str) -> None:
        """
        Args:
            progress: A float between 0.0 and 100.0.
            message: A description of the current step.
        """
        ...
