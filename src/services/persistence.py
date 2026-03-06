"""
Persistence and caching services for Bachata Beat-Story Sync.
"""

import base64
import hashlib
import json
import logging
import os

from src.core.exceptions import CacheError
from src.core.interfaces import (
    AnalysisRepositoryProtocol,
    VideoAnalysisInputProtocol,
    VideoAnalyzerProtocol,
)
from src.core.models import VideoAnalysisResult

logger = logging.getLogger(__name__)


class FileAnalysisRepository(AnalysisRepositoryProtocol):
    """
    File-based repository for persisting analysis results.
    Stores data as JSON in a specified cache directory.
    """

    def __init__(self, cache_dir: str = ".bachata_cache") -> None:
        """
        Initializes the repository and creates the cache directory if needed.

        Args:
            cache_dir: The directory to store cache files.
        """
        self.cache_dir = cache_dir
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
        except OSError as e:
            raise CacheError(
                f"Failed to create cache directory {self.cache_dir}: {e}"
            ) from e

    def _get_cache_path(self, video_path: str) -> str:
        """Generates a stable cache file path based on the absolute video path."""
        # Use MD5 hash of the absolute path to create a unique, safe filename
        abs_path = os.path.abspath(video_path)
        path_hash = hashlib.md5(abs_path.encode("utf-8")).hexdigest()
        return os.path.join(self.cache_dir, f"{path_hash}.json")

    def get_video_analysis(self, video_path: str) -> VideoAnalysisResult | None:
        """
        Retrieves a cached video analysis result.
        Handles base64 decoding of thumbnail data.
        """
        cache_path = self._get_cache_path(video_path)

        if not os.path.exists(cache_path):
            return None

        try:
            with open(cache_path, encoding="utf-8") as f:
                data = json.load(f)

            # Decode thumbnail_data if present
            if data.get("thumbnail_data"):
                data["thumbnail_data"] = base64.b64decode(data["thumbnail_data"])

            return VideoAnalysisResult(**data)
        except (json.JSONDecodeError, OSError, ValueError, TypeError) as e:
            logger.warning(f"Failed to read or parse cache file {cache_path}: {e}")
            return None

    def save_video_analysis(self, result: VideoAnalysisResult) -> None:
        """
        Saves a video analysis result to the cache.
        Handles base64 encoding of thumbnail data for JSON compatibility.
        """
        cache_path = self._get_cache_path(result.path)

        try:
            # Serialize model to dict
            data = result.model_dump()

            # Encode thumbnail_data to base64 string if present
            if data.get("thumbnail_data") is not None:
                encoded = base64.b64encode(data["thumbnail_data"]).decode("utf-8")
                data["thumbnail_data"] = encoded

            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except (OSError, TypeError, ValueError) as e:
            logger.warning(f"Failed to write cache file {cache_path}: {e}")
            # We don't raise here to prevent stopping the process just because caching
            # failed. But we could log it or raise a domain exception if strict caching
            # was wanted. In this context, caching is an optimization.


class CachedVideoAnalyzer(VideoAnalyzerProtocol):
    """
    Decorator for VideoAnalyzerProtocol that adds caching capabilities.
    """

    def __init__(
        self,
        base_analyzer: VideoAnalyzerProtocol,
        repository: AnalysisRepositoryProtocol,
    ) -> None:
        """
        Initializes the CachedVideoAnalyzer.

        Args:
            base_analyzer: The underlying analyzer to use if cache misses.
            repository: The repository used to store and retrieve cache.
        """
        self._base_analyzer = base_analyzer
        self._repository = repository

    def analyze(self, input_data: VideoAnalysisInputProtocol) -> VideoAnalysisResult:
        """
        Analyzes a video file, utilizing the cache if available.
        """
        # 1. Try to get from cache
        cached_result = self._repository.get_video_analysis(input_data.file_path)
        if cached_result is not None:
            logger.debug(f"Cache hit for video: {input_data.file_path}")
            return cached_result

        # 2. If miss, run base analyzer
        logger.debug(f"Cache miss for video, analyzing: {input_data.file_path}")
        result = self._base_analyzer.analyze(input_data)

        # 3. Save to cache
        self._repository.save_video_analysis(result)

        return result
