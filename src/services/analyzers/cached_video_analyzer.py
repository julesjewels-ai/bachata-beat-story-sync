"""
Cached implementation of the VideoAnalyzer.
"""
import base64
import hashlib
import logging
import os
from typing import Dict, Any, cast

from src.core.interfaces import IVideoAnalyzer, CacheBackend
from src.core.models import VideoAnalysisInput, VideoAnalysisResult

logger = logging.getLogger(__name__)


class CachedVideoAnalyzer:
    """
    A caching wrapper around an IVideoAnalyzer.
    Persists analysis results to a CacheBackend to avoid re-processing.
    """

    def __init__(self, analyzer: IVideoAnalyzer, cache: CacheBackend) -> None:
        self.analyzer = analyzer
        self.cache = cache

    def analyze(self, input_data: VideoAnalysisInput) -> VideoAnalysisResult:
        """
        Analyzes a video file, utilizing the cache if available.
        """
        file_path = input_data.file_path

        try:
            cache_key = self._generate_cache_key(file_path)
            cached_data = self.cache.get(cache_key)

            if cached_data:
                logger.info(f"Cache hit for {file_path}")
                try:
                    return self._deserialize_result(cast(Dict[str, Any], cached_data))
                except Exception as e:
                    logger.warning(
                        f"Failed to deserialize cached result for {file_path}: {e}"
                    )
                    # Fallback to re-analysis
        except Exception as e:
            logger.warning(f"Cache lookup failed for {file_path}: {e}")

        logger.info(f"Cache miss for {file_path}. Analyzing...")
        result = self.analyzer.analyze(input_data)

        try:
            cache_key = self._generate_cache_key(file_path)
            serialized = self._serialize_result(result)
            self.cache.set(cache_key, serialized)
        except Exception as e:
            logger.warning(f"Failed to cache result for {file_path}: {e}")

        return result

    def _generate_cache_key(self, file_path: str) -> str:
        """Generates a unique cache key based on file path, size, and mtime."""
        try:
            stat = os.stat(file_path)
            # Create a string combining path, size, and mtime
            unique_str = f"{file_path}:{stat.st_size}:{stat.st_mtime}"
            return hashlib.sha256(unique_str.encode('utf-8')).hexdigest()
        except OSError:
            # If file is inaccessible, use path hash but risk stale cache
            return hashlib.sha256(file_path.encode('utf-8')).hexdigest()

    def _serialize_result(self, result: VideoAnalysisResult) -> Dict[str, Any]:
        """Serializes the result to a JSON-compatible dictionary."""
        # Get dict with python types (bytes remain bytes)
        data = result.model_dump()

        # Convert bytes to base64 string
        thumb_data = data.get('thumbnail_data')
        if thumb_data and isinstance(thumb_data, bytes):
             data['thumbnail_data'] = base64.b64encode(thumb_data).decode('utf-8')

        return data

    def _deserialize_result(self, data: Dict[str, Any]) -> VideoAnalysisResult:
        """Deserializes the dictionary back to a VideoAnalysisResult."""
        # Copy to avoid mutating cache input
        data_copy = data.copy()

        # Handle base64 decoding for thumbnail_data if present
        thumbnail_b64 = data_copy.get('thumbnail_data')
        if thumbnail_b64 and isinstance(thumbnail_b64, str):
             try:
                 data_copy['thumbnail_data'] = base64.b64decode(thumbnail_b64)
             except ValueError:
                 logger.warning("Failed to decode thumbnail data from cache")
                 data_copy['thumbnail_data'] = None

        return VideoAnalysisResult(**data_copy)
