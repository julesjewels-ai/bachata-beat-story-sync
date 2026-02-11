"""
Unit tests for the CachedVideoAnalyzer.
"""
import pytest
import base64
from unittest.mock import Mock, MagicMock
from src.core.models import VideoAnalysisInput, VideoAnalysisResult
from src.services.analyzers.cached_video_analyzer import CachedVideoAnalyzer
from src.core.interfaces import CacheBackend, IVideoAnalyzer

@pytest.fixture
def mock_cache():
    return Mock(spec=CacheBackend)

@pytest.fixture
def mock_analyzer():
    # Use MagicMock to allow setting return values easily
    return MagicMock(spec=IVideoAnalyzer)

@pytest.fixture
def valid_input(tmp_path):
    f = tmp_path / "test.mp4"
    f.touch()
    return VideoAnalysisInput(file_path=str(f))

def test_cache_miss_delegates_and_caches(mock_analyzer, mock_cache, valid_input):
    """Test that a cache miss triggers analysis and caches the result."""
    analyzer = CachedVideoAnalyzer(mock_analyzer, mock_cache)

    # Setup cache miss
    mock_cache.get.return_value = None

    # Setup analyzer result
    expected_result = VideoAnalysisResult(
        path=valid_input.file_path,
        intensity_score=0.5,
        duration=10.0,
        thumbnail_data=b'fake_thumbnail'
    )
    mock_analyzer.analyze.return_value = expected_result

    # Execute
    result = analyzer.analyze(valid_input)

    # Verify
    assert result == expected_result
    mock_analyzer.analyze.assert_called_once_with(valid_input)
    mock_cache.set.assert_called_once()

    # Verify cached value structure (base64 encoding)
    call_args = mock_cache.set.call_args
    # call_args is (args, kwargs). args[1] is value.
    cached_val = call_args[0][1]
    assert cached_val['path'] == valid_input.file_path
    assert cached_val['intensity_score'] == 0.5
    # Expect base64 encoded string for bytes
    expected_b64 = base64.b64encode(b'fake_thumbnail').decode('utf-8')
    assert cached_val['thumbnail_data'] == expected_b64

def test_cache_hit_returns_deserialized_result(mock_analyzer, mock_cache, valid_input):
    """Test that a cache hit returns the result without calling the analyzer."""
    analyzer = CachedVideoAnalyzer(mock_analyzer, mock_cache)

    # Setup cache hit
    cached_b64 = base64.b64encode(b'cached_thumbnail').decode('utf-8')
    cached_data = {
        "path": valid_input.file_path,
        "intensity_score": 0.8,
        "duration": 5.0,
        "thumbnail_data": cached_b64
    }
    mock_cache.get.return_value = cached_data

    # Execute
    result = analyzer.analyze(valid_input)

    # Verify
    assert result.intensity_score == 0.8
    assert result.duration == 5.0
    assert result.thumbnail_data == b'cached_thumbnail'
    mock_analyzer.analyze.assert_not_called()

def test_cache_hit_with_none_thumbnail(mock_analyzer, mock_cache, valid_input):
    """Test deserialization when thumbnail is None."""
    analyzer = CachedVideoAnalyzer(mock_analyzer, mock_cache)

    cached_data = {
        "path": valid_input.file_path,
        "intensity_score": 0.8,
        "duration": 5.0,
        "thumbnail_data": None
    }
    mock_cache.get.return_value = cached_data

    result = analyzer.analyze(valid_input)

    assert result.thumbnail_data is None
