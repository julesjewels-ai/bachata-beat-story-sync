"""
Integration test for the FileSystemRepository.
Tests the CRUD behaviour and custom exception handling.
"""

import os

import pytest
from src.core.exceptions import NotFoundError, StorageError
from src.core.models import PacingConfig
from src.core.repository import FileSystemRepository


@pytest.fixture
def repo_dir(tmp_path) -> str:
    return str(tmp_path / "test_repo")


@pytest.fixture
def repo(repo_dir) -> FileSystemRepository[PacingConfig]:
    return FileSystemRepository(base_dir=repo_dir, model_type=PacingConfig)


def test_repository_crud(repo: FileSystemRepository[PacingConfig], repo_dir: str):
    """Test Create, Read, Update, and Delete operations on the repository."""
    entity_id = "test_pacing"
    pacing = PacingConfig(
        min_clip_seconds=1.0,
        high_intensity_seconds=2.0,
        medium_intensity_seconds=3.0,
        low_intensity_seconds=4.0,
    )

    # 1. Create (Save)
    repo.save(entity_id, pacing)
    assert os.path.exists(os.path.join(repo_dir, f"{entity_id}.json"))

    # 2. Read (Get)
    loaded_pacing = repo.get(entity_id)
    assert loaded_pacing.min_clip_seconds == 1.0
    assert loaded_pacing.high_intensity_seconds == 2.0

    # 3. Update (Save again)
    pacing.min_clip_seconds = 1.5
    repo.save(entity_id, pacing)
    updated_pacing = repo.get(entity_id)
    assert updated_pacing.min_clip_seconds == 1.5

    # 4. Delete
    repo.delete(entity_id)
    assert not os.path.exists(os.path.join(repo_dir, f"{entity_id}.json"))


def test_repository_not_found(repo: FileSystemRepository[PacingConfig]):
    """Test NotFoundError is raised when getting/deleting a non-existent entity."""
    with pytest.raises(NotFoundError, match="Entity 'missing' not found"):
        repo.get("missing")

    with pytest.raises(NotFoundError, match="Entity 'missing' not found"):
        repo.delete("missing")


def test_repository_storage_error(tmp_path):
    """Test that a StorageError is raised on initialization failure."""
    # Create a file instead of a directory to force an OSError when makedirs is called
    file_path = tmp_path / "not_a_dir"
    file_path.write_text("content")

    with pytest.raises(StorageError, match="Cannot initialize repository"):
        FileSystemRepository(base_dir=str(file_path), model_type=PacingConfig)
