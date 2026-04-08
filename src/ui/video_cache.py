"""
Streamlit caching for video metadata and thumbnails.
"""

from __future__ import annotations

import streamlit as st
from src.core.app import BachataSyncEngine
from src.core.models import VideoAnalysisResult

@st.cache_resource
def get_cached_clips(directory: str) -> list[VideoAnalysisResult]:
    """
    Scans a directory for video clips and caches the results, including thumbnails.
    
    Args:
        directory: Path to the directory containing video clips.
        
    Returns:
        List of VideoAnalysisResult objects.
    """
    engine = BachataSyncEngine()
    # Note: We don't pass an observer here because it's cached and we want 
    # it to be silent on subsequent runs.
    return engine.scan_video_library(directory)
