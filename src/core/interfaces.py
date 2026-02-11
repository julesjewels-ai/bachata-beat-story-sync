"""
Core interfaces and protocols for Bachata Beat-Story Sync.
"""
from typing import Protocol, Optional, Any
from src.core.models import (
    VideoAnalysisInput, VideoAnalysisResult,
    AudioAnalysisInput, AudioAnalysisResult
)


class ProgressObserver(Protocol):
    """
    Protocol for objects that observe progress of long-running operations.
    """
    def on_progress(self, current: int, total: int, message: str = "") -> None:
        """
        Called to update progress.

        Args:
            current: The current number of items processed.
            total: The total number of items to process.
            message: A descriptive message about the current operation.
        """
        ...


class IVideoAnalyzer(Protocol):
    """
    Interface for video analysis services.
    """
    def analyze(self, input_data: VideoAnalysisInput) -> VideoAnalysisResult:
        """Analyzes a video file."""
        ...


class IAudioAnalyzer(Protocol):
    """
    Interface for audio analysis services.
    """
    def analyze(self, input_data: AudioAnalysisInput) -> AudioAnalysisResult:
        """Analyzes an audio file."""
        ...


class CacheBackend(Protocol):
    """
    Interface for caching backends.
    """
    def get(self, key: str) -> Optional[Any]:
        """Retrieves a value from the cache."""
        ...

    def set(self, key: str, value: Any) -> None:
        """Sets a value in the cache."""
        ...
