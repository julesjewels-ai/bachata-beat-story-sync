"""
Core business logic for Bachata Beat-Story Sync.
Handles audio analysis logic and video synchronization algorithms.
"""
import logging
import os
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator, ValidationError
from src.core.video_analyzer import VideoAnalyzer, VideoAnalysisInput, SUPPORTED_VIDEO_EXTENSIONS
from src.core.validation import validate_file_path

logger = logging.getLogger(__name__)

SUPPORTED_AUDIO_EXTENSIONS = {'.wav', '.mp3'}

class AudioAnalysisInput(BaseModel):
    """
    Input model for audio analysis validation.
    """
    file_path: str = Field(..., description="Path to the audio file")

    @field_validator('file_path')
    @classmethod
    def validate_path(cls, v: str) -> str:
        return validate_file_path(v, SUPPORTED_AUDIO_EXTENSIONS)

class BachataSyncEngine:
    """
    The main engine responsible for analyzing audio features and
    mapping them to video segments based on intensity.
    """

    def __init__(self) -> None:
        self.supported_audio_ext = list(SUPPORTED_AUDIO_EXTENSIONS)
        # Use the centralized constant for supported video extensions
        self.supported_video_ext = SUPPORTED_VIDEO_EXTENSIONS
        self.video_analyzer = VideoAnalyzer()

    def analyze_audio(self, input_data: AudioAnalysisInput) -> Dict[str, Any]:
        """
        Analyzes a Bachata track to find BPM, beats, and intensity drops.
        
        In a real implementation, this would use librosa or essentialia.
        For the scaffold, it mimics analysis results.
        """
        file_path = input_data.file_path
        
        # Mock logic for MVP scaffold
        # Real logic: y, sr = librosa.load(file_path); onset_env = ...
        return {
            "filename": os.path.basename(file_path),
            "bpm": 128,  # Typical Bachata tempo
            "duration": 180.0,
            "peaks": [15.5, 45.2, 90.0, 120.5], # Timestamps of high intensity
            "sections": ["intro", "verse", "chorus", "break", "outro"]
        }

    def scan_video_library(self, directory: str) -> List[Dict[str, Any]]:
        """
        Scans a directory for video files and assigns a 'visual intensity' score.
        """
        if not os.path.exists(directory):
             raise FileNotFoundError(f"Video directory not found: {directory}")

        clips = []
        for root, _, files in os.walk(directory):
            for file in files:
                if result := self._process_video_file(root, file):
                    clips.append(result)
        return clips

    def _process_video_file(self, root: str, filename: str) -> Optional[Dict[str, Any]]:
        """Helper to process a single video file."""
        _, ext = os.path.splitext(filename)
        if ext.lower() not in self.supported_video_ext:
            return None

        video_path = os.path.join(root, filename)
        try:
            input_data = VideoAnalysisInput(file_path=video_path)
            return self.video_analyzer.analyze(input_data)
        except (ValidationError, ValueError) as e:
            logger.warning(f"Skipping invalid video {video_path}: {e}")
        except Exception as e:
            logger.error(f"Error processing {video_path}: {e}")

        return None

    def generate_story(self, audio_data: Dict[str, Any], 
                       video_clips: List[Dict[str, Any]], 
                       output_path: str) -> str:
        """
        Syncs clips to audio data and exports the timeline.
        """
        # Logic to match audio['peaks'] with video['intensity_score']
        logger.info(f"Synthesizing {len(video_clips)} clips against {audio_data['bpm']} BPM audio...")
        
        # Mock export process
        with open(output_path, 'w') as f:
            f.write("Mock Video Content")
        
        return output_path
