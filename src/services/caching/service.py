"""
Service layer for caching.
"""
import base64
import hashlib
import logging
import os
from typing import Optional, Dict, Any

from src.core.interfaces import CacheBackend, IVideoAnalyzer
from src.core.models import VideoAnalysisResult, VideoAnalysisInput

logger = logging.getLogger(__name__)


class CachedVideoAnalyzer:
    """
    A caching wrapper for IVideoAnalyzer services.
    It caches the analysis result based on the file path, size, and modification time.
    Implements IVideoAnalyzer protocol.
    """

    def __init__(self, delegate: IVideoAnalyzer, cache: CacheBackend):
        """
        Initializes the cached analyzer.

        Args:
            delegate: The underlying video analyzer service.
            cache: The cache backend to use.
        """
        self.delegate = delegate
        self.cache = cache

    def analyze(self, input_data: VideoAnalysisInput) -> VideoAnalysisResult:
        """
        Analyzes a video file, using cached results if available.
        """
        file_path = input_data.file_path

        # Validate file exists (delegate would do it, but we need mtime/size)
        # If file is gone, getmtime raises FileNotFoundError.
        if not os.path.exists(file_path):
             return self.delegate.analyze(input_data)

        try:
            mtime = os.path.getmtime(file_path)
            size = os.path.getsize(file_path)
        except OSError:
            # If we can't stat the file, skip caching and delegate
            return self.delegate.analyze(input_data)

        # Create a deterministic cache key
        key_base = f"{file_path}:{mtime}:{size}"
        cache_key = hashlib.md5(key_base.encode('utf-8')).hexdigest()

        # Try to retrieve from cache
        cached_data = self.cache.get(cache_key)
        if cached_data:
            try:
                # logger.debug("Cache hit for %s", file_path) # Debug level to avoid spam
                return self._deserialize_result(cached_data)
            except Exception as e:
                logger.warning("Failed to deserialize cached data for %s: %s", file_path, e)
                # Fallback to fresh analysis

        # Perform fresh analysis
        # logger.info("Cache miss for %s. Analyzing...", file_path) # Info level might be spammy for batch
        result = self.delegate.analyze(input_data)

        # Cache the result
        try:
            serialized = self._serialize_result(result)
            self.cache.set(cache_key, serialized)
        except Exception as e:
             logger.warning("Failed to serialize/cache result for %s: %s", file_path, e)

        return result

    def _serialize_result(self, result: VideoAnalysisResult) -> Dict[str, Any]:
        """Serializes the result to a JSON-compatible dictionary."""
        data = result.model_dump()
        if data.get('thumbnail_data'):
            # Convert bytes to base64 string
            data['thumbnail_data'] = base64.b64encode(data['thumbnail_data']).decode('ascii')
        return data

    def _deserialize_result(self, data: Dict[str, Any]) -> VideoAnalysisResult:
        """Deserializes the result from a dictionary."""
        if data.get('thumbnail_data') and isinstance(data['thumbnail_data'], str):
            # Convert base64 string back to bytes
            data['thumbnail_data'] = base64.b64decode(data['thumbnail_data'])
        return VideoAnalysisResult(**data)
