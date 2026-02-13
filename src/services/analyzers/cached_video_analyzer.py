"""
Cached implementation of the VideoAnalyzer using the Decorator pattern.
"""
import hashlib
import os
import base64
import logging
from typing import Optional, Any, Dict
from src.core.interfaces import IVideoAnalyzer
from src.core.models import VideoAnalysisInput, VideoAnalysisResult
from src.services.caching.interfaces import CacheBackend

logger = logging.getLogger(__name__)


class CachedVideoAnalyzer:
    """
    Decorator/Wrapper for IVideoAnalyzer that adds caching capabilities.
    """

    def __init__(self, inner: IVideoAnalyzer, cache: CacheBackend) -> None:
        self.inner = inner
        self.cache = cache

    def analyze(self, input_data: VideoAnalysisInput) -> VideoAnalysisResult:
        """
        Analyzes a video file, utilizing cache if available.
        """
        file_path = input_data.file_path

        # Calculate Cache Key
        cache_key = self._generate_cache_key(file_path)
        if not cache_key:
            return self.inner.analyze(input_data)

        # Check Cache
        cached_data = self.cache.get(cache_key)
        if cached_data:
            try:
                # Deserialize
                result = self._deserialize_result(cached_data)
                logger.debug(f"Cache hit for {file_path}")
                return result
            except Exception as e:
                logger.warning(
                    f"Failed to deserialize cache for {file_path}: {e}. "
                    "Re-analyzing."
                )
                self.cache.delete(cache_key)

        # Cache Miss
        logger.debug(f"Cache miss for {file_path}. Analyzing...")
        result = self.inner.analyze(input_data)

        # Serialize and Cache
        try:
            serialized_data = self._serialize_result(result)
            self.cache.set(cache_key, serialized_data)
        except Exception as e:
            logger.warning(f"Failed to cache result for {file_path}: {e}")

        return result

    def _generate_cache_key(self, file_path: str) -> Optional[str]:
        """Generates a cache key based on file path, mtime, and size."""
        try:
            stat = os.stat(file_path)
            key_str = f"{file_path}:{stat.st_mtime}:{stat.st_size}"
            return hashlib.md5(key_str.encode('utf-8')).hexdigest()
        except OSError:
            return None

    def _serialize_result(self, result: VideoAnalysisResult) -> Dict[str, Any]:
        """Serializes VideoAnalysisResult to a JSON-compatible dict."""
        # Handle Pydantic v1 vs v2 compatibility
        if hasattr(result, 'model_dump'):
            data = result.model_dump()
        else:
            data = result.dict()

        if data.get('thumbnail_data'):
            # Convert bytes to base64 string
            data['thumbnail_data'] = base64.b64encode(
                data['thumbnail_data']
            ).decode('utf-8')

        return data

    def _deserialize_result(self, data: Dict[str, Any]) -> VideoAnalysisResult:
        """Deserializes a dict into VideoAnalysisResult."""
        # Avoid mutating the cached dict
        data_copy = data.copy()

        if data_copy.get('thumbnail_data'):
            # Convert base64 string back to bytes
            try:
                data_copy['thumbnail_data'] = base64.b64decode(
                    data_copy['thumbnail_data']
                )
            except Exception:
                # If decoding fails, just drop the thumbnail
                data_copy['thumbnail_data'] = None

        return VideoAnalysisResult(**data_copy)
