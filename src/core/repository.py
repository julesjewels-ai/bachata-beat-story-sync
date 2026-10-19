"""
Generic repository pattern for domain model persistence.
"""

import json
import os
from typing import Generic, Protocol, TypeVar

from pydantic import BaseModel

from src.core.exceptions import EntityNotFoundError, StorageError

T = TypeVar("T", bound=BaseModel)


class ModelRepository(Protocol, Generic[T]):
    """
    Protocol for a repository that persists and retrieves Pydantic models.
    """

    def save(self, entity_id: str, model: T) -> None:
        """Saves a model entity by ID."""
        ...

    def get(self, entity_id: str, model_type: type[T]) -> T:
        """Retrieves a model entity by ID. Raises EntityNotFoundError if not found."""
        ...

    def delete(self, entity_id: str) -> None:
        """Deletes a model entity by ID."""
        ...


class FileSystemRepository(Generic[T]):
    """
    A concrete implementation of ModelRepository that stores models as JSON files
    in a specified directory on the filesystem.
    """

    def __init__(self, base_directory: str) -> None:
        """
        Args:
            base_directory: The root directory for storing repository data.
        """
        self.base_directory = base_directory
        try:
            os.makedirs(self.base_directory, exist_ok=True)
        except OSError as e:
            raise StorageError(f"Failed to create repository directory: {e}") from e

    def _get_file_path(self, entity_id: str) -> str:
        """
        Sanitizes the entity ID to prevent path traversal and returns the full path.
        """
        # Sanitize input to prevent path traversal vulnerabilities
        safe_id = os.path.basename(entity_id)
        if not safe_id:
            raise StorageError("Invalid entity ID provided.")
        return os.path.join(self.base_directory, f"{safe_id}.json")

    def save(self, entity_id: str, model: T) -> None:
        """
        Saves the Pydantic model to a JSON file.
        """
        file_path = self._get_file_path(entity_id)
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(model.model_dump_json(indent=2))
        except OSError as e:
            raise StorageError(
                f"Failed to write entity {entity_id} to storage: {e}"
            ) from e
        except Exception as e:
            raise StorageError(
                f"Unexpected error saving entity {entity_id}: {e}"
            ) from e

    def get(self, entity_id: str, model_type: type[T]) -> T:
        """
        Retrieves the Pydantic model from its JSON file.
        """
        file_path = self._get_file_path(entity_id)
        if not os.path.exists(file_path):
            raise EntityNotFoundError(f"Entity with ID {entity_id} not found.")

        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
            return model_type.model_validate(data)
        except json.JSONDecodeError as e:
            raise StorageError(
                f"Failed to decode JSON for entity {entity_id}: {e}"
            ) from e
        except Exception as e:
            raise StorageError(f"Failed to load entity {entity_id}: {e}") from e

    def delete(self, entity_id: str) -> None:
        """
        Deletes the JSON file for the given entity ID.
        """
        file_path = self._get_file_path(entity_id)
        if not os.path.exists(file_path):
            # Deletion is idempotent; if it's not there, we consider it deleted.
            return

        try:
            os.remove(file_path)
        except OSError as e:
            raise StorageError(f"Failed to delete entity {entity_id}: {e}") from e
