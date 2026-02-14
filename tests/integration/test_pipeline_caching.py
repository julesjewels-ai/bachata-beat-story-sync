"""
Integration test for caching pipeline.
"""
import os
import pytest
from unittest.mock import MagicMock, patch
from src.core.app import BachataSyncEngine
from src.core.models import VideoAnalysisResult
from src.services.caching.backend import JsonFileCache
from src.services.analyzers.cached_video_analyzer import CachedVideoAnalyzer

DUMMY_VIDEO = "test_video.mp4"
DUMMY_DIR = "dummy_dir"
CACHE_FILE = ".bachata_cache_test.json"

@pytest.fixture
def setup_environment():
    """Sets up dummy video and cleans cache."""
    # Create dummy dir
    if not os.path.exists(DUMMY_DIR):
        os.makedirs(DUMMY_DIR)

    # Create dummy video
    with open(DUMMY_VIDEO, "w") as f:
        f.write("fake video content")

    # Remove cache if exists
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)

    yield

    # Cleanup
    if os.path.exists(DUMMY_VIDEO):
        os.remove(DUMMY_VIDEO)
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)
    if os.path.exists(DUMMY_DIR):
        os.rmdir(DUMMY_DIR)

def test_video_analysis_caching(setup_environment):
    """
    Verifies that video analysis results are cached and reused.
    """
    # 1. Create Mock Analyzer
    mock_analyzer = MagicMock()
    # Mock result
    expected_result = VideoAnalysisResult(
        path=os.path.abspath(DUMMY_VIDEO),
        intensity_score=0.8,
        duration=15.0,
        thumbnail_data=b"\x00\x01\x02"  # Binary data
    )
    mock_analyzer.analyze.return_value = expected_result

    # 2. Setup Caching Components
    cache = JsonFileCache(file_path=CACHE_FILE)
    cached_analyzer = CachedVideoAnalyzer(mock_analyzer, cache)

    # 3. Setup Engine
    engine = BachataSyncEngine(video_analyzer=cached_analyzer)

    # 4. Mock file collection to return our dummy video
    # We patch _collect_video_files to avoid recursive directory scanning
    with patch.object(engine, '_collect_video_files', return_value=[DUMMY_VIDEO]):

        # Run 1: Should trigger analysis (Cache Miss)
        results1 = engine.scan_video_library("dummy_dir")

        assert len(results1) == 1
        assert results1[0].intensity_score == 0.8
        assert mock_analyzer.analyze.call_count == 1

        # Run 2: Should use cache (Cache Hit)
        results2 = engine.scan_video_library("dummy_dir")

        assert len(results2) == 1
        assert results2[0].intensity_score == 0.8
        assert results2[0].thumbnail_data == b"\x00\x01\x02"
        # Call count should remain 1, proving inner analyzer was skipped
        assert mock_analyzer.analyze.call_count == 1
