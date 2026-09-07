"""
Generic Repository pattern implementation for domain models.
"""
import json
import logging
import os
from typing import Generic, Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from src.core.exceptions import RepositoryError, StorageError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class ModelRepository(Protocol[T]):
    """Protocol defining the contract for domain model persistence."""

    def get(self, entity_id: str) -> T | None:
        """Retrieve an entity by its ID."""
        ...

    def save(self, entity_id: str, entity: T) -> None:
        """Persist an entity with the given ID."""
        ...

    def delete(self, entity_id: str) -> None:
        """Remove an entity by its ID."""
        ...


class FileSystemRepository(Generic[T]):
    """
    Concrete implementation of ModelRepository using file system.
    """

    def __init__(self, storage_dir: str, model_class: type[T]) -> None:
        self.storage_dir = storage_dir
        self.model_class = model_class
        try:
            os.makedirs(self.storage_dir, exist_ok=True)
        except OSError as e:
            msg = f"Failed to create storage directory {self.storage_dir}: {e}"
            raise StorageError(msg) from e

    def _get_path(self, entity_id: str) -> str:
        safe_id = "".join(c for c in entity_id if c.isalnum() or c in ("-", "_"))
        return os.path.join(self.storage_dir, f"{safe_id}.json")

    def get(self, entity_id: str) -> T | None:
        path = self._get_path(entity_id)
        if not os.path.exists(path):
            return None
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
                return self.model_class.model_validate(data)
        except (OSError, ValidationError, json.JSONDecodeError) as e:
            logger.error("Failed to read entity %s: %s", entity_id, e)
            raise RepositoryError(f"Failed to read entity {entity_id}") from e

    def save(self, entity_id: str, entity: T) -> None:
        path = self._get_path(entity_id)
        try:
            temp_path = f"{path}.tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(entity.model_dump_json(indent=2))
            os.replace(temp_path, path)
        except OSError as e:
            logger.error("Failed to save entity %s: %s", entity_id, e)
            raise StorageError(f"Failed to save entity {entity_id}") from e

    def delete(self, entity_id: str) -> None:
        path = self._get_path(entity_id)
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError as e:
                raise StorageError(f"Failed to delete entity {entity_id}") from e
