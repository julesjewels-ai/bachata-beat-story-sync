"""
Integration tests for the FileSystemRepository.
"""

import os
from pathlib import Path

import pytest
from pydantic import BaseModel, Field

from src.core.exceptions import EntityNotFoundError, StorageError
from src.core.repository import FileSystemRepository


class DummyModel(BaseModel):
    """A dummy domain model for testing the repository."""

    name: str = Field(..., description="The name of the dummy model")
    value: int = Field(..., description="A test value")


@pytest.fixture
def repo(tmp_path: Path) -> FileSystemRepository[DummyModel]:
    """Provides a FileSystemRepository instance configured with a temp directory."""
    return FileSystemRepository[DummyModel](str(tmp_path))


def test_repository_save_and_get(repo: FileSystemRepository[DummyModel]) -> None:
    """Test that a model can be saved and retrieved accurately."""
    model = DummyModel(name="test_model", value=42)
    entity_id = "model_1"

    # Save the model
    repo.save(entity_id, model)

    # Retrieve the model
    retrieved = repo.get(entity_id, DummyModel)

    assert retrieved.name == "test_model"
    assert retrieved.value == 42
    assert retrieved == model


def test_repository_get_not_found(repo: FileSystemRepository[DummyModel]) -> None:
    """Test that getting a non-existent entity raises EntityNotFoundError."""
    with pytest.raises(EntityNotFoundError, match="not found"):
        repo.get("non_existent", DummyModel)


def test_repository_delete(repo: FileSystemRepository[DummyModel]) -> None:
    """Test that an entity can be deleted."""
    model = DummyModel(name="to_delete", value=99)
    entity_id = "delete_me"

    repo.save(entity_id, model)
    # Ensure it's there
    assert repo.get(entity_id, DummyModel).name == "to_delete"

    # Delete it
    repo.delete(entity_id)

    # Ensure it's gone
    with pytest.raises(EntityNotFoundError):
        repo.get(entity_id, DummyModel)

    # Deleting again should be idempotent and not raise
    repo.delete(entity_id)


def test_repository_path_traversal_prevention(
    repo: FileSystemRepository[DummyModel], tmp_path: Path
) -> None:
    """Test that the repository sanitizes entity IDs to prevent path traversal."""
    model = DummyModel(name="sneaky", value=0)

    # Attempt to write outside the repo directory
    sneaky_id = "../sneaky_model"

    # The repository should extract just 'sneaky_model'
    repo.save(sneaky_id, model)

    # It should not exist in the parent directory (which might not be accessible anyway)
    # But it should exist exactly as 'sneaky_model.json' in the repo directory
    expected_path = os.path.join(str(tmp_path), "sneaky_model.json")
    assert os.path.exists(expected_path)

    # Getting with the sneaky id should also resolve to the safe id
    retrieved = repo.get(sneaky_id, DummyModel)
    assert retrieved.name == "sneaky"


def test_repository_invalid_id_raises_storage_error(
    repo: FileSystemRepository[DummyModel],
) -> None:
    """Test that an invalid (empty after basename) entity ID raises a StorageError."""
    model = DummyModel(name="invalid", value=1)

    # An ID that becomes empty after os.path.basename
    invalid_id = "/"

    with pytest.raises(StorageError, match="Invalid entity ID"):
        repo.save(invalid_id, model)
