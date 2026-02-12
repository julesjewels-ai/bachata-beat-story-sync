"""
Unit tests for caching backend.
"""
import os
import tempfile
import pytest
from src.services.caching.backend import JsonFileCache

@pytest.fixture
def temp_cache_file():
    fd, path = tempfile.mkstemp()
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)

def test_cache_miss(temp_cache_file):
    cache = JsonFileCache(temp_cache_file)
    assert cache.get("key1") is None

def test_cache_set_get(temp_cache_file):
    cache = JsonFileCache(temp_cache_file)
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"

def test_cache_persistence(temp_cache_file):
    cache1 = JsonFileCache(temp_cache_file)
    cache1.set("key1", "value1")

    # Reload from disk
    cache2 = JsonFileCache(temp_cache_file)
    assert cache2.get("key1") == "value1"

def test_cache_corruption(temp_cache_file):
    with open(temp_cache_file, "w") as f:
        f.write("invalid json")

    cache = JsonFileCache(temp_cache_file)
    # Should start empty and not crash
    assert cache.get("key1") is None

    # Should be able to write new data
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"
