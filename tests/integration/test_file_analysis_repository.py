"""
Integration tests for the FileAnalysisRepository.
"""

import os

import pytest
from src.adapters.repository import FileAnalysisRepository
from src.core.models import VideoAnalysisResult


@pytest.fixture
def dummy_result() -> VideoAnalysisResult:
    """Fixture providing a valid VideoAnalysisResult with thumbnail data."""
    return VideoAnalysisResult(
        path="/tmp/test_video.mp4",
        intensity_score=0.75,
        duration=15.0,
        is_vertical=False,
        thumbnail_data=b"mock_thumbnail_bytes_123",
        scene_changes=[2.0, 5.5, 10.1],
    )


def test_repository_lifecycle(
    tmp_path: pytest.TempPathFactory | os.PathLike[str],
    dummy_result: VideoAnalysisResult,
) -> None:
    """
    Tests the full lifecycle of the FileAnalysisRepository:
    save, get, and delete operations.
    """
    cache_file = os.path.join(str(tmp_path), ".test_cache.json")
    repo = FileAnalysisRepository(cache_file_name=cache_file)

    # Force the repo to use our temp path instead of project root
    repo.cache_path = cache_file

    # Ensure starting state
    assert repo.get(dummy_result.path) is None
    assert len(repo.list_all()) == 0

    # Test Save
    # We need to mock os.path.exists and os.stat for the file path
    # because the repo checks if the video file exists before saving.
    # Instead, let's create a dummy file to satisfy the stat checks.
    test_video_path = os.path.join(str(tmp_path), "test_video.mp4")
    with open(test_video_path, "wb") as f:
        f.write(b"dummy video content")

    # Update the dummy result to use the actual test file path
    dummy_result.path = test_video_path

    repo.save(test_video_path, dummy_result)

    # Test Get
    retrieved = repo.get(test_video_path)
    assert retrieved is not None
    assert retrieved.path == dummy_result.path
    assert retrieved.intensity_score == dummy_result.intensity_score
    assert retrieved.duration == dummy_result.duration
    assert retrieved.thumbnail_data == b"mock_thumbnail_bytes_123"
    assert retrieved.scene_changes == dummy_result.scene_changes

    # Test List
    all_items = repo.list_all()
    assert len(all_items) == 1
    assert all_items[0].path == test_video_path

    # Test Persistence (re-instantiate)
    repo2 = FileAnalysisRepository(cache_file_name=cache_file)
    repo2.cache_path = cache_file
    repo2._load()
    retrieved2 = repo2.get(test_video_path)
    assert retrieved2 is not None
    assert retrieved2.thumbnail_data == b"mock_thumbnail_bytes_123"

    # Test Delete
    repo.delete(test_video_path)
    assert repo.get(test_video_path) is None
    assert len(repo.list_all()) == 0
