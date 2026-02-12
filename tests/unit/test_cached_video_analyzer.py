"""
Unit tests for CachedVideoAnalyzer.
"""
import json
import base64
import os
import tempfile
from unittest.mock import MagicMock
import pytest
from src.services.analyzers import CachedVideoAnalyzer
from src.core.models import VideoAnalysisResult, VideoAnalysisInput
from src.core.interfaces import IVideoAnalyzer, CacheBackend

@pytest.fixture
def mock_analyzer():
    return MagicMock(spec=IVideoAnalyzer)

@pytest.fixture
def mock_cache():
    return MagicMock(spec=CacheBackend)

@pytest.fixture
def dummy_video_file():
    fd, path = tempfile.mkstemp(suffix=".mp4")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)

def test_analyze_cache_miss(mock_analyzer, mock_cache, dummy_video_file):
    cached_analyzer = CachedVideoAnalyzer(mock_analyzer, mock_cache)

    # Mock cache miss
    mock_cache.get.return_value = None

    # Mock analyzer result
    expected_result = VideoAnalysisResult(
        path=dummy_video_file,
        intensity_score=0.5,
        duration=10.0,
        thumbnail_data=b"fake_thumb"
    )
    mock_analyzer.analyze.return_value = expected_result

    # Act
    input_data = VideoAnalysisInput(file_path=dummy_video_file)
    result = cached_analyzer.analyze(input_data)

    # Assert
    assert result.intensity_score == expected_result.intensity_score
    mock_analyzer.analyze.assert_called_once()
    mock_cache.set.assert_called_once()

    # Verify serialization
    call_args = mock_cache.set.call_args
    key, val = call_args[0]
    data = json.loads(val)
    assert data['path'] == dummy_video_file
    assert data['intensity_score'] == 0.5
    assert data['thumbnail_data'] == base64.b64encode(b"fake_thumb").decode('ascii')

def test_analyze_cache_hit(mock_analyzer, mock_cache, dummy_video_file):
    cached_analyzer = CachedVideoAnalyzer(mock_analyzer, mock_cache)

    # Mock cache hit
    cached_data = {
        "path": dummy_video_file,
        "intensity_score": 0.8,
        "duration": 5.0,
        "thumbnail_data": base64.b64encode(b"cached_thumb").decode('ascii')
    }
    mock_cache.get.return_value = json.dumps(cached_data)

    # Act
    input_data = VideoAnalysisInput(file_path=dummy_video_file)
    result = cached_analyzer.analyze(input_data)

    # Assert
    assert result.intensity_score == 0.8
    assert result.thumbnail_data == b"cached_thumb"
    mock_analyzer.analyze.assert_not_called()

def test_analyze_cache_corruption(mock_analyzer, mock_cache, dummy_video_file):
    cached_analyzer = CachedVideoAnalyzer(mock_analyzer, mock_cache)

    # Mock corrupt cache
    mock_cache.get.return_value = "invalid json"

    # Mock analyzer result
    expected_result = VideoAnalysisResult(
        path=dummy_video_file,
        intensity_score=0.5,
        duration=10.0,
        thumbnail_data=None
    )
    mock_analyzer.analyze.return_value = expected_result

    # Act
    input_data = VideoAnalysisInput(file_path=dummy_video_file)
    result = cached_analyzer.analyze(input_data)

    # Assert
    assert result.intensity_score == expected_result.intensity_score
    mock_analyzer.analyze.assert_called_once()
    # It should overwrite cache with valid data
    mock_cache.set.assert_called_once()
