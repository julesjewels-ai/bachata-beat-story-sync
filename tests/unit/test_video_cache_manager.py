import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from src.core.models import VideoAnalysisResult
from src.core.video_cache_manager import VideoAnalysisCache


class TestVideoAnalysisCache:
    @pytest.fixture
    def temp_cache_file(self):
        """Creates a temporary cache file path."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        yield path
        if os.path.exists(path):
            os.remove(path)

    @pytest.fixture
    def temp_video_file(self):
        """Creates a mock temporary video file."""
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"mock video bytes")
            path = f.name
        yield path
        if os.path.exists(path):
            os.remove(path)

    def test_cache_miss_when_file_not_in_cache(self, temp_cache_file, temp_video_file):
        """Should return None if file is not in cache."""
        cache = VideoAnalysisCache(cache_file_name=temp_cache_file)
        assert cache.get(temp_video_file) is None

    def test_cache_hit_and_miss_on_modification(self, temp_cache_file, temp_video_file):
        """Should hit when stats match, but miss if file size or mtime changes."""
        cache = VideoAnalysisCache(cache_file_name=temp_cache_file)
        result = VideoAnalysisResult(
            path=temp_video_file,
            intensity_score=0.45,
            duration=12.5,
            is_vertical=False,
            thumbnail_data=b"fake-thumbnail-bytes",
            scene_changes=[1.0, 5.0],
            opening_intensity=0.3,
        )

        # Set cache
        cache.set(temp_video_file, result)

        # Get cache: should hit
        cached = cache.get(temp_video_file)
        assert cached is not None
        assert cached.path == temp_video_file
        assert cached.intensity_score == 0.45
        assert cached.duration == 12.5
        assert cached.thumbnail_data == b"fake-thumbnail-bytes"
        assert cached.scene_changes == [1.0, 5.0]
        assert cached.opening_intensity == 0.3

        # Modify file size (force cache miss)
        with open(temp_video_file, "ab") as f:
            f.write(b"extra bytes")

        # Get cache: should miss
        assert cache.get(temp_video_file) is None

    def test_load_and_save_cache(self, temp_cache_file, temp_video_file):
        """Should successfully write cache to disk and load it back on init."""
        cache = VideoAnalysisCache(cache_file_name=temp_cache_file)
        result = VideoAnalysisResult(
            path=temp_video_file,
            intensity_score=0.8,
            duration=5.0,
            thumbnail_data=None,
        )
        cache.set(temp_video_file, result)
        cache.save()

        # Instantiate a new cache pointing to the same file
        new_cache = VideoAnalysisCache(cache_file_name=temp_cache_file)
        cached = new_cache.get(temp_video_file)
        assert cached is not None
        assert cached.path == temp_video_file
        assert cached.intensity_score == 0.8
        assert cached.duration == 5.0
        assert cached.thumbnail_data is None

    def test_find_project_root(self):
        """Should return project root when markers are present."""
        cache = VideoAnalysisCache()
        root = cache._find_project_root()
        assert os.path.exists(os.path.join(root, "Makefile")) or os.path.exists(
            os.path.join(root, ".git")
        )
