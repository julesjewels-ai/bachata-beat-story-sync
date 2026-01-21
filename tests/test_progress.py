"""
Tests for progress reporting mechanism.
"""
from unittest.mock import Mock, call, MagicMock
import os
from src.core.app import BachataSyncEngine
from src.core.interfaces import ProgressObserver

def test_progress_reporting(monkeypatch, tmp_path):
    """
    Test that the engine calls the observer correctly.
    """
    # Create mock video files
    video_dir = tmp_path / "videos"
    video_dir.mkdir()
    (video_dir / "vid1.mp4").touch()
    (video_dir / "vid2.mp4").touch()

    # Mock VideoAnalyzer to avoid real processing
    mock_analyzer = Mock()
    mock_analyzer.analyze.return_value = MagicMock(
        path="path", intensity_score=0.5, duration=10.0
    )

    engine = BachataSyncEngine()
    engine.video_analyzer = mock_analyzer

    # Mock observer
    observer = Mock(spec=ProgressObserver)

    # Run scan
    engine.scan_video_library(str(video_dir), observer=observer)

    # Check calls
    # Should be called twice (for 2 files)
    assert observer.on_progress.call_count == 2

    # Verify arguments of the first call
    # call(current, total, message)
    # The exact order of files depends on OS, so we check general structure
    args, kwargs = observer.on_progress.call_args_list[0]
    assert args[0] == 1 # current
    assert args[1] == 2 # total
    assert "Processing" in kwargs['message']

    args, kwargs = observer.on_progress.call_args_list[1]
    assert args[0] == 2 # current
    assert args[1] == 2 # total
