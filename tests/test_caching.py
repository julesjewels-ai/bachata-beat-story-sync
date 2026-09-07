"""Integration tests for the caching decorator and repository pattern."""

from pathlib import Path

from pydantic import BaseModel
from src.core.caching import repository_cache
from src.core.repository import FileSystemRepository


class DummyResult(BaseModel):
    value: int
    name: str


def test_cache_decorator_integration(tmp_path: Path) -> None:
    repo_dir = str(tmp_path / "dummy_cache")
    repo = FileSystemRepository(storage_dir=repo_dir, model_class=DummyResult)

    call_count = 0

    @repository_cache(repository=repo)
    def expensive_operation(param: int, text: str) -> DummyResult:
        nonlocal call_count
        call_count += 1
        return DummyResult(value=param * 2, name=text.upper())

    # First call - should execute function
    res1 = expensive_operation(5, "hello")
    assert call_count == 1
    assert res1.value == 10
    assert res1.name == "HELLO"

    # Second call - should hit cache
    res2 = expensive_operation(5, "hello")
    assert call_count == 1
    assert res2.value == 10
    assert res2.name == "HELLO"

    # Third call with different args - should execute function
    res3 = expensive_operation(10, "world")
    assert call_count == 2
    assert res3.value == 20
    assert res3.name == "WORLD"
