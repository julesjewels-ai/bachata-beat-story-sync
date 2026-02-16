"""
Integration test for caching pipeline.
"""
import pytest
import os
import shutil
import base64
from unittest.mock import MagicMock
from src.core.models import VideoAnalysisInput, VideoAnalysisResult
from src.services.caching.backend import JsonFileCache
from src.services.caching.analyzers import CachedVideoAnalyzer
from src.core.app import BachataSyncEngine


@pytest.fixture
def cache_backend(tmp_path):
    cache_path = tmp_path / "integration_cache.json"
    return JsonFileCache(str(cache_path))


@pytest.fixture
def mock_real_analyzer():
    analyzer = MagicMock()
    # Mock return value for analysis
    analyzer.analyze.return_value = VideoAnalysisResult(
        path="video.mp4",
        intensity_score=0.8,
        duration=20.0,
        thumbnail_data=b"thumb"
    )
    return analyzer


def test_engine_uses_cache(cache_backend, mock_real_analyzer, tmp_path):
    """
    Test that the BachataSyncEngine correctly utilizes the CachedVideoAnalyzer
    to cache results and avoid re-processing.
    """
    # Create a dummy video file in tmp_path
    video_path = tmp_path / "video.mp4"
    video_path.write_text("dummy content")
    str_path = str(video_path)

    # Setup analyzer result to match the dummy file path
    mock_real_analyzer.analyze.return_value = VideoAnalysisResult(
        path=str_path,
        intensity_score=0.8,
        duration=20.0,
        thumbnail_data=b"thumb"
    )

    # Setup cached analyzer and inject into engine
    cached_analyzer = CachedVideoAnalyzer(mock_real_analyzer, cache_backend)
    engine = BachataSyncEngine(video_analyzer=cached_analyzer)

    # Mock _collect_video_files so we don't rely on os.walk
    # We force it to return our dummy file
    # Note: We patch the method on the INSTANCE
    engine._collect_video_files = MagicMock(return_value=[str_path])

    # 1. First Run: Should be a cache MISS
    results1 = engine.scan_video_library(str(tmp_path))

    assert len(results1) == 1
    assert results1[0].intensity_score == 0.8
    # Real analyzer should have been called once
    mock_real_analyzer.analyze.assert_called_once()

    # Verify cache key generation and persistence
    cache_key = cached_analyzer._generate_cache_key(str_path)
    assert cache_backend.get(cache_key) is not None

    # 2. Second Run: Should be a cache HIT
    results2 = engine.scan_video_library(str(tmp_path))

    assert len(results2) == 1
    # Real analyzer call count should remain 1
    mock_real_analyzer.analyze.assert_called_once()
