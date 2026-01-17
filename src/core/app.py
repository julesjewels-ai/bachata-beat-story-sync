"""
Core business logic for Bachata Beat-Story Sync.
Handles audio analysis logic and video synchronization algorithms.
"""
import logging
import os
from typing import List, Dict, Any, Optional, Callable
import time
import random
from pydantic import BaseModel, Field, field_validator, ValidationError
from src.core.video_analyzer import VideoAnalyzer, VideoAnalysisInput, SUPPORTED_VIDEO_EXTENSIONS
from src.core.models import SimulationRequest

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
        # Security: Prevent path traversal
        if ".." in v:
            raise ValueError("Path traversal attempt detected")

        if not os.path.exists(v):
            raise ValueError(f"Audio file not found: {v}")

        # Security: Allowlist extensions
        _, ext = os.path.splitext(v)
        if ext.lower() not in SUPPORTED_AUDIO_EXTENSIONS:
            raise ValueError(f"Unsupported audio extension: {ext}")
        return v

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

    def run_simulation(self, request: SimulationRequest, on_progress: Optional[Callable[[float, str], None]] = None) -> Dict[str, Any]:
        """
        Runs a simulation of the syncing process.

        Args:
            request: Configuration for the simulation.
            on_progress: Optional callback for progress reporting.

        Returns:
            A dictionary containing the simulation results.
        """
        track_name = request.track_name
        duration = request.duration
        clip_count = request.clip_count

        steps = [
            ("Analyzing audio track...", 10),
            ("Detecting beats...", 20),
            ("Identifying emotional peaks...", 30),
            ("Scanning video library...", 50),
            ("Calculating visual intensity...", 70),
            ("Matching beats to clips...", 85),
            ("Rendering final output...", 100)
        ]

        if on_progress:
            on_progress(0, f"Starting simulation for '{track_name}' ({duration}s)...")

        for message, progress in steps:
            time.sleep(random.uniform(0.1, 0.3))  # Simulate work
            if on_progress:
                on_progress(float(progress), message)

        result = {
            "status": "success",
            "audio_file": track_name,
            "clips_used": clip_count,
            "bpm": random.randint(120, 140),
            "output_path": "simulation_output.mp4"
        }

        if on_progress:
            on_progress(100.0, "Simulation complete!")

        return result
