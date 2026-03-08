from pathlib import Path

import pytest
from pytest_mock import MockerFixture
from src.core.interfaces import VideoAnalysisInputProtocol
from src.core.models import VideoAnalysisResult
from src.services.persistence import CachedVideoAnalyzer, FileAnalysisRepository


class MockVideoAnalysisInput(VideoAnalysisInputProtocol):
    def __init__(self, file_path: str):
        self.file_path = file_path


@pytest.fixture
def temp_cache_dir(tmp_path: Path) -> Path:
    return tmp_path / "cache"


@pytest.fixture
def sample_video_result() -> VideoAnalysisResult:
    return VideoAnalysisResult(
        path="/fake/path/video.mp4",
        intensity_score=0.85,
        duration=10.5,
        is_vertical=False,
        thumbnail_data=b"fake_thumbnail_bytes",
    )


def test_file_analysis_repository_save_and_get(
    temp_cache_dir: Path, sample_video_result: VideoAnalysisResult
) -> None:
    """Test saving and retrieving from the repository."""
    repo = FileAnalysisRepository(cache_dir=str(temp_cache_dir))
    key = "test_key_123"

    # Save to cache
    repo.save(key, sample_video_result)

    # Retrieve from cache
    cached_result = repo.get(key)

    assert cached_result is not None
    assert cached_result.path == sample_video_result.path
    assert cached_result.intensity_score == sample_video_result.intensity_score
    assert cached_result.duration == sample_video_result.duration
    assert cached_result.is_vertical == sample_video_result.is_vertical
    assert cached_result.thumbnail_data == sample_video_result.thumbnail_data


def test_file_analysis_repository_get_miss(temp_cache_dir: Path) -> None:
    """Test retrieving a non-existent key."""
    repo = FileAnalysisRepository(cache_dir=str(temp_cache_dir))
    assert repo.get("non_existent_key") is None


def test_cached_video_analyzer_cache_miss_and_hit(
    temp_cache_dir: Path,
    sample_video_result: VideoAnalysisResult,
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    """Test that CachedVideoAnalyzer delegates on miss and returns from cache on hit."""
    mock_analyzer = mocker.MagicMock()
    mock_analyzer.analyze.return_value = sample_video_result

    repo = FileAnalysisRepository(cache_dir=str(temp_cache_dir))
    cached_analyzer = CachedVideoAnalyzer(analyzer=mock_analyzer, repository=repo)

    # Create a dummy file to test os.path.getmtime
    dummy_file = tmp_path / "video.mp4"
    dummy_file.touch()

    input_data = MockVideoAnalysisInput(file_path=str(dummy_file))

    # First call: cache miss, should delegate to underlying analyzer
    result1 = cached_analyzer.analyze(input_data)

    assert result1 == sample_video_result
    mock_analyzer.analyze.assert_called_once_with(input_data)

    # Second call: cache hit, should NOT delegate
    result2 = cached_analyzer.analyze(input_data)

    assert result2 == sample_video_result
    mock_analyzer.analyze.assert_called_once() # Still only called once
