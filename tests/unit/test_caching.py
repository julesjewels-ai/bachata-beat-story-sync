"""
Unit tests for the caching service.
"""
import base64
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from src.core.models import VideoAnalysisResult
from src.core.video_analyzer import VideoAnalysisInput
from src.services.caching import JsonFileCache, CachedVideoAnalyzer


@pytest.fixture
def cache_dir():
    with tempfile.TemporaryDirectory() as tmp:
        yield tmp


@pytest.fixture
def json_cache(cache_dir):
    return JsonFileCache(cache_dir)


@pytest.fixture
def dummy_video(tmp_path):
    """Creates a dummy video file to pass validation."""
    p = tmp_path / "test.mp4"
    p.touch()
    return str(p)


def test_json_cache_set_get(json_cache):
    """Test basic set and get operations."""
    key = "test_key"
    value = {"foo": "bar", "baz": 123}

    json_cache.set(key, value)
    retrieved = json_cache.get(key)

    assert retrieved == value


def test_json_cache_miss(json_cache):
    """Test get returns None for missing key."""
    assert json_cache.get("missing") is None


def test_json_cache_persistence(json_cache, cache_dir):
    """Test data is actually written to disk."""
    key = "persist"
    value = {"a": 1}
    json_cache.set(key, value)

    expected_file = Path(cache_dir) / f"{key}.json"
    assert expected_file.exists()

    with open(expected_file, "r") as f:
        data = json.load(f)
    assert data == value


def test_cached_analyzer_miss(json_cache, dummy_video):
    """Test cache miss calls inner analyzer and caches result."""
    inner = Mock()
    result = VideoAnalysisResult(
        path=dummy_video,
        intensity_score=0.5,
        duration=10.0,
        thumbnail_data=b"fake_thumb"
    )
    inner.analyze.return_value = result

    analyzer = CachedVideoAnalyzer(inner, json_cache)
    input_data = VideoAnalysisInput(file_path=dummy_video)

    # 1. First call: Miss
    res1 = analyzer.analyze(input_data)
    assert res1 == result
    inner.analyze.assert_called_once()

    # Check cache is populated
    assert len(list(Path(json_cache.cache_dir).glob("*.json"))) == 1


def test_cached_analyzer_hit(json_cache, dummy_video):
    """Test cache hit returns cached result without calling inner."""
    inner = Mock()
    result = VideoAnalysisResult(
        path=dummy_video,
        intensity_score=0.5,
        duration=10.0,
        thumbnail_data=b"fake_thumb"
    )

    analyzer = CachedVideoAnalyzer(inner, json_cache)
    input_data = VideoAnalysisInput(file_path=dummy_video)

    # Manually populate cache by calling once
    inner.analyze.return_value = result
    analyzer.analyze(input_data)

    inner.reset_mock()

    # 2. Second call: Hit
    res2 = analyzer.analyze(input_data)

    assert res2.path == result.path
    assert res2.intensity_score == result.intensity_score
    assert res2.thumbnail_data == result.thumbnail_data
    inner.analyze.assert_not_called()


def test_cached_analyzer_serialization(json_cache, dummy_video):
    """Test that bytes are correctly serialized/deserialized."""
    inner = Mock()
    original_thumb = b"\x00\x01\x02\xff"
    result = VideoAnalysisResult(
        path=dummy_video,
        intensity_score=0.8,
        duration=5.0,
        thumbnail_data=original_thumb
    )
    inner.analyze.return_value = result

    analyzer = CachedVideoAnalyzer(inner, json_cache)
    input_data = VideoAnalysisInput(file_path=dummy_video)

    # Populate
    analyzer.analyze(input_data)

    # Verify JSON content
    cache_files = list(Path(json_cache.cache_dir).glob("*.json"))
    assert len(cache_files) == 1

    with open(cache_files[0], "r") as f:
        data = json.load(f)

    # Should be base64 string
    expected_b64 = base64.b64encode(original_thumb).decode("ascii")
    assert data["thumbnail_data"] == expected_b64
