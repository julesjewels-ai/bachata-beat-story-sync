"""
Unit tests for the CachedVideoAnalyzer service.
"""
import pytest
from unittest.mock import MagicMock, patch
from src.core.video_analyzer import VideoAnalysisInput
from src.core.models import VideoAnalysisResult
from src.services.caching.service import CachedVideoAnalyzer


@pytest.fixture
def mock_analyzer():
    """Fixture for a mock IVideoAnalyzer."""
    return MagicMock()


@pytest.fixture
def mock_cache():
    """Fixture for a mock CacheBackend."""
    return MagicMock()


@pytest.fixture
def cached_analyzer(mock_analyzer, mock_cache):
    """Fixture for the CachedVideoAnalyzer instance."""
    return CachedVideoAnalyzer(mock_analyzer, mock_cache)


@patch("src.core.video_analyzer.validate_file_path", return_value="dummy.mp4")
@patch("os.stat")
def test_analyze_cache_hit(mock_stat, mock_validate, cached_analyzer, mock_cache, mock_analyzer):
    """Test that a cache hit returns the cached result without calling the analyzer."""
    mock_stat.return_value.st_size = 1024
    mock_stat.return_value.st_mtime = 1234567890

    # Setup cache hit
    mock_cache.get.return_value = {
        "path": "dummy.mp4",
        "intensity_score": 0.8,
        "duration": 10.0,
        "thumbnail_data": None
    }

    input_data = VideoAnalysisInput(file_path="dummy.mp4")
    result = cached_analyzer.analyze(input_data)

    assert result.path == "dummy.mp4"
    assert result.intensity_score == 0.8
    # Ensure the real analyzer was NOT called
    mock_analyzer.analyze.assert_not_called()
    # Ensure cache was checked
    mock_cache.get.assert_called_once()


@patch("src.core.video_analyzer.validate_file_path", return_value="dummy.mp4")
@patch("os.stat")
def test_analyze_cache_miss(mock_stat, mock_validate, cached_analyzer, mock_cache, mock_analyzer):
    """Test that a cache miss calls the analyzer and stores the result."""
    mock_stat.return_value.st_size = 1024
    mock_stat.return_value.st_mtime = 1234567890

    # Setup cache miss
    mock_cache.get.return_value = None

    expected_result = VideoAnalysisResult(
        path="dummy.mp4",
        intensity_score=0.5,
        duration=5.0,
        thumbnail_data=None
    )
    mock_analyzer.analyze.return_value = expected_result

    input_data = VideoAnalysisInput(file_path="dummy.mp4")
    result = cached_analyzer.analyze(input_data)

    assert result == expected_result
    # Ensure analyzer WAS called
    mock_analyzer.analyze.assert_called_once_with(input_data)
    # Ensure result was stored in cache
    mock_cache.set.assert_called_once()


@patch("src.core.video_analyzer.validate_file_path", return_value="dummy.mp4")
@patch("os.stat", side_effect=OSError)
def test_analyze_os_error(mock_stat, mock_validate, cached_analyzer, mock_cache, mock_analyzer):
    """Test behavior when file metadata cannot be accessed (no caching)."""
    expected_result = VideoAnalysisResult(
        path="dummy.mp4",
        intensity_score=0.5,
        duration=5.0,
        thumbnail_data=None
    )
    mock_analyzer.analyze.return_value = expected_result

    input_data = VideoAnalysisInput(file_path="dummy.mp4")
    result = cached_analyzer.analyze(input_data)

    assert result == expected_result
    mock_analyzer.analyze.assert_called_once()
    # Cache should not be touched if stat fails
    mock_cache.get.assert_not_called()
    mock_cache.set.assert_not_called()
