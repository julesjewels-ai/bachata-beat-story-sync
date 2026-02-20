"""
Integration tests for the caching pipeline.
"""
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.core.app import BachataSyncEngine
from src.core.models import VideoAnalysisResult
from src.core.video_analyzer import VideoAnalysisInput
from src.services.caching.backend import JsonFileCache
from src.services.caching.video import CachedVideoAnalyzer


@pytest.fixture
def temp_dirs():
    """Create temp directories for cache and video library."""
    root = tempfile.mkdtemp()
    cache_dir = os.path.join(root, "cache")
    video_dir = os.path.join(root, "videos")
    os.makedirs(cache_dir, exist_ok=True)
    os.makedirs(video_dir, exist_ok=True)
    try:
        yield cache_dir, video_dir
    finally:
        shutil.rmtree(root)


def test_pipeline_caching_integration(temp_dirs):
    """
    Test the full pipeline integration:
    Engine -> CachedVideoAnalyzer -> JsonFileCache -> InnerAnalyzer
    """
    cache_dir, video_dir = temp_dirs

    # Create a dummy video file in the library directory
    video_path = os.path.join(video_dir, "test_clip.mp4")
    Path(video_path).touch()

    # 1. Setup Dependencies
    cache_backend = JsonFileCache(cache_dir)

    # Mock the heavy/expensive inner analyzer
    mock_inner_analyzer = Mock()
    expected_result = VideoAnalysisResult(
        path=video_path,
        intensity_score=0.75,
        duration=12.0,
        thumbnail_data=None
    )

    # Configure mock to return expected result when called
    mock_inner_analyzer.analyze.return_value = expected_result

    # 2. Wire Dependencies
    cached_analyzer = CachedVideoAnalyzer(
        inner=mock_inner_analyzer,
        cache=cache_backend
    )

    engine = BachataSyncEngine(video_analyzer=cached_analyzer)

    # 3. First Pass: Cache Miss
    # Should scan the library, find the clip, call analyze (miss), cache it.
    results1 = engine.scan_video_library(video_dir)

    assert len(results1) == 1
    assert results1[0].path == video_path
    assert results1[0].intensity_score == 0.75

    # Verify inner analyzer was called once
    mock_inner_analyzer.analyze.assert_called_once()

    # Verify cache file created
    cache_files = list(Path(cache_dir).glob("*.json"))
    assert len(cache_files) == 1

    # 4. Second Pass: Cache Hit
    # Reset mock to ensure no new calls to inner logic
    mock_inner_analyzer.reset_mock()

    results2 = engine.scan_video_library(video_dir)

    assert len(results2) == 1
    assert results2[0].path == video_path
    assert results2[0].intensity_score == 0.75

    # Verify inner analyzer was NOT called (served from cache)
    mock_inner_analyzer.analyze.assert_not_called()
