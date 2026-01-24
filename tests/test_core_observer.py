import os
import pytest
from unittest.mock import MagicMock
from src.core.app import BachataSyncEngine
from src.core.interfaces import ProgressObserver

def test_scan_video_library_observer_calls(tmp_path):
    # Setup dummy video files
    video_dir = tmp_path / "videos"
    video_dir.mkdir()
    (video_dir / "clip1.mp4").touch()
    (video_dir / "clip2.mp4").touch()

    engine = BachataSyncEngine()

    # Mock Observer
    observer = MagicMock(spec=ProgressObserver)

    # Mock video_analyzer to avoid actual processing overhead and errors
    engine.video_analyzer.analyze = MagicMock(return_value=MagicMock())

    engine.scan_video_library(str(video_dir), observer=observer)

    # Check if on_progress was called
    # implementation:
    # for i, ...: observer.on_progress(i, total, ...)
    # finally: observer.on_progress(total, total, ...)

    # We expect at least 3 calls for 2 files.
    assert observer.on_progress.call_count >= 3

    # Verify the last call
    observer.on_progress.assert_called_with(2, 2, message="Scan complete.")
