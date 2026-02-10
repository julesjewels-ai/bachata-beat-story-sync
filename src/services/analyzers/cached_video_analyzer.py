"""
Cached implementation of the VideoAnalyzer.
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
    A caching wrapper for video analyzers.
    It stores analysis results based on file path and modification time.
    """

    def __init__(self, analyzer: IVideoAnalyzer, cache: CacheBackend) -> None:
        self.analyzer = analyzer
        self.cache = cache

    def analyze(self, input_data: VideoAnalysisInput) -> VideoAnalysisResult:
        """
        Analyzes a video file, checking the cache first.
        """
        file_path = input_data.file_path

        # Calculate cache key based on path, size, and mtime
        cache_key = self._generate_cache_key(file_path)

        if cache_key:
            cached_data = self.cache.get(cache_key)
            if cached_data:
                try:
                    return self._deserialize(cached_data)
                except Exception as e:
                    logger.warning(
                        f"Failed to deserialize cached data for {file_path}: {e}"
                    )
                    # Proceed to re-analyze if cache is corrupted

        # Cache miss or invalid cache
        result = self.analyzer.analyze(input_data)

        if cache_key:
            try:
                serialized = self._serialize(result)
                self.cache.set(cache_key, serialized)
            except Exception as e:
                logger.warning(f"Failed to cache result for {file_path}: {e}")

        return result

    def _generate_cache_key(self, file_path: str) -> Optional[str]:
        """Generates a unique cache key based on file metadata."""
        try:
            stat = os.stat(file_path)
            # Combine path, size, and mtime
            key_str = f"{file_path}:{stat.st_size}:{stat.st_mtime}"
            return hashlib.sha256(key_str.encode('utf-8')).hexdigest()
        except OSError as e:
            logger.warning(f"Could not stat file {file_path}: {e}")
            return None

    def _serialize(self, result: VideoAnalysisResult) -> Dict[str, Any]:
        """Serializes the result to a JSON-compatible dictionary."""
        data = result.model_dump()

        # Encode bytes to base64 string for JSON
        if data.get('thumbnail_data'):
            if isinstance(data['thumbnail_data'], bytes):
                data['thumbnail_data'] = base64.b64encode(
                    data['thumbnail_data']
                ).decode('utf-8')

        return data

    def _deserialize(self, data: Dict[str, Any]) -> VideoAnalysisResult:
        """Deserializes a dictionary back to VideoAnalysisResult."""
        # Decode base64 string back to bytes
        if data.get('thumbnail_data'):
            if isinstance(data['thumbnail_data'], str):
                data['thumbnail_data'] = base64.b64decode(
                    data['thumbnail_data']
                )

        return VideoAnalysisResult(**data)
