"""
Integration tests for persistence and caching services.
"""

import os
from pathlib import Path

from pytest_mock import MockerFixture
from src.core.interfaces import VideoAnalysisInputProtocol, VideoAnalyzerProtocol
from src.core.models import VideoAnalysisResult
from src.services.persistence import CachedVideoAnalyzer, FileAnalysisRepository


class DummyInput(VideoAnalysisInputProtocol):
    """Dummy input for testing."""

    def __init__(self, file_path: str):
        self.file_path = file_path


def test_cached_video_analyzer_integration(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    """
    Test that CachedVideoAnalyzer correctly retrieves and stores analysis
    results from the FileAnalysisRepository using a temporary directory.
    """
    temp_cache_dir = str(tmp_path / "cache")
    repository = FileAnalysisRepository(cache_dir=temp_cache_dir)

    dummy_path = "/fake/video/path.mp4"
    dummy_input = DummyInput(file_path=dummy_path)
    expected_result = VideoAnalysisResult(
        path=dummy_path,
        intensity_score=0.85,
        duration=15.0,
        is_vertical=True,
        thumbnail_data=b"fake_image_data",
    )

    # Mock the base analyzer protocol
    mock_analyzer = mocker.Mock(spec=VideoAnalyzerProtocol)
    mock_analyzer.analyze.return_value = expected_result

    cached_analyzer = CachedVideoAnalyzer(
        base_analyzer=mock_analyzer, repository=repository
    )

    # First call: cache miss, should call base analyzer and save to repo
    result1 = cached_analyzer.analyze(dummy_input)

    assert result1 == expected_result
    mock_analyzer.analyze.assert_called_once_with(dummy_input)

    # Verify cache file was created
    cache_files = os.listdir(temp_cache_dir)
    assert len(cache_files) == 1
    assert cache_files[0].endswith(".json")

    # Second call: cache hit, should NOT call base analyzer
    result2 = cached_analyzer.analyze(dummy_input)

    assert result2 == expected_result
    mock_analyzer.analyze.assert_called_once()  # Still only called once!

    # Verify binary data round-trips through base64 properly
    assert result2.thumbnail_data == b"fake_image_data"
