"""
Service implementations for caching.
"""
import base64
import hashlib
import logging
import os
from typing import Dict, Any

from src.core.interfaces import IVideoAnalyzer, CacheBackend
from src.core.models import VideoAnalysisResult, VideoAnalysisInput

logger = logging.getLogger(__name__)


class CachedVideoAnalyzer:
    """
    A decorator for IVideoAnalyzer that caches analysis results.
    """

    def __init__(self, analyzer: IVideoAnalyzer, cache: CacheBackend) -> None:
        """
        Initializes the cached analyzer.

        Args:
            analyzer: The underlying video analyzer to use on cache miss.
            cache: The cache backend to store results.
        """
        self._analyzer = analyzer
        self._cache = cache

    def analyze(self, input_data: VideoAnalysisInput) -> VideoAnalysisResult:
        """
        Analyzes a video file, using cached results if available.
        """
        cache_key = self._generate_cache_key(input_data.file_path)

        # Try cache
        try:
            cached_data = self._cache.get(cache_key)
            if cached_data:
                logger.info(f"Cache hit for {input_data.file_path}")
                return self._deserialize_result(cached_data)
        except Exception as e:
            logger.warning(f"Cache read error for {input_data.file_path}: {e}")

        # Cache miss
        logger.info(f"Cache miss for {input_data.file_path}. Analyzing...")
        result = self._analyzer.analyze(input_data)

        # Store in cache
        try:
            serialized = self._serialize_result(result)
            self._cache.set(cache_key, serialized)
        except Exception as e:
            logger.warning(f"Cache write error for {input_data.file_path}: {e}")

        return result

    def _generate_cache_key(self, file_path: str) -> str:
        """
        Generates a cache key based on file path and metadata.
        """
        try:
            stats = os.stat(file_path)
            # Use path, modification time, and size for uniqueness
            key_data = f"{file_path}:{stats.st_mtime}:{stats.st_size}"
            return hashlib.md5(key_data.encode("utf-8")).hexdigest()
        except OSError:
            # Fallback to just path hash if stat fails (unlikely if file exists)
            return hashlib.md5(file_path.encode("utf-8")).hexdigest()

    def _serialize_result(self, result: VideoAnalysisResult) -> Dict[str, Any]:
        """
        Serializes the result to a JSON-compatible dictionary.
        Handles binary data (thumbnail) by base64 encoding.
        """
        data = result.model_dump()
        if result.thumbnail_data:
            data["thumbnail_data"] = base64.b64encode(result.thumbnail_data).decode("utf-8")
        return data

    def _deserialize_result(self, data: Dict[str, Any]) -> VideoAnalysisResult:
        """
        Deserializes the result from a dictionary.
        Handles binary data (thumbnail) by base64 decoding.
        """
        if data.get("thumbnail_data"):
            # If it's a string, decode it. If it's None, it stays None.
            if isinstance(data["thumbnail_data"], str):
                data["thumbnail_data"] = base64.b64decode(data["thumbnail_data"])

        return VideoAnalysisResult.model_validate(data)
