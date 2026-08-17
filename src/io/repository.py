"""
Concrete implementations for repositories.
"""

import base64
import json
import logging
import os
from collections.abc import Iterable
from typing import Any

from src.core.exceptions import SerializationError, StorageError
from src.core.interfaces import VideoAnalysisRepository
from src.core.models import VideoAnalysisResult

logger = logging.getLogger(__name__)


class FileAnalysisRepository(VideoAnalysisRepository):
    """
    JSON file-backed repository for storing video analysis results.
    Implements VideoAnalysisRepository protocol.
    """

    def __init__(self, file_path: str = ".video_repository.json") -> None:
        self._file_path = file_path
        # In-memory store
        self._store: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self._file_path):
            return

        try:
            with open(self._file_path, encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    raise SerializationError(
                        "Repository file must contain a JSON object."
                    )
                self._store = data
        except json.JSONDecodeError as e:
            raise SerializationError(f"Failed to decode repository JSON: {e}") from e
        except OSError as e:
            raise StorageError(f"Failed to read repository file: {e}") from e
        except Exception as e:
            if isinstance(e, SerializationError):
                raise
            raise StorageError(f"Unexpected error loading repository: {e}") from e

    def _save_to_disk(self) -> None:
        try:
            temp_path = self._file_path + ".tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self._store, f, indent=2)
            os.replace(temp_path, self._file_path)
        except OSError as e:
            raise StorageError(f"Failed to save repository to disk: {e}") from e
        except Exception as e:
            raise StorageError(f"Unexpected error saving repository: {e}") from e

    def get_by_path(self, file_path: str) -> VideoAnalysisResult | None:
        """Retrieves a cached analysis result by its exact file path."""
        abs_path = os.path.abspath(file_path)
        data = self._store.get(abs_path)
        if not data:
            return None

        try:
            # Check if file exists and has same stats
            if not os.path.exists(abs_path):
                return None
            stat = os.stat(abs_path)

            if data.get("mtime") == stat.st_mtime and data.get("size") == stat.st_size:
                result_data = data["result"].copy()

                # Decode thumbnail from base64
                if result_data.get("thumbnail_data") is not None:
                    result_data["thumbnail_data"] = base64.b64decode(
                        result_data["thumbnail_data"]
                    )

                return VideoAnalysisResult.model_validate(result_data)
        except Exception as e:
            logger.debug(
                "Failed to deserialize VideoAnalysisResult for %s: %s", abs_path, e
            )

        return None

    def save(self, result: VideoAnalysisResult) -> None:
        """Saves an analysis result."""
        abs_path = os.path.abspath(result.path)
        try:
            if not os.path.exists(abs_path):
                return

            stat = os.stat(abs_path)
            result_data = result.model_dump()

            # Encode thumbnail to base64
            if result_data.get("thumbnail_data") is not None:
                result_data["thumbnail_data"] = base64.b64encode(
                    result_data["thumbnail_data"]
                ).decode("utf-8")

            self._store[abs_path] = {
                "mtime": stat.st_mtime,
                "size": stat.st_size,
                "result": result_data,
            }
            self._save_to_disk()
        except StorageError:
            raise
        except Exception as e:
            raise SerializationError(
                f"Failed to serialize result for {abs_path}: {e}"
            ) from e

    def get_all(self) -> Iterable[VideoAnalysisResult]:
        """Retrieves all saved analysis results."""
        results = []
        for abs_path in self._store:
            res = self.get_by_path(abs_path)
            if res:
                results.append(res)
        return results
