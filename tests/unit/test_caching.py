"""
Tests for the CachedVideoAnalyzer and FileAnalysisRepository.
"""

import os
from typing import Any

from src.core.cached_analyzer import CachedVideoAnalyzer
from src.core.interfaces import VideoAnalyzerProtocol
from src.core.models import VideoAnalysisResult


class MockAnalyzer(VideoAnalyzerProtocol):
    def __init__(self, result: Any) -> None:
        self.result = result
        self.call_count = 0

    def analyze(self, input_data: Any) -> Any:
        self.call_count += 1
        return self.result


class MockInput:
    def __init__(self, file_path: str) -> None:
        self.file_path = file_path


def test_cached_analyzer_miss_and_hit(tmp_path: Any) -> None:
    from src.core.repository import FileAnalysisRepository

    repo_file = str(tmp_path / ".test_cache.json")
    repo = FileAnalysisRepository(cache_file_name=repo_file)

    # Needs to match VideoAnalysisResult structure for set/get to work.
    dummy_result = VideoAnalysisResult(
        path=os.path.abspath("dummy.mp4"),
        intensity_score=0.5,
        duration=10.0,
        is_vertical=False,
    )

    base_analyzer = MockAnalyzer(dummy_result)
    cached_analyzer = CachedVideoAnalyzer(base_analyzer, repo)

    input_file = tmp_path / "dummy.mp4"
    input_data = MockInput(str(input_file))

    # First call: should be a miss, call base_analyzer
    res1 = cached_analyzer.analyze(input_data)
    assert base_analyzer.call_count == 1
    assert res1 == dummy_result

    # We must save the repo to disk or mock the stat
    # Actually FileAnalysisRepository does an os.stat, so the file MUST exist!
    # Let's create an empty dummy file so stat passes
    with open(input_file, "w") as f:
        f.write("test")

    # Retry caching now that file exists
    res1 = cached_analyzer.analyze(input_data)
    assert base_analyzer.call_count == 2

    # Third call: should be a hit (no base analyzer call)
    res2 = cached_analyzer.analyze(input_data)
    assert base_analyzer.call_count == 2
    assert res2 is not None
    assert res2.path == os.path.abspath("dummy.mp4")

    # Now verify string input works as well
    res3 = cached_analyzer.analyze(str(input_file))
    assert base_analyzer.call_count == 2  # still hit
    assert res3 is not None
    assert res3.path == os.path.abspath("dummy.mp4")
