import json
import os
import tempfile
import time
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.core.models import VideoAnalysisResult, VideoAnalysisInput
from src.services.analyzers.cached_video_analyzer import CachedVideoAnalyzer
from src.services.caching.backend import JsonFileCache
from src.services.caching.exceptions import CacheError

# Helpers
def create_result(path="test.mp4", score=0.5, duration=10.0, thumb=None):
    return VideoAnalysisResult(
        path=path,
        intensity_score=score,
        duration=duration,
        thumbnail_data=thumb
    )

class TestJsonFileCache:
    def test_basic_ops(self):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            path = tmp.name

        try:
            cache = JsonFileCache(path)
            cache.set("k1", "v1")
            assert cache.get("k1") == "v1"

            cache.delete("k1")
            assert cache.get("k1") is None

            cache.set("k2", "v2")
            cache.clear()
            assert cache.get("k2") is None
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_persistence(self):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            path = tmp.name

        try:
            cache1 = JsonFileCache(path)
            cache1.set("persistent", "data")

            # Reload from disk
            cache2 = JsonFileCache(path)
            assert cache2.get("persistent") == "data"
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_ttl(self):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            path = tmp.name

        try:
            cache = JsonFileCache(path)
            # Set with 0.1s TTL
            cache.set("expire", "val", ttl=0.1)
            assert cache.get("expire") == "val"

            time.sleep(0.2)
            assert cache.get("expire") is None
        finally:
            if os.path.exists(path):
                os.remove(path)

class TestCachedVideoAnalyzer:
    def test_analyze_cache_miss(self):
        mock_analyzer = Mock()
        mock_cache = Mock()

        # Setup cache miss
        mock_cache.get.return_value = None

        # Setup analyzer result
        expected_result = create_result()
        mock_analyzer.analyze.return_value = expected_result

        cached_analyzer = CachedVideoAnalyzer(mock_analyzer, mock_cache)

        # Setup input
        # Validate path mocking: VideoAnalysisInput uses validate_path which uses os.path.exists
        # We need to mock validate_file_path or ensure input is valid.
        # But VideoAnalysisInput validation happens at instantiation.
        # We can mock os.path.exists to pass validation.

        with patch("src.core.models.validate_file_path") as mock_validate:
            mock_validate.side_effect = lambda x, y: x # Pass through
            input_data = VideoAnalysisInput(file_path="test.mp4")

        # Mock os.stat to return consistent values for cache key generation
        with patch("os.stat") as mock_stat:
            mock_stat.return_value.st_size = 100
            mock_stat.return_value.st_mtime = 1000

            result = cached_analyzer.analyze(input_data)

            assert result == expected_result
            mock_analyzer.analyze.assert_called_once()
            mock_cache.set.assert_called_once()

    def test_analyze_cache_hit(self):
        mock_analyzer = Mock()
        mock_cache = Mock()

        # Setup cache hit
        # The cache stores serialized data (dict)
        original_result = create_result()
        serialized_data = original_result.model_dump()
        mock_cache.get.return_value = serialized_data

        cached_analyzer = CachedVideoAnalyzer(mock_analyzer, mock_cache)

        with patch("src.core.models.validate_file_path") as mock_validate:
            mock_validate.side_effect = lambda x, y: x
            input_data = VideoAnalysisInput(file_path="test.mp4")

        with patch("os.stat") as mock_stat:
            mock_stat.return_value.st_size = 100
            mock_stat.return_value.st_mtime = 1000

            result = cached_analyzer.analyze(input_data)

            assert result == original_result
            mock_analyzer.analyze.assert_not_called()

    def test_analyze_with_thumbnail_serialization(self):
        mock_analyzer = Mock()
        mock_cache = Mock()

        # Setup result with thumbnail (bytes)
        thumb_bytes = b"fake_png_data"
        original_result = create_result(thumb=thumb_bytes)

        mock_analyzer.analyze.return_value = original_result
        mock_cache.get.return_value = None # Miss

        cached_analyzer = CachedVideoAnalyzer(mock_analyzer, mock_cache)

        with patch("src.core.models.validate_file_path") as mock_validate:
            mock_validate.side_effect = lambda x, y: x
            input_data = VideoAnalysisInput(file_path="test.mp4")

        with patch("os.stat") as mock_stat:
            mock_stat.return_value.st_size = 100
            mock_stat.return_value.st_mtime = 1000

            result = cached_analyzer.analyze(input_data)

            assert result.thumbnail_data == thumb_bytes

            # Verify what was set in cache
            args, _ = mock_cache.set.call_args
            key, val = args
            # Value should have base64 string
            import base64
            expected_b64 = base64.b64encode(thumb_bytes).decode('utf-8')
            assert val['thumbnail_data'] == expected_b64
