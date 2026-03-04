import pytest
import os
import json
from src.core.models import VideoAnalysisResult
from src.services.persistence import FileAnalysisRepository, CachedVideoAnalyzer, CacheError
from src.core.interfaces import VideoAnalyzerProtocol, VideoAnalysisInputProtocol


class MockAnalyzer(VideoAnalyzerProtocol):
    def __init__(self, result: VideoAnalysisResult):
        self.result = result
        self.call_count = 0

    def analyze(self, input_data: VideoAnalysisInputProtocol) -> VideoAnalysisResult:
        self.call_count += 1
        return self.result


class MockInput(VideoAnalysisInputProtocol):
    def __init__(self, file_path: str):
        self._file_path = file_path

    @property
    def file_path(self) -> str:
        return self._file_path


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Fixture providing a temporary directory for cache."""
    return str(tmp_path / ".test_cache")


@pytest.fixture
def dummy_result():
    return VideoAnalysisResult(
        path="/some/dummy/path.mp4",
        intensity_score=0.75,
        duration=10.5,
        is_vertical=False,
        thumbnail_data=b"dummy_binary_data"
    )


def test_file_analysis_repository_save_and_get(temp_cache_dir, dummy_result):
    repo = FileAnalysisRepository(cache_dir=temp_cache_dir)

    # Save result
    repo.save(dummy_result)

    # Check cache directory contains file
    files = os.listdir(temp_cache_dir)
    assert len(files) == 1

    # Validate Base64 conversion
    with open(os.path.join(temp_cache_dir, files[0]), "r") as f:
        data = json.load(f)
        assert isinstance(data["thumbnail_data"], str)
        assert data["thumbnail_data"] != "dummy_binary_data"

    # Get result
    retrieved = repo.get(dummy_result.path)

    assert retrieved is not None
    assert retrieved.path == dummy_result.path
    assert retrieved.intensity_score == dummy_result.intensity_score
    assert retrieved.duration == dummy_result.duration
    assert retrieved.is_vertical == dummy_result.is_vertical
    assert retrieved.thumbnail_data == b"dummy_binary_data"


def test_file_analysis_repository_get_not_found(temp_cache_dir):
    repo = FileAnalysisRepository(cache_dir=temp_cache_dir)
    assert repo.get("/non/existent/path.mp4") is None


def test_cached_video_analyzer_hits_cache(temp_cache_dir, dummy_result):
    repo = FileAnalysisRepository(cache_dir=temp_cache_dir)
    inner_analyzer = MockAnalyzer(dummy_result)
    cached_analyzer = CachedVideoAnalyzer(inner_analyzer, repo)

    input_data = MockInput(file_path=dummy_result.path)

    # First call - should miss cache and call inner analyzer
    res1 = cached_analyzer.analyze(input_data)
    assert inner_analyzer.call_count == 1
    assert res1.path == dummy_result.path

    # Second call - should hit cache
    res2 = cached_analyzer.analyze(input_data)
    assert inner_analyzer.call_count == 1  # Count should not increase
    assert res2.path == dummy_result.path
    assert res2.intensity_score == dummy_result.intensity_score
