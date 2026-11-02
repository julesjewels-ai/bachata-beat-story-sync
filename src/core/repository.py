"""
Generic repository pattern for Pydantic models.
"""

import json
import logging
import os
from typing import Generic, Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel, ValidationError

from src.core.exceptions import RepositoryError, StorageError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


@runtime_checkable
class ModelRepository(Protocol, Generic[T]):
    """Protocol for saving and retrieving Pydantic domain models."""

    def get(self, model_id: str) -> T | None:
        """Retrieves a model by its identifier."""
        ...

    def save(self, model_id: str, model: T) -> None:
        """Saves a model."""
        ...


class FileSystemRepository(Generic[T]):
    """
    A concrete implementation of ModelRepository that saves Pydantic models
    to the file system as JSON files.
    """

    def __init__(self, directory: str, model_class: type[T]):
        self.directory = directory
        self.model_class = model_class

        # Ensure the directory exists
        try:
            os.makedirs(self.directory, exist_ok=True)
        except OSError as e:
            raise StorageError(
                f"Failed to create repository directory: {self.directory}"
            ) from e

    def _get_file_path(self, model_id: str) -> str:
        """Constructs a safe file path for the given model ID."""
        # Sanitize input to prevent path traversal
        safe_id = os.path.basename(model_id)
        if not safe_id:
            raise StorageError(f"Invalid model_id provided: {model_id}")
        return os.path.join(self.directory, f"{safe_id}.json")

    def get(self, model_id: str) -> T | None:
        """Retrieves a model by its ID from the filesystem."""
        file_path = self._get_file_path(model_id)

        if not os.path.exists(file_path):
            return None

        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
            return self.model_class.model_validate(data)
        except json.JSONDecodeError as e:
            logger.error("Failed to decode JSON from %s: %s", file_path, e)
            raise RepositoryError(f"Corrupted data in {file_path}") from e
        except ValidationError as e:
            logger.error("Failed to validate model data from %s: %s", file_path, e)
            raise RepositoryError(f"Invalid model schema in {file_path}") from e
        except OSError as e:
            logger.error("IO Error reading %s: %s", file_path, e)
            raise RepositoryError(f"Failed to read file {file_path}") from e

    def save(self, model_id: str, model: T) -> None:
        """Saves a model to the filesystem as JSON."""
        file_path = self._get_file_path(model_id)

        try:
            data = model.model_dump(mode="json")

            # Write to temporary file first then rename to avoid corruption
            temp_path = f"{file_path}.tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            os.replace(temp_path, file_path)
            logger.debug("Successfully saved model to %s", file_path)
        except OSError as e:
            logger.error("IO Error writing to %s: %s", file_path, e)
            raise RepositoryError(f"Failed to save model to {file_path}") from e
