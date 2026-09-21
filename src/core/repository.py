"""
Repository pattern definitions for domain models.
"""

import json
import os
from typing import Generic, Protocol, TypeVar

from pydantic import BaseModel

from src.core.exceptions import RepositoryError, StorageError

T = TypeVar("T", bound=BaseModel)


class ModelRepository(Protocol, Generic[T]):
    """
    Protocol defining the generic repository interface.
    """

    def save(self, model: T) -> None:
        """Saves a model entity."""
        ...

    def get(self, entity_id: str) -> T | None:
        """Retrieves a model entity by ID."""
        ...

    def list_all(self) -> list[T]:
        """Lists all entities."""
        ...


class FileSystemRepository(Generic[T]):
    """
    Concrete implementation of ModelRepository using local filesystem and JSON.
    """

    def __init__(self, base_path: str, model_class: type[T]) -> None:
        self.base_path = base_path
        self.model_class = model_class

        try:
            os.makedirs(self.base_path, exist_ok=True)
        except OSError as e:
            raise StorageError(f"Failed to create repository directory: {e}") from e

    def _get_file_path(self, entity_id: str) -> str:
        return os.path.join(self.base_path, f"{entity_id}.json")

    def save(self, model: T) -> None:
        try:
            # Assuming models have an 'id' field as specified in instructions or inherently.
            entity_id = getattr(model, "id")
            if not entity_id:
                 raise ValueError("Model does not have an 'id' attribute.")

            file_path = self._get_file_path(str(entity_id))
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(model.model_dump_json(indent=2))
        except (OSError, ValueError) as e:
            raise StorageError(f"Failed to save entity to {self.base_path}: {e}") from e

    def get(self, entity_id: str) -> T | None:
        file_path = self._get_file_path(entity_id)
        if not os.path.exists(file_path):
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return self.model_class.model_validate(data)
        except Exception as e:
            raise StorageError(f"Failed to load entity {entity_id}: {e}") from e

    def list_all(self) -> list[T]:
        entities = []
        try:
            for filename in os.listdir(self.base_path):
                if filename.endswith(".json"):
                    entity_id = filename[:-5]
                    entity = self.get(entity_id)
                    if entity:
                        entities.append(entity)
            return entities
        except OSError as e:
             raise StorageError(f"Failed to list entities in {self.base_path}: {e}") from e
