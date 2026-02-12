"""
Integration test for caching in BachataSyncEngine.
Ensures dependency injection and caching logic work end-to-end.
"""
import sys
from unittest.mock import MagicMock

# Mock heavy dependencies before imports
sys.modules['cv2'] = MagicMock()
sys.modules['moviepy'] = MagicMock()
sys.modules['librosa'] = MagicMock()
sys.modules['tensorflow'] = MagicMock()
sys.modules['numpy'] = MagicMock()

import os  # noqa: E402
import json  # noqa: E402
import tempfile  # noqa: E402
import shutil  # noqa: E402
import pytest  # noqa: E402
from src.core.app import BachataSyncEngine  # noqa: E402
from src.core.models import VideoAnalysisResult  # noqa: E402
from src.services.analyzers import CachedVideoAnalyzer  # noqa: E402
from src.core.interfaces import IVideoAnalyzer  # noqa: E402

@pytest.fixture
def mock_video_analyzer():
    analyzer = MagicMock(spec=IVideoAnalyzer)
    return analyzer

@pytest.fixture
def temp_cache_file():
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)

@pytest.fixture
def dummy_video_file():
    fd, path = tempfile.mkstemp(suffix=".mp4")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)

@pytest.fixture
def temp_dir():
    path = tempfile.mkdtemp()
    yield path
    shutil.rmtree(path)

def test_engine_uses_injected_analyzer(mock_video_analyzer, dummy_video_file, temp_dir):
    # Setup
    expected_result = VideoAnalysisResult(
        path=dummy_video_file,
        intensity_score=0.9,
        duration=15.0,
        thumbnail_data=None
    )
    mock_video_analyzer.analyze.return_value = expected_result

    # Inject into engine
    engine = BachataSyncEngine(video_analyzer=mock_video_analyzer)

    # Mock finding files to avoid recursive directory scan
    engine._collect_video_files = MagicMock(return_value=[dummy_video_file])  # type: ignore[method-assign]

    # Execute
    results = engine.scan_video_library(temp_dir)

    # Verify
    assert len(results) == 1
    assert results[0] == expected_result
    mock_video_analyzer.analyze.assert_called_once()

    # Verify input argument was correct
    args = mock_video_analyzer.analyze.call_args[0]
    assert args[0].file_path == dummy_video_file

def test_default_engine_uses_caching(temp_cache_file, dummy_video_file, temp_dir):
    # Setup Engine with default (CachedVideoAnalyzer) pointing to temp cache
    # We must patch VideoAnalyzer because the default ctor instantiates it
    with pytest.MonkeyPatch.context() as m:
        mock_real_analyzer_cls = MagicMock()
        mock_real_analyzer_instance = mock_real_analyzer_cls.return_value

        # Mock result from "real" analyzer
        expected_result = VideoAnalysisResult(
            path=dummy_video_file,
            intensity_score=0.7,
            duration=12.0,
            thumbnail_data=b"real_thumb"
        )
        mock_real_analyzer_instance.analyze.return_value = expected_result

        # Patch VideoAnalyzer class in src.core.app module
        m.setattr("src.core.app.VideoAnalyzer", mock_real_analyzer_cls)

        # Instantiate engine using specific cache path via dependency injection
        engine = BachataSyncEngine(cache_path=temp_cache_file)

        # Verify type
        assert isinstance(engine.video_analyzer, CachedVideoAnalyzer)

        # Mock finding files
        engine._collect_video_files = MagicMock(return_value=[dummy_video_file])  # type: ignore[method-assign]

        # First Run: Cache Miss
        results1 = engine.scan_video_library(temp_dir)
        assert len(results1) == 1
        assert results1[0].intensity_score == 0.7
        mock_real_analyzer_instance.analyze.assert_called_once()

        # Verify cache file content
        with open(temp_cache_file, 'r') as f:
            cache_data = json.load(f)
            assert len(cache_data) == 1 # One entry

        # Second Run: Cache Hit
        # Reset mock to prove it's not called
        mock_real_analyzer_instance.analyze.reset_mock()

        results2 = engine.scan_video_library(temp_dir)
        assert len(results2) == 1
        assert results2[0].intensity_score == 0.7

        # Should NOT call real analyzer
        mock_real_analyzer_instance.analyze.assert_not_called()
