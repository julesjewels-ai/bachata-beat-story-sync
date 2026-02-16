"""
Caching analyzers for Bachata Beat-Story Sync.
"""
import base64
import hashlib
import logging
import os
from typing import Any, Dict, Optional

from src.core.interfaces import IVideoAnalyzer, CacheBackend
from src.core.models import VideoAnalysisResult, VideoAnalysisInput

logger = logging.getLogger(__name__)


class CachedVideoAnalyzer:
    """
    A caching wrapper for IVideoAnalyzer.

    This service intercepts analysis requests, checks a persistent cache
    for existing results based on file metadata (path, size, mtime),
    and returns cached results if available. If not, it delegates to the
    underlying analyzer and caches the result.
    """

    def __init__(self, analyzer: IVideoAnalyzer, cache: CacheBackend) -> None:
        """
        Initialize the cached analyzer.

        Args:
            analyzer: The real video analyzer to delegate to on cache miss.
            cache: The cache backend to use for storage.
        """
        self.analyzer = analyzer
        self.cache = cache

    def analyze(self, input_data: VideoAnalysisInput) -> VideoAnalysisResult:
        """
        Analyzes a video file, utilizing caching to avoid redundant processing.
        """
        file_path = input_data.file_path
        cache_key = self._generate_cache_key(file_path)

        cached_data = self.cache.get(cache_key)
        if cached_data:
            try:
                # Deserialize thumbnail (Base64 str -> bytes)
                if cached_data.get("thumbnail_data"):
                    cached_data["thumbnail_data"] = base64.b64decode(
                        cached_data["thumbnail_data"]
                    )

                logger.debug("Cache hit for video: %s", file_path)
                return VideoAnalysisResult(**cached_data)
            except Exception as e:
                logger.warning(
                    "Failed to deserialize cached data for %s: %s",
                    file_path, e
                )
                # Fall through to re-analysis on deserialization failure

        logger.debug("Cache miss for video: %s", file_path)
        result = self.analyzer.analyze(input_data)

        try:
            # Serialize for cache (bytes -> Base64 str)
            cache_value = result.model_dump()
            if cache_value.get("thumbnail_data"):
                cache_value["thumbnail_data"] = base64.b64encode(
                    cache_value["thumbnail_data"]
                ).decode('utf-8')

            self.cache.set(cache_key, cache_value)
        except Exception as e:
            logger.warning("Failed to cache result for %s: %s", file_path, e)

        return result

    def _generate_cache_key(self, file_path: str) -> str:
        """
        Generates a unique cache key based on file path and metadata.
        Uses MD5 of (path + size + mtime) to detect file changes.
        """
        try:
            stat = os.stat(file_path)
            unique_str = f"{file_path}_{stat.st_size}_{stat.st_mtime}"
            return hashlib.md5(unique_str.encode('utf-8')).hexdigest()
        except OSError:
            # Fallback if stat fails (unlikely if validate_path passed)
            return hashlib.md5(file_path.encode('utf-8')).hexdigest()
