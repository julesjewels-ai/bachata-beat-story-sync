"""
Integration tests for the caching layer.
Verifies the end-to-end caching behavior of the video analysis pipeline.
"""
import pytest
import os
import json
import tempfile
import base64
from typing import Optional

from src.core.models import VideoAnalysisInput, VideoAnalysisResult
from src.core.interfaces import IVideoAnalyzer
from src.services.caching.backend import JsonFileCache
from src.services.analyzers import CachedVideoAnalyzer
from src.core.app import BachataSyncEngine


class MockVideoAnalyzer:
    """Mock analyzer to simulate video processing."""

    def __init__(self) -> None:
        self.call_count = 0

    def analyze(self, input_data: VideoAnalysisInput) -> VideoAnalysisResult:
        self.call_count += 1
        return VideoAnalysisResult(
            path=input_data.file_path,
            intensity_score=0.5,
            duration=10.0,
            thumbnail_data=b"fake_thumbnail_bytes"
        )


def test_caching_integration() -> None:
    """
    Verifies that the caching layer correctly intercepts calls,
    persists data, and prevents redundant processing.
    """
    # 1. Setup Environment
    # Create temp cache file (initially empty)
    fd_cache, cache_path = tempfile.mkstemp(suffix=".json")
    os.close(fd_cache)
    if os.path.exists(cache_path):
        os.remove(cache_path) # Ensure clean start

    # Create temp video file for validation
    fd_vid, video_path = tempfile.mkstemp(suffix=".mp4")
    os.write(fd_vid, b"fake video content")
    os.close(fd_vid)

    try:
        # 2. First Execution (Cache Miss)
        cache_backend = JsonFileCache(file_path=cache_path)
        inner_analyzer = MockVideoAnalyzer()
        cached_analyzer = CachedVideoAnalyzer(inner_analyzer, cache_backend)

        # Inject into Engine
        engine = BachataSyncEngine(video_analyzer=cached_analyzer)

        # Manually invoke helper to bypass directory scan logic
        # We simulate scanning a single file
        input_data = VideoAnalysisInput(file_path=video_path)
        result1 = cached_analyzer.analyze(input_data)

        assert result1.intensity_score == 0.5
        assert result1.thumbnail_data == b"fake_thumbnail_bytes"
        assert inner_analyzer.call_count == 1

        # Verify Cache Persistence
        assert os.path.exists(cache_path)
        with open(cache_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # There should be exactly one entry
            assert len(data) == 1
            entry = list(data.values())[0]

            assert entry['path'] == video_path
            assert entry['intensity_score'] == 0.5
            # Verify base64 encoding of thumbnail
            expected_b64 = base64.b64encode(b"fake_thumbnail_bytes").decode('utf-8')
            assert entry['thumbnail_data'] == expected_b64

        # 3. Second Execution (Cache Hit)
        # Create a FRESH engine/cache to simulate app restart
        # Re-using the same cache file path

        new_cache_backend = JsonFileCache(file_path=cache_path)
        # Reuse inner_analyzer to check call_count, or create new one and check count=0
        # Reusing is better to assert it wasn't called again on the same object
        new_cached_analyzer = CachedVideoAnalyzer(inner_analyzer, new_cache_backend)

        result2 = new_cached_analyzer.analyze(input_data)

        assert result2.intensity_score == 0.5
        assert result2.thumbnail_data == b"fake_thumbnail_bytes"
        # Call count should STILL be 1 (no new call)
        assert inner_analyzer.call_count == 1

    finally:
        # Cleanup
        if os.path.exists(cache_path):
            try:
                os.remove(cache_path)
            except OSError:
                pass
        if os.path.exists(video_path):
            try:
                os.remove(video_path)
            except OSError:
                pass
