"""
Unit tests for the caching service backend.
"""
import os
import json
import pytest
from src.services.caching.backend import JsonFileCache

@pytest.fixture
def cache_file(tmp_path):
    f = tmp_path / "test_cache.json"
    return str(f)

def test_cache_init_empty(cache_file):
    """Test initializing cache with non-existent file."""
    cache = JsonFileCache(cache_file)
    assert cache.get("key") is None
    # File is not created until set is called
    assert not os.path.exists(cache_file)

def test_cache_set_get(cache_file):
    """Test setting and getting values."""
    cache = JsonFileCache(cache_file)
    cache.set("foo", "bar")
    assert cache.get("foo") == "bar"

    # Check persistence on disk
    assert os.path.exists(cache_file)
    with open(cache_file, 'r') as f:
        data = json.load(f)
    assert data["foo"] == "bar"

def test_cache_persistence_reload(cache_file):
    """Test that cache reloads data from disk."""
    cache = JsonFileCache(cache_file)
    cache.set("a", 1)

    cache2 = JsonFileCache(cache_file)
    assert cache2.get("a") == 1

def test_cache_corrupted_file(cache_file):
    """Test resilience against corrupted cache files."""
    with open(cache_file, 'w') as f:
        f.write("{invalid_json")

    cache = JsonFileCache(cache_file)
    # Should handle error and start empty
    assert cache.get("key") is None

    # Should be able to overwrite
    cache.set("new", "val")
    assert cache.get("new") == "val"

    # Check if file is valid JSON now
    with open(cache_file, 'r') as f:
        data = json.load(f)
    assert data["new"] == "val"
