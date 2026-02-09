"""
Integration tests for the caching layer.
"""
import os
import pytest
from unittest.mock import MagicMock
from src.core.models import VideoAnalysisResult
from src.services.caching import JsonFileCache
from src.services.analyzers import CachedVideoAnalyzer
from src.core.video_analyzer import VideoAnalysisInput
from src.core.app import BachataSyncEngine

@pytest.fixture
def mock_video_file(tmp_path):
    """Creates a dummy video file."""
    p = tmp_path / "test_video.mp4"
    p.touch()
    return str(p)

@pytest.fixture
def mock_result(mock_video_file):
    # Use real binary data to test robustness
    return VideoAnalysisResult(
        path=mock_video_file,
        intensity_score=0.8,
        duration=12.5,
        thumbnail_data=b"\xFF\x00\xFF\x89PNG\r\n\x1a\n"
    )

def test_caching_behavior(tmp_path, mock_video_file, mock_result):
    """Test that the caching layer works as expected."""
    cache_file = tmp_path / "cache.json"

    # 1. Setup inner analyzer mock
    inner_analyzer = MagicMock()
    inner_analyzer.analyze.return_value = mock_result

    # 2. Setup cached analyzer
    cache = JsonFileCache(str(cache_file))
    cached_analyzer = CachedVideoAnalyzer(inner_analyzer, cache)

    input_data = VideoAnalysisInput(file_path=mock_video_file)

    # 3. First run: Cache miss
    result1 = cached_analyzer.analyze(input_data)

    assert result1 == mock_result
    inner_analyzer.analyze.assert_called_once()

    # 4. Verify cache file exists
    assert cache_file.exists()

    # 5. Second run: Cache hit (same file, same mtime)
    inner_analyzer.reset_mock()

    result2 = cached_analyzer.analyze(input_data)
    assert result2 == mock_result
    inner_analyzer.analyze.assert_not_called()

    # 6. Verify binary data preservation (exact match)
    assert result2.thumbnail_data == b"\xFF\x00\xFF\x89PNG\r\n\x1a\n"

    # 7. Invalidation: Touch file (update mtime)
    st = os.stat(mock_video_file)
    new_mtime = st.st_mtime + 100
    os.utime(mock_video_file, (st.st_atime, new_mtime))

    # Re-setup inner mock because it was reset
    inner_analyzer.analyze.return_value = mock_result

    result3 = cached_analyzer.analyze(input_data)
    assert result3 == mock_result
    inner_analyzer.analyze.assert_called_once()

def test_engine_wiring():
    """Test that BachataSyncEngine wires up caching by default."""
    engine = BachataSyncEngine()
    # Check if video_analyzer is CachedVideoAnalyzer
    from src.services.analyzers import CachedVideoAnalyzer
    assert isinstance(engine.video_analyzer, CachedVideoAnalyzer)

    engine_no_cache = BachataSyncEngine(use_cache=False)
    assert not isinstance(engine_no_cache.video_analyzer, CachedVideoAnalyzer)
