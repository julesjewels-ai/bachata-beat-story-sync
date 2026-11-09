"""
Tests for the generic file system repository.
"""

import os
from pathlib import Path

import pytest
from pydantic import BaseModel, Field
from src.core.exceptions import RepositoryError, StorageError
from src.core.repository import FileSystemRepository


class DummyDomainModel(BaseModel):
    name: str = Field(...)
    score: float = Field(...)
    is_active: bool = Field(default=True)


@pytest.fixture
def repo(tmp_path: Path) -> FileSystemRepository[DummyDomainModel]:
    return FileSystemRepository(
        base_dir=str(tmp_path / "repo_data"), model_class=DummyDomainModel
    )


def test_repository_save_and_get(repo: FileSystemRepository[DummyDomainModel]):
    """Test standard save and get operations."""
    model = DummyDomainModel(name="test_item", score=9.5)

    # Save the model
    repo.save(id="item_1", model=model)

    # Verify file was created
    expected_file = os.path.join(repo.base_dir, "item_1.json")
    assert os.path.exists(expected_file)

    # Retrieve the model
    retrieved = repo.get(id="item_1")
    assert retrieved is not None
    assert retrieved.name == "test_item"
    assert retrieved.score == 9.5
    assert retrieved.is_active is True


def test_repository_get_not_found(repo: FileSystemRepository[DummyDomainModel]):
    """Test retrieving an item that does not exist."""
    assert repo.get(id="nonexistent") is None


def test_repository_delete(repo: FileSystemRepository[DummyDomainModel]):
    """Test deleting an item."""
    model = DummyDomainModel(name="to_delete", score=1.0)
    repo.save(id="item_2", model=model)

    assert repo.get(id="item_2") is not None

    # Delete the model
    repo.delete(id="item_2")

    # Verify deletion
    assert repo.get(id="item_2") is None


def test_repository_invalid_id_path_traversal(
    repo: FileSystemRepository[DummyDomainModel],
):
    """Test that path traversal attempts are sanitized or rejected."""
    model = DummyDomainModel(name="hacker", score=0.0)

    # os.path.basename("../item") evaluates to "item"
    repo.save(id="../item", model=model)

    # The file should be saved as just "item.json" in the base_dir
    expected_file = os.path.join(repo.base_dir, "item.json")
    assert os.path.exists(expected_file)
    assert not os.path.exists(os.path.join(repo.base_dir, "../item.json"))


def test_repository_validation_error(
    repo: FileSystemRepository[DummyDomainModel], tmp_path: Path
):
    """Test getting an item with invalid JSON structure raises RepositoryError."""
    model_id = "bad_data"
    file_path = os.path.join(repo.base_dir, f"{model_id}.json")

    # Manually write invalid data (missing required field 'name')
    os.makedirs(repo.base_dir, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write('{"score": 5.0}')

    with pytest.raises(RepositoryError, match="Data validation failed"):
        repo.get(id=model_id)


def test_repository_directory_creation_failure(monkeypatch):
    """Test storage error when base_dir cannot be created."""

    def mock_makedirs(*args, **kwargs):
        raise OSError("Permission denied")

    monkeypatch.setattr(os, "makedirs", mock_makedirs)

    with pytest.raises(StorageError, match="Failed to create repository directory"):
        FileSystemRepository(base_dir="/fake/dir", model_class=DummyDomainModel)
