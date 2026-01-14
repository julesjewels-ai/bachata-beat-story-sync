"""
Core business logic for Bachata Beat-Story Sync.
Handles audio analysis logic and video synchronization algorithms.
"""
import logging
import os
from typing import List, Dict, Any, Optional
import re
from pydantic import ValidationError, BaseModel, Field, field_validator
from src.core.video_analyzer import VideoAnalyzer, VideoAnalysisInput, SUPPORTED_VIDEO_EXTENSIONS

logger = logging.getLogger(__name__)


class StoryGenerationInput(BaseModel):
    """
    Input model for validating story generation output.
    """
    output_path: str = Field(..., description="Path for the output video file")

    @field_validator('output_path')
    @classmethod
    def validate_output_path(cls, v: str) -> str:
        # Enforce strict filename characters (no directory separators allowed to prevent traversal)
        if not re.match(r"^[\w\-. ]+$", v):
            raise ValueError(
                "Invalid characters in filename. Allowed: A-Z, a-z, 0-9, -, ., space"
            )

        # Enforce .mp4 extension
        if not v.lower().endswith('.mp4'):
            raise ValueError("Output file must have .mp4 extension")

        return v


class BachataSyncEngine:
    """
    The main engine responsible for analyzing audio features and
    mapping them to video segments based on intensity.
    """

    def __init__(self) -> None:
        self.supported_audio_ext = ['.wav', '.mp3']
        # Use the centralized constant for supported video extensions
        self.supported_video_ext = SUPPORTED_VIDEO_EXTENSIONS
        self.video_analyzer = VideoAnalyzer()

    def analyze_audio(self, file_path: str) -> Dict[str, Any]:
        """
        Analyzes a Bachata track to find BPM, beats, and intensity drops.
        
        In a real implementation, this would use librosa or essentialia.
        For the scaffold, it mimics analysis results.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Audio file not found: {file_path}")
        
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
                _, ext = os.path.splitext(file)
                if ext.lower() in self.supported_video_ext:
                    video_path = os.path.join(root, file)
                    try:
                        input_data = VideoAnalysisInput(file_path=video_path)
                        analysis_result = self.video_analyzer.analyze(input_data)
                        clips.append(analysis_result)
                    except (ValidationError, ValueError) as e:
                        logger.warning(f"Skipping invalid video {video_path}: {e}")
                    except Exception as e:
                        logger.error(f"Error processing {video_path}: {e}")
        return clips

    def generate_story(self, audio_data: Dict[str, Any], 
                       video_clips: List[Dict[str, Any]], 
                       output_path: str) -> str:
        """
        Syncs clips to audio data and exports the timeline.
        """
        # Security: Validate output path
        validated_input = StoryGenerationInput(output_path=output_path)
        safe_path = validated_input.output_path

        # Logic to match audio['peaks'] with video['intensity_score']
        logger.info(f"Synthesizing {len(video_clips)} clips against {audio_data['bpm']} BPM audio...")
        
        # Mock export process
        with open(safe_path, 'w') as f:
            f.write("Mock Video Content")
        
        return safe_path

    def run_simulation(self) -> None:
        """
        Runs a simulation for testing or demo purposes without real files.
        """
        logger.info("--- SIMULATION MODE ---")
        mock_audio = {"bpm": 130, "peaks": [10, 20]}
        logger.info(f"Simulated Audio Analysis: {mock_audio}")
        logger.info("Simulated Video Matching: Match Found at index 0")
        logger.info("--- SIMULATION COMPLETE ---")
