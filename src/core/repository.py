"""
Repository pattern for Data Persistence and Caching of Pydantic Domain Models.
Implements the Dependency Inversion Principle using a generic ModelRepository Protocol.
"""

import json
import logging
import os
from typing import Generic, Protocol, TypeVar

from pydantic import BaseModel

from src.core.exceptions import NotFoundError, StorageError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class ModelRepository(Protocol, Generic[T]):
    """Generic Protocol for saving and retrieving Pydantic domain models."""

    def get(self, id: str) -> T:
        """Retrieve a model by its identifier."""
        ...

    def save(self, id: str, model: T) -> None:
        """Save a model using its identifier."""
        ...

    def delete(self, id: str) -> None:
        """Delete a model by its identifier."""
        ...


class FileSystemRepository(Generic[T]):
    """
    Concrete implementation of ModelRepository using the local file system.
    Serializes and deserializes Pydantic models to JSON files.
    """

    def __init__(self, base_dir: str, model_type: type[T]) -> None:
        self.base_dir = base_dir
        self.model_type = model_type

        try:
            os.makedirs(self.base_dir, exist_ok=True)
        except OSError as e:
            logger.error("Failed to create base directory %s: %s", self.base_dir, e)
            raise StorageError(
                f"Cannot initialize repository at {self.base_dir}"
            ) from e

    def _get_path(self, id: str) -> str:
        """Construct the file path for a given identifier."""
        safe_id = os.path.basename(id)
        return os.path.join(self.base_dir, f"{safe_id}.json")

    def get(self, id: str) -> T:
        """Retrieve a model by its identifier."""
        path = self._get_path(id)
        if not os.path.exists(path):
            raise NotFoundError(f"Entity '{id}' not found in {self.base_dir}")

        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            return self.model_type.model_validate(data)
        except Exception as e:
            logger.error("Failed to read entity %s from %s: %s", id, path, e)
            raise StorageError(f"Failed to read entity '{id}'") from e

    def save(self, id: str, model: T) -> None:
        """Save a model using its identifier."""
        path = self._get_path(id)

        try:
            # Write to a temp file first for atomicity
            temp_path = f"{path}.tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(model.model_dump(), f, indent=2)
            os.replace(temp_path, path)
            logger.debug("Saved entity %s to %s", id, path)
        except Exception as e:
            logger.error("Failed to save entity %s to %s: %s", id, path, e)
            raise StorageError(f"Failed to save entity '{id}'") from e

    def delete(self, id: str) -> None:
        """Delete a model by its identifier."""
        path = self._get_path(id)
        if not os.path.exists(path):
            raise NotFoundError(f"Entity '{id}' not found in {self.base_dir}")

        try:
            os.remove(path)
            logger.debug("Deleted entity %s from %s", id, path)
        except Exception as e:
            logger.error("Failed to delete entity %s from %s: %s", id, path, e)
            raise StorageError(f"Failed to delete entity '{id}'") from e
