"""
Cached video analyzer implementation.
"""
import base64
import hashlib
import logging
import os
from typing import Optional

from src.core.interfaces import CacheBackend, IVideoAnalyzer
from src.core.models import VideoAnalysisResult, VideoAnalysisInput

logger = logging.getLogger(__name__)


class CachedVideoAnalyzer:
    """
    A decorator/wrapper for IVideoAnalyzer that caches analysis results.
    """

    def __init__(self, analyzer: IVideoAnalyzer, cache: CacheBackend) -> None:
        self.analyzer = analyzer
        self.cache = cache

    def analyze(self, input_data: VideoAnalysisInput) -> VideoAnalysisResult:
        """
        Analyzes a video file, using cached results if available.
        """
        file_path = input_data.file_path
        cache_key = self._generate_cache_key(file_path)

        cached_data = self.cache.get(cache_key)
        if cached_data:
            logger.info(f"Cache hit for video: {file_path}")
            try:
                # Decode thumbnail from base64 string back to bytes
                if cached_data.get("thumbnail_data"):
                    cached_data["thumbnail_data"] = base64.b64decode(
                        cached_data["thumbnail_data"]
                    )
                return VideoAnalysisResult(**cached_data)
            except Exception as e:
                logger.warning(f"Failed to deserialize cached data for {file_path}: {e}")
                # Fall through to re-analysis

        logger.info(f"Cache miss for video: {file_path}. Analyzing...")
        result = self.analyzer.analyze(input_data)

        # Cache the result
        try:
            data = result.model_dump()
            # Encode thumbnail bytes to base64 string for JSON serialization
            if data.get("thumbnail_data"):
                data["thumbnail_data"] = base64.b64encode(
                    data["thumbnail_data"]
                ).decode("utf-8")

            self.cache.set(cache_key, data)
        except Exception as e:
            logger.warning(f"Failed to cache result for {file_path}: {e}")

        return result

    def _generate_cache_key(self, file_path: str) -> str:
        """
        Generates a unique cache key based on file path and metadata.
        """
        try:
            stat = os.stat(file_path)
            # Combine path, size, and mtime to detect changes
            key_str = f"{file_path}:{stat.st_size}:{stat.st_mtime}"
        except OSError:
            # If file doesn't exist (should be caught by validation), just use path
            key_str = file_path

        return hashlib.md5(key_str.encode("utf-8")).hexdigest()
