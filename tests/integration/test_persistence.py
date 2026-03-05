"""
Integration tests for persistence and caching services.
"""

import base64
import os
import tempfile
from unittest.mock import MagicMock

import pytest
from src.core.interfaces import VideoAnalysisInputProtocol
from src.core.models import VideoAnalysisResult
from src.services.persistence import CachedVideoAnalyzer, FileAnalysisRepository


class DummyInput(VideoAnalysisInputProtocol):
    file_path: str

    def __init__(self, file_path: str):
        self.file_path = file_path


@pytest.fixture
def temp_cache_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def mock_analyzer():
    analyzer = MagicMock()
    return analyzer


def test_cache_miss_stores_data(temp_cache_dir, mock_analyzer):
    repo = FileAnalysisRepository(cache_dir=temp_cache_dir)
    cached_analyzer = CachedVideoAnalyzer(mock_analyzer, repo)

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tf:
        tf.write(b"dummy")
        tf_path = tf.name

    try:
        expected_result = VideoAnalysisResult(
            path=tf_path,
            intensity_score=0.5,
            duration=10.0,
            is_vertical=False,
            thumbnail_data=b"thumb",
        )
        mock_analyzer.analyze.return_value = expected_result

        input_data = DummyInput(file_path=tf_path)

        # First call should miss cache and call underlying analyzer
        result = cached_analyzer.analyze(input_data)

        mock_analyzer.analyze.assert_called_once_with(input_data)
        assert result.path == tf_path
        assert result.intensity_score == 0.5
        assert result.thumbnail_data == b"thumb"

        # Verify it was saved to the repo
        cached_result = repo.get_analysis(tf_path)
        assert cached_result is not None
        assert cached_result.path == tf_path
        assert cached_result.thumbnail_data == b"thumb"
    finally:
        os.remove(tf_path)


def test_cache_hit_returns_stored_data(temp_cache_dir, mock_analyzer):
    repo = FileAnalysisRepository(cache_dir=temp_cache_dir)
    cached_analyzer = CachedVideoAnalyzer(mock_analyzer, repo)

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tf:
        tf.write(b"dummy")
        tf_path = tf.name

    try:
        initial_result = VideoAnalysisResult(
            path=tf_path,
            intensity_score=0.8,
            duration=20.0,
            is_vertical=True,
            thumbnail_data=None,
        )

        # Pre-populate cache
        repo.save_analysis(tf_path, initial_result)

        input_data = DummyInput(file_path=tf_path)

        # First call should hit cache and NOT call underlying analyzer
        result = cached_analyzer.analyze(input_data)

        mock_analyzer.analyze.assert_not_called()
        assert result.path == tf_path
        assert result.intensity_score == 0.8
        assert result.is_vertical is True
        assert result.thumbnail_data is None
    finally:
        os.remove(tf_path)


def test_thumbnail_base64_encoding_decoding(temp_cache_dir):
    repo = FileAnalysisRepository(cache_dir=temp_cache_dir)

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tf:
        tf.write(b"dummy")
        tf_path = tf.name

    try:
        original_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        result = VideoAnalysisResult(
            path=tf_path,
            intensity_score=0.1,
            duration=5.0,
            is_vertical=False,
            thumbnail_data=original_bytes,
        )

        repo.save_analysis(tf_path, result)

        # Check raw JSON to ensure it's base64 encoded string
        cache_path = repo._get_cache_path(tf_path)
        with open(cache_path, encoding="utf-8") as f:
            raw_data = f.read()
            assert "thumbnail_data" in raw_data
            encoded_str = base64.b64encode(original_bytes).decode("utf-8")
            assert f'"{encoded_str}"' in raw_data

        # Check retrieved result to ensure it's decoded back to bytes
        retrieved_result = repo.get_analysis(tf_path)
        assert retrieved_result is not None
        assert retrieved_result.thumbnail_data == original_bytes
    finally:
        os.remove(tf_path)
