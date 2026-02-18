"""
Cached implementation of VideoAnalyzer.
"""
import base64
import hashlib
import logging
import os
from typing import Optional

from src.core.interfaces import IVideoAnalyzer
from src.core.models import VideoAnalysisResult
from src.core.video_analyzer import VideoAnalysisInput
from src.services.caching.backend import CacheBackend

logger = logging.getLogger(__name__)


class CachedVideoAnalyzer:
    """
    Caching decorator for VideoAnalyzer.
    Wraps an IVideoAnalyzer to provide transparent caching of analysis results.
    """

    def __init__(self, delegate: IVideoAnalyzer, cache: CacheBackend) -> None:
        self.delegate = delegate
        self.cache = cache

    def analyze(self, input_data: VideoAnalysisInput) -> VideoAnalysisResult:
        """
        Analyze the video, using cached result if available and valid.
        """
        file_path = input_data.file_path
        cache_key = self._generate_cache_key(file_path)

        # 1. Try Cache
        cached_data = self.cache.get(cache_key)
        if cached_data:
            try:
                # Deserialize thumbnail from base64 if present
                if cached_data.get("thumbnail_data"):
                    cached_data["thumbnail_data"] = base64.b64decode(
                        cached_data["thumbnail_data"]
                    )

                logger.debug("Cache hit for video: %s", file_path)
                return VideoAnalysisResult(**cached_data)
            except Exception as e:
                logger.warning(
                    "Cache deserialization failed for %s: %s", file_path, e
                )
                self.cache.delete(cache_key)

        # 2. Miss - Analyze
        logger.debug("Cache miss for video: %s", file_path)
        result = self.delegate.analyze(input_data)

        # 3. Store in Cache
        try:
            # Serialize to dict
            data = result.model_dump()

            # Serialize thumbnail to base64
            if data.get("thumbnail_data"):
                data["thumbnail_data"] = base64.b64encode(
                    data["thumbnail_data"]
                ).decode("utf-8")

            self.cache.set(cache_key, data)
        except Exception as e:
            logger.warning("Failed to cache result for %s: %s", file_path, e)

        return result

    def _generate_cache_key(self, file_path: str) -> str:
        """
        Generate a unique cache key based on file path and metadata.
        Invalidates cache if file changes (mtime/size).
        """
        try:
            stats = os.stat(file_path)
            # Mix path, mtime, and size
            key_str = f"{file_path}:{stats.st_mtime}:{stats.st_size}"
            return hashlib.md5(key_str.encode("utf-8")).hexdigest()
        except OSError:
            # Fallback if file not accessible (shouldn't happen here usually)
            return hashlib.md5(file_path.encode("utf-8")).hexdigest()
