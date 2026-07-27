"""
Decorator for caching video analysis.
"""

import logging
from typing import Any

from src.core.interfaces import AnalysisRepositoryProtocol, VideoAnalyzerProtocol

logger = logging.getLogger(__name__)


class CachedVideoAnalyzer(VideoAnalyzerProtocol):
    """
    Decorator that adds caching to any VideoAnalyzerProtocol implementation.
    """

    def __init__(
        self,
        base_analyzer: VideoAnalyzerProtocol,
        repository: AnalysisRepositoryProtocol,
    ) -> None:
        self._base_analyzer = base_analyzer
        self._repository = repository

    def analyze(self, input_data: Any) -> Any | None:
        """
        Attempts to fetch the result from the cache repository.
        On a miss, delegates to the base analyzer and caches the result.
        """
        file_path = (
            input_data
            if isinstance(input_data, str)
            else getattr(input_data, "file_path", None)
        )
        if not file_path:
            return self._base_analyzer.analyze(input_data)

        try:
            cached_result = self._repository.get(file_path)
            if cached_result is not None:
                return cached_result
        except Exception as e:
            logger.warning("Cache retrieval failed for %s: %s", file_path, e)

        result = self._base_analyzer.analyze(input_data)

        if result is not None:
            try:
                self._repository.set(file_path, result)
            except Exception as e:
                logger.warning("Cache storage failed for %s: %s", file_path, e)

        return result
