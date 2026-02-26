import os
import shutil
import tempfile
import pytest
from unittest.mock import Mock
from src.services.persistence import FileAnalysisRepository, CachedVideoAnalyzer
from src.core.models import VideoAnalysisResult, VideoAnalysisInput

class TestPersistence:
    @pytest.fixture
    def cache_dir(self):
        # Create a temp directory for cache
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # Cleanup
        shutil.rmtree(temp_dir)

    def test_repository_save_and_load(self, cache_dir):
        repo = FileAnalysisRepository(cache_dir=cache_dir)

        # Create a dummy result
        result = VideoAnalysisResult(
            path="/tmp/fake.mp4",
            intensity_score=0.5,
            duration=10.0,
            is_vertical=False,
            thumbnail_data=b"\x00\x01\x02"
        )

        key = "test_key"
        repo.save_video_analysis(key, result)

        # Verify file exists
        assert os.path.exists(os.path.join(cache_dir, f"{key}.json"))

        # Load back
        loaded = repo.get_video_analysis(key)
        assert loaded is not None
        assert loaded.path == result.path
        assert loaded.thumbnail_data == result.thumbnail_data

    def test_cached_analyzer_hit_miss(self, cache_dir):
        repo = FileAnalysisRepository(cache_dir=cache_dir)
        mock_real_analyzer = Mock()

        # Create a dummy file for input
        dummy_path = os.path.join(cache_dir, "dummy.mp4")
        with open(dummy_path, "w") as f:
            f.write("content")

        # Create a dummy result
        expected_result = VideoAnalysisResult(
            path=dummy_path,
            intensity_score=0.8,
            duration=5.0,
            is_vertical=True,
            thumbnail_data=None
        )
        mock_real_analyzer.analyze.return_value = expected_result

        analyzer = CachedVideoAnalyzer(mock_real_analyzer, repo)
        input_data = VideoAnalysisInput(file_path=dummy_path)

        # 1. First call: Miss
        result1 = analyzer.analyze(input_data)
        # We compare dict representation because objects might be different instances
        assert result1.model_dump() == expected_result.model_dump()
        mock_real_analyzer.analyze.assert_called_once()

        # 2. Second call: Hit
        result2 = analyzer.analyze(input_data)
        assert result2.path == expected_result.path
        assert result2.intensity_score == expected_result.intensity_score
        assert mock_real_analyzer.analyze.call_count == 1 # Still 1
