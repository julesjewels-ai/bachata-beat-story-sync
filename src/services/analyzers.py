"""
Service layer implementations for analyzers.
"""
import hashlib
import json
import base64
import os
import logging
from typing import Dict, Any
from src.core.interfaces import IVideoAnalyzer, CacheBackend
from src.core.models import VideoAnalysisResult, VideoAnalysisInput

logger = logging.getLogger(__name__)


class CachedVideoAnalyzer:
    """
    A decorator/proxy for IVideoAnalyzer that caches results.

    This implementation wraps a concrete IVideoAnalyzer and uses a CacheBackend
    to store and retrieve analysis results, avoiding expensive re-computation.
    """
    def __init__(self, analyzer: IVideoAnalyzer, cache: CacheBackend):
        self.analyzer = analyzer
        self.cache = cache

    def analyze(self, input_data: VideoAnalysisInput) -> VideoAnalysisResult:
        """
        Analyzes the video, using cache if available.
        """
        file_path = input_data.file_path
        cache_key = self._generate_cache_key(file_path)

        # Try Cache
        if cached_json := self.cache.get(cache_key):
            try:
                data = json.loads(cached_json)
                return self._deserialize_result(data)
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Cache corruption for {file_path}: {e}")

        # Analyze
        result = self.analyzer.analyze(input_data)

        # Update Cache
        try:
            serialized = self._serialize_result(result)
            self.cache.set(cache_key, serialized)
        except Exception as e:
            logger.warning(f"Failed to cache result for {file_path}: {e}")

        return result

    def _generate_cache_key(self, file_path: str) -> str:
        """Generates a unique cache key based on file content/metadata."""
        try:
            stats = os.stat(file_path)
            # Combine path, modification time, and size
            key_data = f"{file_path}|{stats.st_mtime}|{stats.st_size}"
            return hashlib.md5(key_data.encode('utf-8')).hexdigest()
        except OSError:
            # If file access fails (unlikely given validation), return path hash
            return hashlib.md5(file_path.encode('utf-8')).hexdigest()

    def _serialize_result(self, result: VideoAnalysisResult) -> str:
        """Serializes the result to JSON, handling bytes."""
        # Handle Pydantic v1/v2 compatibility
        if hasattr(result, 'model_dump'):
            data = result.model_dump()
        else:
            data = result.dict()  # type: ignore

        # Handle bytes (thumbnail)
        thumb = data.get('thumbnail_data')
        if isinstance(thumb, bytes):
            data['thumbnail_data'] = base64.b64encode(thumb).decode('ascii')

        return json.dumps(data)

    def _deserialize_result(self, data: Dict[str, Any]) -> VideoAnalysisResult:
        """Deserializes JSON data back to VideoAnalysisResult."""
        thumb = data.get('thumbnail_data')
        if isinstance(thumb, str):
            try:
                data['thumbnail_data'] = base64.b64decode(thumb)
            except ValueError:
                logger.warning("Failed to decode thumbnail from cache")
                data['thumbnail_data'] = None

        return VideoAnalysisResult(**data)
