"""
Integration tests for persistence services.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from src.core.interfaces import VideoAnalysisInputProtocol
from src.core.models import VideoAnalysisResult
from src.services.persistence import CachedVideoAnalyzer, FileAnalysisRepository


class MockVideoAnalysisInput(VideoAnalysisInputProtocol):
    def __init__(self, file_path: str):
        self.file_path = file_path


@pytest.fixture
def temp_cache_dir(tmp_path: Path) -> str:
    cache_dir = tmp_path / ".bachata_cache_test"
    return str(cache_dir)


@pytest.fixture
def dummy_analysis_result() -> VideoAnalysisResult:
    return VideoAnalysisResult(
        path="/dummy/path/video.mp4",
        intensity_score=0.75,
        duration=10.0,
        is_vertical=False,
        thumbnail_data=b"dummy_thumbnail_data",
    )


def test_file_analysis_repository_save_and_get(
    temp_cache_dir: str, dummy_analysis_result: VideoAnalysisResult
) -> None:
    """Test saving and retrieving an analysis result using FileAnalysisRepository."""
    repo = FileAnalysisRepository(cache_dir=temp_cache_dir)
    file_path = "/dummy/path/video.mp4"

    # Save
    repo.save_video_analysis(file_path, dummy_analysis_result)

    # Verify cache directory exists and contains a file
    assert os.path.exists(temp_cache_dir)
    cache_files = os.listdir(temp_cache_dir)
    assert len(cache_files) == 1

    # Get
    retrieved_result = repo.get_video_analysis(file_path)

    # Verify
    assert retrieved_result is not None
    assert retrieved_result.path == dummy_analysis_result.path
    assert retrieved_result.intensity_score == dummy_analysis_result.intensity_score
    assert retrieved_result.duration == dummy_analysis_result.duration
    assert retrieved_result.is_vertical == dummy_analysis_result.is_vertical
    assert retrieved_result.thumbnail_data == dummy_analysis_result.thumbnail_data


def test_cached_video_analyzer_cache_miss_and_hit(
    temp_cache_dir: str, dummy_analysis_result: VideoAnalysisResult
) -> None:
    """Test CachedVideoAnalyzer logic for cache misses and subsequent hits."""
    repo = FileAnalysisRepository(cache_dir=temp_cache_dir)

    # Mock analyzer
    mock_analyzer = MagicMock()
    mock_analyzer.analyze.return_value = dummy_analysis_result

    cached_analyzer = CachedVideoAnalyzer(analyzer=mock_analyzer, repository=repo)

    input_data = MockVideoAnalysisInput(file_path="/dummy/path/video.mp4")

    # 1. Cache miss: Should call the underlying analyzer and save to cache
    result1 = cached_analyzer.analyze(input_data)

    assert result1 == dummy_analysis_result
    mock_analyzer.analyze.assert_called_once_with(input_data)

    # Verify it was saved to the repository
    cached_data = repo.get_video_analysis(input_data.file_path)
    assert cached_data is not None
    assert cached_data.intensity_score == dummy_analysis_result.intensity_score

    # Reset mock for next check
    mock_analyzer.reset_mock()

    # 2. Cache hit: Should retrieve from cache and NOT call the underlying analyzer
    result2 = cached_analyzer.analyze(input_data)

    assert result2 is not None
    assert result2.intensity_score == dummy_analysis_result.intensity_score
    mock_analyzer.analyze.assert_not_called()
