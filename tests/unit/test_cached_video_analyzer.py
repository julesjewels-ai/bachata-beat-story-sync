"""
Tests for the CachedVideoAnalyzer service.
"""
import pytest
import base64
from unittest.mock import MagicMock
from src.core.models import VideoAnalysisInput, VideoAnalysisResult
from src.services.caching.analyzers import CachedVideoAnalyzer


@pytest.fixture
def mock_real_analyzer():
    analyzer = MagicMock()
    # Mock return value for a cache miss
    analyzer.analyze.return_value = VideoAnalysisResult(
        path="test.mp4",
        intensity_score=0.75,
        duration=15.0,
        thumbnail_data=b"real_thumb"
    )
    return analyzer


@pytest.fixture
def mock_cache():
    return MagicMock()


from unittest.mock import patch

@pytest.fixture
def analyzer_service(mock_real_analyzer, mock_cache):
    return CachedVideoAnalyzer(mock_real_analyzer, mock_cache)


@patch("src.services.caching.analyzers.os.stat")
@patch("src.core.validation.os.path.exists", return_value=True)
def test_analyze_cache_miss(
    mock_exists, mock_stat, analyzer_service, mock_real_analyzer, mock_cache
):
    """Test that a cache miss calls the real analyzer and updates the cache."""
    # Mock stat
    mock_stat.return_value.st_size = 100
    mock_stat.return_value.st_mtime = 1000.0

    # Simulate cache miss
    mock_cache.get.return_value = None

    input_data = VideoAnalysisInput(file_path="test.mp4")
    result = analyzer_service.analyze(input_data)

    # Should call real analyzer
    mock_real_analyzer.analyze.assert_called_once_with(input_data)
    assert result.intensity_score == 0.75

    # Should cache the result
    mock_cache.set.assert_called_once()
    args, _ = mock_cache.set.call_args
    key, val = args

    assert val["path"] == "test.mp4"
    # Thumbnail should be Base64 encoded in cache
    expected_b64 = base64.b64encode(b"real_thumb").decode('utf-8')
    assert val["thumbnail_data"] == expected_b64


@patch("src.services.caching.analyzers.os.stat")
@patch("src.core.validation.os.path.exists", return_value=True)
def test_analyze_cache_hit(
    mock_exists, mock_stat, analyzer_service, mock_real_analyzer, mock_cache
):
    """Test that a cache hit returns cached data without calling real analyzer."""
    # Mock stat
    mock_stat.return_value.st_size = 100
    mock_stat.return_value.st_mtime = 1000.0

    # Simulate cache hit
    thumb_b64 = base64.b64encode(b"cached_thumb").decode('utf-8')
    cached_val = {
        "path": "test.mp4",
        "intensity_score": 0.5,
        "duration": 10.0,
        "thumbnail_data": thumb_b64
    }
    mock_cache.get.return_value = cached_val

    input_data = VideoAnalysisInput(file_path="test.mp4")
    result = analyzer_service.analyze(input_data)

    # Should NOT call real analyzer
    mock_real_analyzer.analyze.assert_not_called()

    # Result should come from cache
    assert result.intensity_score == 0.5
    assert result.thumbnail_data == b"cached_thumb"


@patch("src.services.caching.analyzers.os.stat")
@patch("src.core.validation.os.path.exists", return_value=True)
def test_analyze_cache_hit_no_thumbnail(
    mock_exists, mock_stat, analyzer_service, mock_real_analyzer, mock_cache
):
    """Test cache hit handling when thumbnail_data is None."""
    # Mock stat
    mock_stat.return_value.st_size = 100
    mock_stat.return_value.st_mtime = 1000.0

    cached_val = {
        "path": "test.mp4",
        "intensity_score": 0.5,
        "duration": 10.0,
        "thumbnail_data": None
    }
    mock_cache.get.return_value = cached_val

    input_data = VideoAnalysisInput(file_path="test.mp4")
    result = analyzer_service.analyze(input_data)

    assert result.thumbnail_data is None


@patch("src.services.caching.analyzers.os.stat")
@patch("src.core.validation.os.path.exists", return_value=True)
def test_analyze_cache_deserialization_failure(
    mock_exists, mock_stat, analyzer_service, mock_real_analyzer, mock_cache
):
    """Test that deserialization failure triggers re-analysis."""
    # Mock stat
    mock_stat.return_value.st_size = 100
    mock_stat.return_value.st_mtime = 1000.0

    # Simulate cache hit with bad data
    mock_cache.get.return_value = {"invalid": "data"}

    # This should fail validation when creating VideoAnalysisResult
    # So analyze should catch exception and fallback to real analyzer

    input_data = VideoAnalysisInput(file_path="test.mp4")
    result = analyzer_service.analyze(input_data)

    # Should call real analyzer despite cache hit (because hit was invalid)
    mock_real_analyzer.analyze.assert_called_once()
    assert result.intensity_score == 0.75
