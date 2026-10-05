"""
Generic Repository interface and FileSystem implementation for domain models.
"""

import json
import logging
import os
from typing import Generic, Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from src.core.exceptions import RepositoryError, StorageError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class ModelRepository(Protocol, Generic[T]):
    """Generic interface for a domain model repository."""

    def get(self, model_id: str) -> T | None:
        """
        Retrieve a model by its ID.

        Args:
            model_id: The unique identifier of the model.

        Returns:
            The model instance if found, else None.
        """
        ...

    def save(self, model_id: str, model: T) -> None:
        """
        Save a model.

        Args:
            model_id: The unique identifier to save the model under.
            model: The model instance to save.
        """
        ...

    def delete(self, model_id: str) -> bool:
        """
        Delete a model by its ID.

        Args:
            model_id: The unique identifier of the model to delete.

        Returns:
            True if the model was deleted, False if it did not exist.
        """
        ...

    def list_all(self) -> list[T]:
        """
        List all models in the repository.

        Returns:
            A list of all model instances.
        """
        ...


class FileSystemRepository(Generic[T]):
    """
    File system based implementation of the ModelRepository protocol.
    Saves Pydantic models as JSON files in a specified directory.
    """

    def __init__(self, base_dir: str, model_type: type[T]) -> None:
        """
        Initialize the FileSystemRepository.

        Args:
            base_dir: The directory where JSON files will be stored.
            model_type: The Pydantic BaseModel class type.
        """
        self.base_dir = base_dir
        self.model_type = model_type

        try:
            os.makedirs(self.base_dir, exist_ok=True)
        except OSError as e:
            raise StorageError(
                f"Failed to create repository directory {self.base_dir}: {e}"
            ) from e

    def _get_file_path(self, model_id: str) -> str:
        # Sanitize model_id for file system (basic sanitization)
        safe_id = "".join(
            c if c.isalnum() or c in ("-", "_") else "_" for c in model_id
        )
        return os.path.join(self.base_dir, f"{safe_id}.json")

    def get(self, model_id: str) -> T | None:
        file_path = self._get_file_path(model_id)
        if not os.path.exists(file_path):
            return None

        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
            return self.model_type.model_validate(data)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON for model %s: %s", model_id, e)
            raise StorageError(f"Corrupted storage file for {model_id}") from e
        except ValidationError as e:
            logger.error("Data validation failed for model %s: %s", model_id, e)
            raise RepositoryError(f"Data format mismatch for {model_id}") from e
        except OSError as e:
            logger.error("Failed to read storage file for model %s: %s", model_id, e)
            raise StorageError(f"Failed to read from storage for {model_id}") from e

    def save(self, model_id: str, model: T) -> None:
        file_path = self._get_file_path(model_id)
        try:
            # Atomic save: write to temp file then rename
            temp_path = f"{file_path}.tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                # Use model_dump to ensure all types are JSON serializable
                json.dump(model.model_dump(mode="json"), f, indent=2)
            os.replace(temp_path, file_path)
        except OSError as e:
            logger.error("Failed to save model %s: %s", model_id, e)
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
            raise StorageError(f"Failed to write to storage for {model_id}") from e

    def delete(self, model_id: str) -> bool:
        file_path = self._get_file_path(model_id)
        if not os.path.exists(file_path):
            return False
        try:
            os.remove(file_path)
            return True
        except OSError as e:
            logger.error("Failed to delete model %s: %s", model_id, e)
            raise StorageError(f"Failed to delete storage file for {model_id}") from e

    def list_all(self) -> list[T]:
        models = []
        try:
            for filename in os.listdir(self.base_dir):
                if filename.endswith(".json"):
                    model_id = filename[:-5]
                    model = self.get(model_id)
                    if model is not None:
                        models.append(model)
        except OSError as e:
            logger.error("Failed to list models in %s: %s", self.base_dir, e)
            raise StorageError(
                f"Failed to read repository directory {self.base_dir}"
            ) from e

        return models
