import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock
from pathlib import Path

from src.core.app import BachataSyncEngine
from src.core.models import VideoAnalysisResult
from src.core.video_analyzer import VideoAnalysisInput
from src.services.caching.backend import JsonFileCache
from src.services.caching.video_analyzer import CachedVideoAnalyzer


class TestPipelineCaching(unittest.TestCase):
    def setUp(self):
        self.cache_dir = tempfile.mkdtemp()
        self.cache = JsonFileCache(self.cache_dir)
        self.mock_delegate = MagicMock()
        self.analyzer = CachedVideoAnalyzer(self.mock_delegate, self.cache)
        self.engine = BachataSyncEngine(video_analyzer=self.analyzer)

        # Create a dummy video file
        self.video_file = os.path.join(self.cache_dir, "test.mp4")
        with open(self.video_file, "w") as f:
            f.write("dummy content")

    def tearDown(self):
        shutil.rmtree(self.cache_dir)

    def test_caching_behavior(self):
        # Setup mock return value
        expected_result = VideoAnalysisResult(
            path=self.video_file,
            intensity_score=0.8,
            duration=10.0,
            thumbnail_data=b"fake_thumb"
        )
        self.mock_delegate.analyze.return_value = expected_result

        # 1. First Run: Cache Miss
        result1 = self.analyzer.analyze(VideoAnalysisInput(file_path=self.video_file))

        self.assertEqual(result1.path, self.video_file)
        self.assertEqual(result1.intensity_score, 0.8)
        self.mock_delegate.analyze.assert_called_once()

        # 2. Verify Cache File Exists
        files = list(Path(self.cache_dir).glob("*.json"))
        self.assertEqual(len(files), 1)

        # 3. Second Run: Cache Hit
        # Reset mock to ensure it's not called again
        self.mock_delegate.reset_mock()

        result2 = self.analyzer.analyze(VideoAnalysisInput(file_path=self.video_file))

        self.assertEqual(result2.path, self.video_file)
        self.assertEqual(result2.intensity_score, 0.8)
        self.assertEqual(result2.thumbnail_data, b"fake_thumb")
        self.mock_delegate.analyze.assert_not_called()

    def test_engine_integration(self):
        # Setup mock
        expected_result = VideoAnalysisResult(
            path=self.video_file,
            intensity_score=0.5,
            duration=5.0,
            thumbnail_data=None
        )
        self.mock_delegate.analyze.return_value = expected_result

        # Run engine scan
        results = self.engine.scan_video_library(self.cache_dir)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].path, self.video_file)
        self.mock_delegate.analyze.assert_called_once()

        # Run again - should hit cache
        self.mock_delegate.reset_mock()
        results2 = self.engine.scan_video_library(self.cache_dir)
        self.assertEqual(len(results2), 1)
        self.mock_delegate.analyze.assert_not_called()
