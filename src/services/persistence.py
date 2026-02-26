"""
Persistence services for Bachata Beat-Story Sync.
"""
import base64
import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Optional

from src.core.interfaces import AnalysisRepository, VideoAnalyzerProtocol
from src.core.models import VideoAnalysisInput, VideoAnalysisResult

logger = logging.getLogger(__name__)


class FileAnalysisRepository:
    """
    Persists analysis results to JSON files.
    """

    def __init__(self, cache_dir: str = ".cache/video_analysis"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def save_video_analysis(self, key: str, result: VideoAnalysisResult) -> None:
        """Saves a video analysis result to a JSON file."""
        try:
            file_path = self.cache_dir / f"{key}.json"

            # Serialize to dict first
            data = result.model_dump()

            # Manually handle bytes field (thumbnail_data)
            if data.get("thumbnail_data"):
                data["thumbnail_data"] = base64.b64encode(data["thumbnail_data"]).decode("utf-8")

            with open(file_path, "w") as f:
                json.dump(data, f)

        except Exception as e:
            logger.warning("Failed to save analysis cache for key %s: %s", key, e)

    def get_video_analysis(self, key: str) -> Optional[VideoAnalysisResult]:
        """Retrieves a video analysis result from cache."""
        file_path = self.cache_dir / f"{key}.json"
        if not file_path.exists():
            return None

        try:
            with open(file_path, "r") as f:
                data = json.load(f)

            # Manually handle bytes field
            if data.get("thumbnail_data"):
                if isinstance(data["thumbnail_data"], str):
                     data["thumbnail_data"] = base64.b64decode(data["thumbnail_data"])

            return VideoAnalysisResult.model_validate(data)

        except Exception as e:
            logger.warning("Failed to load analysis cache for key %s: %s", key, e)
            return None


class CachedVideoAnalyzer:
    """
    Decorator for VideoAnalyzer that caches results.
    """

    def __init__(
        self,
        real_analyzer: VideoAnalyzerProtocol,
        repository: AnalysisRepository
    ):
        self.real_analyzer = real_analyzer
        self.repository = repository

    def analyze(self, input_data: VideoAnalysisInput) -> VideoAnalysisResult:
        """
        Check cache for existing analysis, otherwise run analysis and cache it.
        """
        cache_key = self._generate_key(input_data.file_path)

        # 1. Try to get from cache
        if cached_result := self.repository.get_video_analysis(cache_key):
            logger.debug("Cache hit for %s", input_data.file_path)
            return cached_result

        # 2. Run real analysis
        logger.debug("Cache miss for %s. Analyzing...", input_data.file_path)
        result = self.real_analyzer.analyze(input_data)

        # 3. Save to cache
        self.repository.save_video_analysis(cache_key, result)

        return result

    def _generate_key(self, file_path: str) -> str:
        """
        Generates a cache key based on file path, size, and modification time.
        """
        try:
            stat = os.stat(file_path)
            # Combine path, size, and mtime to ensure cache invalidation if file changes
            key_str = f"{os.path.abspath(file_path)}:{stat.st_size}:{stat.st_mtime}"
            return hashlib.md5(key_str.encode("utf-8")).hexdigest()
        except OSError:
            # If file doesn't exist or can't be stat-ed, use path only (should fail later anyway)
            return hashlib.md5(file_path.encode("utf-8")).hexdigest()
