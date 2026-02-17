"""
Unit tests for the caching backend.
"""
import json
import os
import pytest
from src.services.caching.backend import JsonFileCache


@pytest.fixture
def temp_cache_file(tmp_path):
    """Fixture providing a temporary cache file path."""
    return str(tmp_path / "cache.json")


def test_load_cache_existing(temp_cache_file):
    """Test loading an existing cache file."""
    data = {"foo": "bar"}
    with open(temp_cache_file, "w", encoding="utf-8") as f:
        json.dump(data, f)

    cache = JsonFileCache(temp_cache_file)
    assert cache.get("foo") == "bar"


def test_load_cache_missing(temp_cache_file):
    """Test behavior when cache file does not exist."""
    cache = JsonFileCache(temp_cache_file)
    assert cache.get("foo") is None


def test_load_cache_corrupted(temp_cache_file):
    """Test handling of corrupted cache files."""
    with open(temp_cache_file, "w", encoding="utf-8") as f:
        f.write("invalid json")

    cache = JsonFileCache(temp_cache_file)
    assert cache.get("foo") is None


def test_set_saves_to_disk(temp_cache_file):
    """Test that setting a value persists it to disk."""
    cache = JsonFileCache(temp_cache_file)
    cache.set("foo", {"bar": "baz"})

    assert os.path.exists(temp_cache_file)
    with open(temp_cache_file, "r", encoding="utf-8") as f:
        content = json.load(f)
    assert content["foo"] == {"bar": "baz"}


def test_get_returns_value(temp_cache_file):
    """Test retrieving values from the cache."""
    cache = JsonFileCache(temp_cache_file)
    cache.set("a", 1)
    assert cache.get("a") == 1
    assert cache.get("b") is None
