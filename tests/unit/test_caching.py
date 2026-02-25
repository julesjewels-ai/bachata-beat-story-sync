"""
Unit tests for the Caching Service.
"""
import pytest
import os
import json
import base64
import hashlib
import time
from unittest.mock import MagicMock, patch, ANY
from src.services.caching.backend import JsonFileCache
from src.services.caching.service import CachedVideoAnalyzer
from src.core.models import VideoAnalysisInput, VideoAnalysisResult

@pytest.fixture
def cache_dir(tmp_path):
    d = tmp_path / "cache"
    d.mkdir()
    return str(d)

@pytest.fixture
def json_cache(cache_dir):
    return JsonFileCache(cache_dir)

@pytest.fixture
def mock_analyzer():
    analyzer = MagicMock()
    # Ensure it returns a VideoAnalysisResult when called
    def analyze_side_effect(input_data):
        return VideoAnalysisResult(
            path=input_data.file_path,
            intensity_score=0.5,
            duration=10.0,
            is_vertical=False,
            thumbnail_data=b"fake_thumbnail"
        )
    analyzer.analyze.side_effect = analyze_side_effect
    return analyzer

@pytest.fixture
def video_file(tmp_path):
    """Creates a dummy video file."""
    p = tmp_path / "test_video.mp4"
    p.write_text("fake video content")
    return str(p)

class TestJsonFileCache:

    def test_get_miss(self, json_cache):
        assert json_cache.get("nonexistent") is None

    def test_set_get(self, json_cache):
        key = "test_key"
        value = {"foo": "bar", "baz": 123}
        json_cache.set(key, value)

        cached = json_cache.get(key)
        assert cached == value

        # Verify file exists
        path = os.path.join(json_cache.cache_dir, f"{key}.json")
        assert os.path.exists(path)

    def test_get_corrupted(self, json_cache):
        key = "corrupted"
        path = os.path.join(json_cache.cache_dir, f"{key}.json")
        with open(path, 'w') as f:
            f.write("invalid json")

        assert json_cache.get(key) is None

class TestCachedVideoAnalyzer:

    @pytest.fixture
    def cached_service(self, mock_analyzer, json_cache):
        return CachedVideoAnalyzer(mock_analyzer, json_cache)

    def test_analyze_cache_miss(self, cached_service, mock_analyzer, video_file):
        input_data = VideoAnalysisInput(file_path=video_file)

        result = cached_service.analyze(input_data)

        # Verify delegate called
        mock_analyzer.analyze.assert_called_once()
        assert result.path == video_file

        # Verify cache set
        # We compute the key manually to verify
        mtime = os.path.getmtime(video_file)
        size = os.path.getsize(video_file)
        key_base = f"{video_file}:{mtime}:{size}"
        expected_key = hashlib.md5(key_base.encode('utf-8')).hexdigest()

        cached_val = cached_service.cache.get(expected_key)
        assert cached_val is not None
        assert cached_val['path'] == video_file
        # Verify thumbnail encoded
        assert cached_val['thumbnail_data'] == base64.b64encode(b"fake_thumbnail").decode('ascii')

    def test_analyze_cache_hit(self, cached_service, mock_analyzer, video_file):
        input_data = VideoAnalysisInput(file_path=video_file)

        # Pre-populate cache
        mtime = os.path.getmtime(video_file)
        size = os.path.getsize(video_file)
        key_base = f"{video_file}:{mtime}:{size}"
        expected_key = hashlib.md5(key_base.encode('utf-8')).hexdigest()

        cached_result = {
            "path": video_file,
            "intensity_score": 0.8,
            "duration": 20.0,
            "is_vertical": True,
            "thumbnail_data": base64.b64encode(b"cached_thumb").decode('ascii')
        }
        cached_service.cache.set(expected_key, cached_result)

        # Analyze
        result = cached_service.analyze(input_data)

        # Verify delegate NOT called
        mock_analyzer.analyze.assert_not_called()

        # Verify result from cache
        assert result.intensity_score == 0.8
        assert result.thumbnail_data == b"cached_thumb"

    def test_analyze_file_changed(self, cached_service, mock_analyzer, video_file):
        input_data = VideoAnalysisInput(file_path=video_file)

        # 1. First run (miss)
        cached_service.analyze(input_data)
        mock_analyzer.analyze.assert_called_once()
        mock_analyzer.reset_mock()

        # 2. Modify file (change mtime)
        time.sleep(0.01) # Ensure mtime differs
        os.utime(video_file, None)

        # 3. Second run (file changed -> miss again)
        cached_service.analyze(input_data)
        mock_analyzer.analyze.assert_called_once()

        # Verify new cache entry exists
        mtime = os.path.getmtime(video_file)
        size = os.path.getsize(video_file)
        key_base = f"{video_file}:{mtime}:{size}"
        new_key = hashlib.md5(key_base.encode('utf-8')).hexdigest()

        assert cached_service.cache.get(new_key) is not None
