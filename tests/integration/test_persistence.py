import os
import json
import pytest
from src.services.persistence import FileAnalysisRepository, CachedVideoAnalyzer
from src.core.models import VideoAnalysisResult
from src.core.video_analyzer import VideoAnalysisInput
from src.core.interfaces import VideoAnalyzerProtocol

class MockVideoAnalyzer(VideoAnalyzerProtocol):
    def __init__(self, mock_result: VideoAnalysisResult):
        self.mock_result = mock_result
        self.call_count = 0

    def analyze(self, input_data: VideoAnalysisInput) -> VideoAnalysisResult:
        self.call_count += 1
        return self.mock_result

@pytest.fixture
def temp_cache_dir(tmp_path):
    cache_dir = tmp_path / ".bachata_cache_test"
    yield str(cache_dir)

def test_cached_video_analyzer_integration(temp_cache_dir, tmp_path):
    # 1. Setup mock data and fake video file
    dummy_video = tmp_path / "dummy.mp4"
    dummy_video.write_text("fake video content")
    video_path_str = str(dummy_video)

    expected_result = VideoAnalysisResult(
        path=video_path_str,
        intensity_score=0.85,
        duration=10.5,
        is_vertical=False,
        thumbnail_data=b"fake_thumbnail_data"
    )

    inner_analyzer = MockVideoAnalyzer(expected_result)
    repository = FileAnalysisRepository(cache_dir=temp_cache_dir)
    cached_analyzer = CachedVideoAnalyzer(inner_analyzer, repository)

    input_data = VideoAnalysisInput(file_path=video_path_str)

    # 2. First call: Should miss cache, call inner analyzer, and save to cache
    result1 = cached_analyzer.analyze(input_data)

    assert inner_analyzer.call_count == 1
    assert result1.path == expected_result.path
    assert result1.intensity_score == expected_result.intensity_score
    assert result1.thumbnail_data == expected_result.thumbnail_data

    # Verify file was created in the repository
    cache_files = os.listdir(temp_cache_dir)
    assert len(cache_files) == 1

    # 3. Second call: Should hit cache, inner analyzer NOT called
    result2 = cached_analyzer.analyze(input_data)

    assert inner_analyzer.call_count == 1 # Still 1!
    assert result2.path == expected_result.path
    assert result2.intensity_score == expected_result.intensity_score
    assert result2.thumbnail_data == expected_result.thumbnail_data

def test_file_analysis_repository_thumbnail_encoding(temp_cache_dir):
    repo = FileAnalysisRepository(cache_dir=temp_cache_dir)
    cache_key = "test_key_123"

    result = VideoAnalysisResult(
        path="/fake/path.mp4",
        intensity_score=0.5,
        duration=5.0,
        is_vertical=True,
        thumbnail_data=b"\x00\x01\x02\x03"
    )

    # Save it
    repo.save_video_analysis(cache_key, result)

    # Read it directly from file system to verify json content
    file_path = repo._get_file_path(cache_key)
    assert os.path.exists(file_path)

    with open(file_path, "r") as f:
        data = json.load(f)

    # Verify thumbnail is base64 encoded string
    assert isinstance(data["thumbnail_data"], str)

    # Load it via repository
    loaded_result = repo.get_video_analysis(cache_key)
    assert loaded_result is not None
    assert loaded_result.thumbnail_data == b"\x00\x01\x02\x03"
