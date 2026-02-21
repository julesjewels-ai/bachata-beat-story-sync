"""
Unit tests for caching services.
"""
import base64
import json
import shutil
import tempfile
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from src.core.models import VideoAnalysisResult, VideoAnalysisInput
from src.services.caching.backend import JsonFileCache
from src.services.caching.service import CachedVideoAnalyzer


@pytest.fixture
def temp_cache_dir():
    """Fixture to provide a temporary cache directory."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_analyzer():
    """Fixture to provide a mock IVideoAnalyzer."""
    mock = MagicMock()
    return mock


@pytest.fixture
def temp_video_file(tmp_path):
    """Creates a dummy video file."""
    video_path = tmp_path / "test_video.mp4"
    video_path.touch()
    return str(video_path)


class TestJsonFileCache:
    """Tests for JsonFileCache backend."""

    def test_set_and_get(self, temp_cache_dir):
        cache = JsonFileCache(temp_cache_dir)
        key = "test_key"
        value = {"foo": "bar"}

        cache.set(key, value)
        retrieved = cache.get(key)

        assert retrieved == value
        assert (Path(temp_cache_dir) / f"{key}.json").exists()

    def test_get_missing_key(self, temp_cache_dir):
        cache = JsonFileCache(temp_cache_dir)
        assert cache.get("missing") is None

    def test_delete(self, temp_cache_dir):
        cache = JsonFileCache(temp_cache_dir)
        key = "to_delete"
        cache.set(key, {"a": 1})

        assert cache.get(key) is not None
        cache.delete(key)
        assert cache.get(key) is None
        assert not (Path(temp_cache_dir) / f"{key}.json").exists()

    def test_corrupted_file(self, temp_cache_dir):
        cache = JsonFileCache(temp_cache_dir)
        key = "corrupted"
        file_path = Path(temp_cache_dir) / f"{key}.json"

        with open(file_path, "w") as f:
            f.write("{invalid_json")

        assert cache.get(key) is None
        # Should be deleted after failed read
        assert not file_path.exists()


class TestCachedVideoAnalyzer:
    """Tests for CachedVideoAnalyzer service."""

    def test_analyze_cache_miss(self, temp_cache_dir, mock_analyzer, temp_video_file):
        cache = JsonFileCache(temp_cache_dir)
        service = CachedVideoAnalyzer(mock_analyzer, cache)

        expected_result = VideoAnalysisResult(
            path=temp_video_file,
            intensity_score=0.8,
            duration=10.0,
            thumbnail_data=b"fake_thumbnail"
        )

        input_data = VideoAnalysisInput(file_path=temp_video_file)
        mock_analyzer.analyze.return_value = expected_result

        original_stat = os.stat
        def stat_side_effect(path, *args, **kwargs):
            if str(path) == str(temp_video_file):
                 mock = MagicMock()
                 mock.st_mtime = 1000
                 mock.st_size = 500
                 return mock
            return original_stat(path, *args, **kwargs)

        with patch("src.services.caching.service.os.stat", side_effect=stat_side_effect):
            # Execute
            result = service.analyze(input_data)

            # Verify
            assert result == expected_result
            mock_analyzer.analyze.assert_called_once_with(input_data)

            # Verify cache was written
            assert len(list(Path(temp_cache_dir).glob("*.json"))) == 1

    def test_analyze_cache_hit(self, temp_cache_dir, mock_analyzer, temp_video_file):
        cache = JsonFileCache(temp_cache_dir)
        service = CachedVideoAnalyzer(mock_analyzer, cache)
        input_data = VideoAnalysisInput(file_path=temp_video_file)

        expected_result = VideoAnalysisResult(
            path=temp_video_file,
            intensity_score=0.8,
            duration=10.0,
            thumbnail_data=b"fake_thumbnail"
        )

        # Pre-populate cache manually
        data = expected_result.model_dump()
        data["thumbnail_data"] = base64.b64encode(expected_result.thumbnail_data).decode("utf-8")

        # Generate key manually matching the mocked stat
        key_data = f"{temp_video_file}:1000:500"
        import hashlib
        key = hashlib.md5(key_data.encode("utf-8")).hexdigest()
        cache.set(key, data)

        original_stat = os.stat
        def stat_side_effect(path, *args, **kwargs):
            if str(path) == str(temp_video_file):
                 mock = MagicMock()
                 mock.st_mtime = 1000
                 mock.st_size = 500
                 return mock
            return original_stat(path, *args, **kwargs)

        with patch("src.services.caching.service.os.stat", side_effect=stat_side_effect):
            # Execute
            result = service.analyze(input_data)

            # Verify
            assert result == expected_result
            mock_analyzer.analyze.assert_not_called()

    def test_thumbnail_handling(self, temp_cache_dir, mock_analyzer, temp_video_file):
        cache = JsonFileCache(temp_cache_dir)
        service = CachedVideoAnalyzer(mock_analyzer, cache)

        # Result without thumbnail
        no_thumb_result = VideoAnalysisResult(
            path=temp_video_file,
            intensity_score=0.5,
            duration=5.0,
            thumbnail_data=None
        )
        input_data = VideoAnalysisInput(file_path=temp_video_file)

        mock_analyzer.analyze.return_value = no_thumb_result

        original_stat = os.stat
        def stat_side_effect(path, *args, **kwargs):
            if str(path) == str(temp_video_file):
                 mock = MagicMock()
                 mock.st_mtime = 1000
                 mock.st_size = 500
                 return mock
            return original_stat(path, *args, **kwargs)

        with patch("src.services.caching.service.os.stat", side_effect=stat_side_effect):
            # First call (Miss)
            result1 = service.analyze(input_data)
            assert result1.thumbnail_data is None

            # Second call (Hit)
            result2 = service.analyze(input_data)
            assert result2.thumbnail_data is None
            mock_analyzer.analyze.assert_called_once()
