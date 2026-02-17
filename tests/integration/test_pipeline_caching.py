"""
Integration tests for the caching pipeline.
"""
import os
import pytest
from unittest.mock import MagicMock
from src.core.app import BachataSyncEngine
from src.core.models import VideoAnalysisResult
from src.core.video_analyzer import VideoAnalysisInput
from src.services.caching.backend import JsonFileCache
from src.services.caching.service import CachedVideoAnalyzer


@pytest.fixture
def temp_cache_file(tmp_path):
    return str(tmp_path / "integration_cache.json")


def test_pipeline_caching_integration(temp_cache_file, tmp_path):
    # Setup a dummy video file in the temp directory
    video_file = tmp_path / "video.mp4"
    video_file.write_text("fake video content", encoding="utf-8")
    video_path = str(video_file)

    # Mock the base analyzer
    mock_base_analyzer = MagicMock()
    expected_result = VideoAnalysisResult(
        path=video_path,
        intensity_score=0.9,
        duration=10.0,
        thumbnail_data=b"fake_thumb"
    )
    mock_base_analyzer.analyze.return_value = expected_result

    # Setup the caching stack
    cache_backend = JsonFileCache(temp_cache_file)
    cached_analyzer = CachedVideoAnalyzer(mock_base_analyzer, cache_backend)

    # Setup engine with injected dependency
    engine = BachataSyncEngine(video_analyzer=cached_analyzer)

    # 1. First Run: Cache Miss
    # _process_video_file calls analyze internally
    result1 = engine._process_video_file(video_path)

    assert result1 is not None
    assert result1.intensity_score == 0.9
    mock_base_analyzer.analyze.assert_called_once()

    # Verify cache file exists
    assert os.path.exists(temp_cache_file)

    # Reset mock to verify it's not called again
    mock_base_analyzer.analyze.reset_mock()

    # 2. Second Run: Cache Hit
    # Re-instantiate engine/cache to simulate fresh run but same file
    cache_backend_2 = JsonFileCache(temp_cache_file)
    cached_analyzer_2 = CachedVideoAnalyzer(mock_base_analyzer, cache_backend_2)
    engine_2 = BachataSyncEngine(video_analyzer=cached_analyzer_2)

    result2 = engine_2._process_video_file(video_path)

    assert result2 is not None
    assert result2.intensity_score == 0.9
    assert result2.thumbnail_data == b"fake_thumb"

    # Crucial: base analyzer should NOT be called
    mock_base_analyzer.analyze.assert_not_called()
