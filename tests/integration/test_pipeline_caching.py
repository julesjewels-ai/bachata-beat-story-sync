import os
import shutil
import tempfile
import pytest
from unittest.mock import MagicMock
from src.core.models import VideoAnalysisResult, VideoAnalysisInput
from src.services.caching.backend import JsonFileCache
from src.services.analyzers.cached_video_analyzer import CachedVideoAnalyzer

class MockVideoAnalyzer:
    def __init__(self):
        self.call_count = 0

    def analyze(self, input_data: VideoAnalysisInput) -> VideoAnalysisResult:
        self.call_count += 1
        return VideoAnalysisResult(
            path=input_data.file_path,
            intensity_score=0.8,
            duration=10.0,
            thumbnail_data=b"fake_thumbnail"
        )

def test_cached_video_analyzer_integration():
    # Setup temp cache dir
    temp_dir = tempfile.mkdtemp()

    try:
        # Create dependencies
        base_analyzer = MockVideoAnalyzer()
        cache = JsonFileCache(cache_dir=temp_dir)
        cached_analyzer = CachedVideoAnalyzer(base_analyzer, cache)

        # Create a dummy file for analysis input (needed for validation?)
        # VideoAnalysisInput validates the path exists and has extension.
        # I need to create a dummy video file.
        dummy_video = os.path.join(temp_dir, "test.mp4")
        with open(dummy_video, "wb") as f:
            f.write(b"dummy content")

        input_data = VideoAnalysisInput(file_path=dummy_video)

        # First call: Should hit the analyzer
        result1 = cached_analyzer.analyze(input_data)
        assert base_analyzer.call_count == 1
        assert result1.path == dummy_video
        assert result1.thumbnail_data == b"fake_thumbnail"

        # Second call: Should hit the cache (analyzer count stays 1)
        result2 = cached_analyzer.analyze(input_data)
        assert base_analyzer.call_count == 1
        assert result2.path == dummy_video
        assert result2.thumbnail_data == b"fake_thumbnail"

        # Verify cache file exists
        # We don't know the exact hash, but we can check if a json file exists
        json_files = [f for f in os.listdir(temp_dir) if f.endswith(".json")]
        assert len(json_files) == 1

    finally:
        shutil.rmtree(temp_dir)
