import os

import pytest
from pydantic import BaseModel
from src.core.repository import FileSystemRepository, ModelRepository


class DummyModel(BaseModel):
    name: str
    value: int


@pytest.fixture
def repo(tmp_path: os.PathLike[str]) -> FileSystemRepository[DummyModel]:
    return FileSystemRepository(directory=str(tmp_path), model_class=DummyModel)


def test_repository_save_and_get(repo: FileSystemRepository[DummyModel]) -> None:
    model_id = "test_model_123"
    model = DummyModel(name="test", value=42)

    # Test saving
    repo.save(model_id, model)

    # Test retrieving
    retrieved = repo.get(model_id)
    assert retrieved is not None
    assert retrieved.name == "test"
    assert retrieved.value == 42


def test_repository_get_nonexistent(repo: FileSystemRepository[DummyModel]) -> None:
    assert repo.get("nonexistent") is None


def test_repository_interface(repo: FileSystemRepository[DummyModel]) -> None:
    # Verify that FileSystemRepository implements ModelRepository
    assert isinstance(repo, ModelRepository)
