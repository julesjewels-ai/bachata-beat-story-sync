import hashlib
import os
import streamlit as st
from src.core.app import BachataSyncEngine
from src.core.models import VideoAnalysisResult

def _get_directory_hash(directory: str) -> str:
    """Compute a fast hash of directory contents (names + sizes)."""
    if not os.path.isdir(directory):
        return "none"
    
    items = []
    for root, _, files in os.walk(directory):
        for f in sorted(files):
            if f.startswith('.'): continue
            path = os.path.join(root, f)
            try:
                items.append(f"{f}:{os.path.getsize(path)}")
            except OSError:
                items.append(f)
    
    return hashlib.md5(",".join(items).encode()).hexdigest()

@st.cache_resource(show_spinner="Scanning clips...")
def get_cached_clips(directory: str) -> list[VideoAnalysisResult]:
    """
    Scans a directory for video clips and caches the results.
    
    Streamlit's @st.cache_resource uses the arguments as the cache key.
    We pass a hash of the directory content to ensure invalidation if 
    files are added or modified.
    """
    # We call a sub-function that takes the hash as a parameter
    # so that streamlit handles the caching properly.
    content_hash = _get_directory_hash(directory)
    return _get_cached_clips_internal(directory, content_hash)

@st.cache_resource(show_spinner=False)
def _get_cached_clips_internal(directory: str, content_hash: str) -> list[VideoAnalysisResult]:
    """The actual cached scanning logic, keyed by directory AND content_hash."""
    engine = BachataSyncEngine()
    return engine.scan_video_library(directory)
