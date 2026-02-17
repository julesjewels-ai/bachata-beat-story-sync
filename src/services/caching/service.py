"""
Service layer for caching strategies.
"""
import base64
import hashlib
import logging
import os
from typing import Any, Dict, Optional

from src.core.interfaces import IVideoAnalyzer, CacheBackend
from src.core.models import VideoAnalysisResult
from src.core.video_analyzer import VideoAnalysisInput

logger = logging.getLogger(__name__)


class CachedVideoAnalyzer:
    """
    A caching decorator/proxy for IVideoAnalyzer.
    Uses a CacheBackend to store results based on file metadata.
    """

    def __init__(self, analyzer: IVideoAnalyzer, cache: CacheBackend):
        """
        Args:
            analyzer: The underlying video analyzer to delegate to on cache miss.
            cache: The storage backend for caching results.
        """
        self.analyzer = analyzer
        self.cache = cache

    def analyze(self, input_data: VideoAnalysisInput) -> VideoAnalysisResult:
        """
        Analyzes the video, checking the cache first.
        """
        file_path = input_data.file_path

        # Calculate cache key based on file metadata
        cache_key = self._generate_cache_key(file_path)

        if cache_key:
            cached_data = self.cache.get(cache_key)
            if cached_data:
                try:
                    logger.debug("Cache hit for %s", file_path)
                    return self._deserialize_result(cached_data)
                except Exception as e:
                    logger.warning(
                        "Failed to deserialize cached result for %s: %s",
                        file_path, e
                    )

        # Cache miss or invalid cache
        logger.info("Analyzing video (cache miss): %s", file_path)
        result = self.analyzer.analyze(input_data)

        if cache_key:
            try:
                serialized = self._serialize_result(result)
                self.cache.set(cache_key, serialized)
            except Exception as e:
                logger.warning(
                    "Failed to cache result for %s: %s", file_path, e
                )

        return result

    def _generate_cache_key(self, file_path: str) -> Optional[str]:
        """Generates a unique cache key based on file path and metadata."""
        try:
            stats = os.stat(file_path)
            # Mix path, size, and modification time to detect changes
            key_data = f"{file_path}:{stats.st_size}:{stats.st_mtime}"
            return hashlib.md5(key_data.encode('utf-8')).hexdigest()
        except OSError:
            logger.warning("Could not access file for cache key: %s", file_path)
            return None

    def _serialize_result(self, result: VideoAnalysisResult) -> Dict[str, Any]:
        """Serializes the result to a JSON-compatible dictionary."""
        # Use Pydantic's model_dump but handle bytes manually for JSON
        data = result.model_dump()
        if data.get('thumbnail_data'):
            data['thumbnail_data'] = base64.b64encode(
                data['thumbnail_data']
            ).decode('utf-8')
        return data

    def _deserialize_result(self, data: Dict[str, Any]) -> VideoAnalysisResult:
        """Deserializes the dictionary back to a VideoAnalysisResult."""
        if data.get('thumbnail_data') and isinstance(data['thumbnail_data'], str):
            data['thumbnail_data'] = base64.b64decode(data['thumbnail_data'])
        return VideoAnalysisResult(**data)
