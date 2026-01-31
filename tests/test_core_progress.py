"""
Unit tests for progress reporting in the core engine.
"""
import pytest
from unittest.mock import MagicMock
from src.core.app import BachataSyncEngine


class MockObserver:
    def __init__(self):
        self.updates = []

    def on_progress(self, current: int, total: int, message: str = "") -> None:
        self.updates.append((current, total, message))


@pytest.fixture
def engine():
    return BachataSyncEngine()


def test_scan_video_library_progress(engine, tmp_path):
    """
    Test that scan_video_library calls the observer.
    """
    # Setup: Create some dummy video files
    video_dir = tmp_path / "videos"
    video_dir.mkdir()

    # Create 3 valid video files
    for i in range(3):
        with open(video_dir / f"vid_{i}.mp4", "w") as f:
            f.write("mock content")

    # Create 1 invalid file
    with open(video_dir / "ignore.txt", "w") as f:
        f.write("ignore me")

    # Mock the _process_video_file to avoid actual video analysis
    # We return None so we don't need real video files
    engine._process_video_file = MagicMock(return_value=None)

    observer = MockObserver()

    # Act
    engine.scan_video_library(str(video_dir), observer=observer)

    # Assert
    # Total valid files is 3.
    # Progress should be called:
    # - 0, 3, "Scanning ..."
    # - 1, 3, "Scanning ..."
    # - 2, 3, "Scanning ..."
    # - 3, 3, "Scan complete."

    assert len(observer.updates) >= 4

    # Check that total is always 3
    for current, total, msg in observer.updates:
        assert total == 3

    # Check that it reached completion
    last_update = observer.updates[-1]
    assert last_update[0] == 3
    assert last_update[2] == "Scan complete."
