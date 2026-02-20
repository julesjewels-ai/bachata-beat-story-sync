"""
Video analysis caching implementation.
"""
import base64
import hashlib
import logging
import os
from typing import Optional

from src.core.interfaces import IVideoAnalyzer, CacheBackend
from src.core.models import VideoAnalysisResult
from src.core.video_analyzer import VideoAnalysisInput

logger = logging.getLogger(__name__)


class CachedVideoAnalyzer:
    """
    A decorator for VideoAnalyzer that caches results to avoid re-processing.
    """

    def __init__(self, inner: IVideoAnalyzer, cache: CacheBackend) -> None:
        """
        Initialize the cached video analyzer.

        Args:
            inner: The underlying video analyzer service.
            cache: The cache backend to use.
        """
        self.inner = inner
        self.cache = cache

    def analyze(self, input_data: VideoAnalysisInput) -> VideoAnalysisResult:
        """
        Analyzes a video file, using cached results if available.

        Generates a cache key based on the file path, size, and modification time.
        """
        file_path = input_data.file_path
        cache_key = self._generate_cache_key(file_path)

        # Try to retrieve from cache
        if cached_data := self.cache.get(cache_key):
            try:
                return self._deserialize_result(cached_data)
            except Exception as e:
                logger.warning(
                    "Failed to deserialize cached result for %s: %s",
                    file_path, e
                )

        # Cache miss or error -> Compute
        logger.info("Cache miss for %s. Analyzing...", file_path)
        result = self.inner.analyze(input_data)

        # Store in cache
        try:
            serialized = self._serialize_result(result)
            self.cache.set(cache_key, serialized)
        except Exception as e:
            logger.warning(
                "Failed to cache result for %s: %s",
                file_path, e
            )

        return result

    def _generate_cache_key(self, file_path: str) -> str:
        """Generates a unique cache key for the file state."""
        try:
            stats = os.stat(file_path)
            # Combine path, size, and mtime for uniqueness
            key_data = f"{file_path}|{stats.st_size}|{stats.st_mtime}"
            return hashlib.md5(key_data.encode("utf-8")).hexdigest()
        except OSError:
            # Fallback for missing files (should be caught by validation, but just in case)
            return hashlib.md5(file_path.encode("utf-8")).hexdigest()

    def _serialize_result(self, result: VideoAnalysisResult) -> dict:
        """Converts result to a JSON-serializable dictionary."""
        data = result.model_dump()
        if data.get("thumbnail_data"):
            data["thumbnail_data"] = base64.b64encode(data["thumbnail_data"]).decode("ascii")
        return data

    def _deserialize_result(self, data: dict) -> VideoAnalysisResult:
        """Reconstructs result from a dictionary."""
        if data.get("thumbnail_data"):
            if isinstance(data["thumbnail_data"], str):
                 data["thumbnail_data"] = base64.b64decode(data["thumbnail_data"])
        return VideoAnalysisResult.model_validate(data)
