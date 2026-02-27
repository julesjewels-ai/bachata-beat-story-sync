"""
Integration tests for persistence services.
"""
import json
import os
import time
from unittest.mock import MagicMock, patch

import pytest

from src.core.models import VideoAnalysisResult
from src.core.video_analyzer import VideoAnalysisInput
from src.services.persistence import CachedVideoAnalyzer, FileAnalysisRepository


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Fixture for a temporary cache directory."""
    return str(tmp_path / "cache")


@pytest.fixture
def sample_result():
    """Fixture for a sample analysis result."""
    return VideoAnalysisResult(
        path="/path/to/video.mp4",
        intensity_score=0.8,
        duration=10.0,
        is_vertical=True,
        thumbnail_data=b"fake_png_data"
    )


def test_repository_save_and_get(temp_cache_dir, sample_result):
    """Test saving and retrieving from the file repository."""
    repo = FileAnalysisRepository(cache_dir=temp_cache_dir)
    key = "test_key"

    # Save
    repo.save(key, sample_result)

    # Verify file exists
    expected_path = repo._get_cache_path(key)
    assert os.path.exists(expected_path)

    # Get
    loaded_result = repo.get(key)
    assert loaded_result is not None
    assert loaded_result.path == sample_result.path
    assert loaded_result.intensity_score == sample_result.intensity_score
    assert loaded_result.thumbnail_data == sample_result.thumbnail_data


def test_repository_get_miss(temp_cache_dir):
    """Test retrieving a non-existent key."""
    repo = FileAnalysisRepository(cache_dir=temp_cache_dir)
    result = repo.get("non_existent_key")
    assert result is None


def test_cached_analyzer_hit(temp_cache_dir, sample_result):
    """Test that cached results are returned without calling the analyzer."""
    repo = FileAnalysisRepository(cache_dir=temp_cache_dir)
    mock_analyzer = MagicMock()
    cached_analyzer = CachedVideoAnalyzer(mock_analyzer, repo)

    # Pre-populate cache
    video_path = "test_video.mp4"
    # Create a dummy file to ensure os.stat works
    with open(video_path, "w") as f:
        f.write("dummy content")

    try:
        input_data = VideoAnalysisInput(file_path=video_path)
        cache_key = cached_analyzer._generate_cache_key(video_path)
        repo.save(cache_key, sample_result)

        # Execute
        result = cached_analyzer.analyze(input_data)

        # Verify
        assert result.path == sample_result.path
        mock_analyzer.analyze.assert_not_called()
    finally:
        os.remove(video_path)


def test_cached_analyzer_miss(temp_cache_dir, sample_result):
    """Test that missing cache triggers analysis and saves result."""
    repo = FileAnalysisRepository(cache_dir=temp_cache_dir)
    mock_analyzer = MagicMock()
    mock_analyzer.analyze.return_value = sample_result
    cached_analyzer = CachedVideoAnalyzer(mock_analyzer, repo)

    video_path = "test_video_miss.mp4"
    with open(video_path, "w") as f:
        f.write("dummy content")

    try:
        input_data = VideoAnalysisInput(file_path=video_path)
        cache_key = cached_analyzer._generate_cache_key(video_path)

        # Ensure cache is empty
        assert repo.get(cache_key) is None

        # Execute
        result = cached_analyzer.analyze(input_data)

        # Verify
        assert result.path == sample_result.path
        mock_analyzer.analyze.assert_called_once()

        # Verify it was saved
        assert repo.get(cache_key) is not None
    finally:
        os.remove(video_path)


def test_cache_invalidation_on_change(temp_cache_dir, sample_result):
    """Test that changing the file results in a new cache key."""
    repo = FileAnalysisRepository(cache_dir=temp_cache_dir)
    mock_analyzer = MagicMock()
    mock_analyzer.analyze.return_value = sample_result
    cached_analyzer = CachedVideoAnalyzer(mock_analyzer, repo)

    video_path = "test_video_change.mp4"

    try:
        # Create initial file
        with open(video_path, "w") as f:
            f.write("content 1")

        key1 = cached_analyzer._generate_cache_key(video_path)

        # Modify file (wait to ensure mtime changes if system is fast)
        time.sleep(0.01)
        with open(video_path, "w") as f:
            f.write("content 22222") # Different size too

        key2 = cached_analyzer._generate_cache_key(video_path)

        assert key1 != key2
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)
