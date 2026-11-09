"""
Generic data persistence layer for Pydantic domain models using the Repository pattern.
"""

import json
import os
from typing import Generic, Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from src.core.exceptions import RepositoryError, StorageError

T = TypeVar("T", bound=BaseModel)


class ModelRepository(Protocol, Generic[T]):
    """
    Protocol for a generic repository managing domain models.
    """

    def get(self, id: str) -> T | None:
        """Retrieve a model by its identifier."""
        ...

    def save(self, id: str, model: T) -> None:
        """Save a model using the given identifier."""
        ...

    def delete(self, id: str) -> None:
        """Delete a model by its identifier."""
        ...


class FileSystemRepository(Generic[T]):
    """
    Concrete implementation of ModelRepository using the file system.
    """

    def __init__(self, base_dir: str, model_class: type[T]) -> None:
        """
        Initialize the repository.

        Args:
            base_dir: The directory where JSON files will be stored.
            model_class: The Pydantic model class to serialize/deserialize.
        """
        self.base_dir = base_dir
        self.model_class = model_class
        try:
            os.makedirs(self.base_dir, exist_ok=True)
        except OSError as e:
            raise StorageError(f"Failed to create repository directory: {e}") from e

    def _get_file_path(self, id: str) -> str:
        """
        Sanitize the identifier and construct the file path.
        Uses os.path.basename to prevent path traversal vulnerabilities.
        """
        safe_id = os.path.basename(id)
        if not safe_id:
            raise RepositoryError(f"Invalid identifier: {id}")
        return os.path.join(self.base_dir, f"{safe_id}.json")

    def get(self, id: str) -> T | None:
        """Retrieve a model by its identifier."""
        file_path = self._get_file_path(id)
        if not os.path.exists(file_path):
            return None

        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
            return self.model_class.model_validate(data)
        except (OSError, json.JSONDecodeError) as e:
            raise StorageError(f"Failed to read from storage for id {id}: {e}") from e
        except ValidationError as e:
            raise RepositoryError(f"Data validation failed for id {id}: {e}") from e

    def save(self, id: str, model: T) -> None:
        """Save a model using the given identifier."""
        file_path = self._get_file_path(id)
        try:
            # Write to a temporary file first, then atomically replace
            temp_path = f"{file_path}.tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(model.model_dump(), f, indent=2)
            os.replace(temp_path, file_path)
        except OSError as e:
            raise StorageError(f"Failed to write to storage for id {id}: {e}") from e

    def delete(self, id: str) -> None:
        """Delete a model by its identifier."""
        file_path = self._get_file_path(id)
        if not os.path.exists(file_path):
            return

        try:
            os.remove(file_path)
        except OSError as e:
            raise StorageError(f"Failed to delete storage for id {id}: {e}") from e
