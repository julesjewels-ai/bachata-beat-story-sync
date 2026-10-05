"""
Integration tests for the FileSystemRepository.
"""

import os

import pytest
from pydantic import BaseModel, ConfigDict, Field
from src.core.exceptions import RepositoryError, StorageError
from src.core.repository import FileSystemRepository


class MockDomainModel(BaseModel):
    """A mock Pydantic model for testing the repository."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(...)
    value: int = Field(...)


@pytest.fixture
def repo(tmp_path):
    """Fixture providing a FileSystemRepository."""
    repo_dir = os.path.join(str(tmp_path), "test_repo")
    return FileSystemRepository(base_dir=repo_dir, model_type=MockDomainModel)


def test_repository_lifecycle(repo):
    """Test saving, getting, listing, and deleting a model in the repository."""

    # 1. Save a model
    model = MockDomainModel(name="test_model", value=42)
    repo.save("model_1", model)

    # 2. Get the model
    retrieved_model = repo.get("model_1")
    assert retrieved_model is not None
    assert retrieved_model.name == "test_model"
    assert retrieved_model.value == 42

    # 3. List all models
    repo.save("model_2", MockDomainModel(name="another", value=99))
    models = repo.list_all()
    assert len(models) == 2

    # 4. Delete a model
    assert repo.delete("model_1") is True
    assert repo.get("model_1") is None

    # 5. List after deletion
    models = repo.list_all()
    assert len(models) == 1
    assert models[0].name == "another"


def test_repository_invalid_data(repo, tmp_path):
    """Test getting corrupted or invalid data."""
    repo_dir = os.path.join(str(tmp_path), "test_repo")
    file_path = os.path.join(repo_dir, "bad_model.json")

    # Write invalid JSON
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("{bad_json: True")

    with pytest.raises(StorageError, match="Corrupted storage file"):
        repo.get("bad_model")

    # Write invalid data for the model
    with open(file_path, "w", encoding="utf-8") as f:
        f.write('{"wrong_field": "value"}')

    with pytest.raises(RepositoryError, match="Data format mismatch"):
        repo.get("bad_model")


def test_repository_not_found(repo):
    """Test getting and deleting non-existent models."""
    assert repo.get("non_existent") is None
    assert repo.delete("non_existent") is False
