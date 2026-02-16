"""
Tests for the caching backend.
"""
import pytest
from src.services.caching.backend import JsonFileCache


@pytest.fixture
def cache_file(tmp_path):
    return tmp_path / "test_cache.json"


def test_cache_crud(cache_file):
    """Test Create, Read, Delete operations."""
    cache = JsonFileCache(str(cache_file))

    # Test set and get
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"

    # Test persistence (reload from disk)
    cache2 = JsonFileCache(str(cache_file))
    assert cache2.get("key1") == "value1"

    # Test delete
    cache.delete("key1")
    assert cache.get("key1") is None

    # Confirm deletion persisted
    cache3 = JsonFileCache(str(cache_file))
    assert cache3.get("key1") is None


def test_cache_types(cache_file):
    """Test caching complex JSON types."""
    cache = JsonFileCache(str(cache_file))
    data = {"foo": "bar", "num": 123, "list": [1, 2], "nested": {"a": 1}}
    cache.set("data", data)
    assert cache.get("data") == data


def test_corrupt_cache(cache_file):
    """Test resilience against corrupted cache files."""
    # Create corrupt file
    with open(cache_file, "w") as f:
        f.write("{invalid json")

    cache = JsonFileCache(str(cache_file))
    # Should start empty and not crash
    assert cache.get("any") is None

    # Should overwrite corrupt file on save
    cache.set("new", "val")
    assert cache.get("new") == "val"
