import pytest
from unittest.mock import Mock, call, patch
import os
from pydantic import ValidationError
from typing import List, Optional, Any

from src.core.app import BachataSyncEngine
from src.core.models import VideoAnalysisResult

# Define a sample result for mocking
SAMPLE_RESULT = VideoAnalysisResult(
    path="/path/to/video.mp4",
    intensity_score=8.5,
    duration=120.0,
    thumbnail=b"fake_image_data"
)

@pytest.fixture
def mock_video_analyzer() -> Mock:
    """Mock the VideoAnalyzer to avoid real processing."""
    analyzer = Mock()
    # Default behavior: return a valid result
    analyzer.analyze.return_value = SAMPLE_RESULT
    return analyzer

@pytest.fixture
def mock_observer() -> Mock:
    """Mock the ProgressObserver."""
    return Mock()

@pytest.fixture
def sync_engine(mock_video_analyzer: Mock) -> BachataSyncEngine:
    """Create a BachataSyncEngine with a mocked analyzer."""
    engine = BachataSyncEngine()
    engine.video_analyzer = mock_video_analyzer
    return engine

@pytest.fixture
def mock_fs() -> Any:
    """Patch os.path.exists and os.walk."""
    with patch("src.core.app.os.path.exists") as mock_exists, \
         patch("src.core.app.os.walk") as mock_walk:
        yield mock_exists, mock_walk

@pytest.mark.parametrize("scenario, exists_return, walk_return, analyze_side_effect, expected_count, expected_scanned, expected_error", [
    (
        "directory_missing",
        False,
        [],
        None,
        0,
        0,
        FileNotFoundError
    ),
    (
        "empty_directory",
        True,
        [],
        None,
        0,
        0,
        None
    ),
    (
        "unsupported_extensions",
        True,
        [("/root", [], ["notes.txt", "image.jpg"])],
        None,
        0,
        0,
        None
    ),
    (
        "success_single_file",
        True,
        [("/root", [], ["video.mp4"])],
        None,
        1,
        1,
        None
    ),
    (
        "success_multiple_files",
        True,
        [("/root", [], ["v1.mp4", "v2.MOV"])], # Assuming MOV is supported
        None,
        2,
        2,
        None
    ),
    (
        "validation_failure",
        True,
        [("/root", [], ["bad_video.mp4"])],
        ValidationError.from_exception_data("Mock Error", []),
        0,
        1,
        None
    ),
    (
        "generic_error",
        True,
        [("/root", [], ["error.mp4"])],
        Exception("Unexpected crash"),
        0,
        1,
        None
    ),
])
def test_scan_video_library_behavior(
    scenario: str,
    exists_return: bool,
    walk_return: List[Any],
    analyze_side_effect: Any,
    expected_count: int,
    expected_scanned: int,
    expected_error: Optional[type],
    sync_engine: BachataSyncEngine,
    mock_video_analyzer: Mock,
    mock_observer: Mock,
    mock_fs: Any
) -> None:
    # Arrange
    mock_exists, mock_walk = mock_fs
    mock_exists.return_value = exists_return
    mock_walk.return_value = walk_return

    if analyze_side_effect:
        mock_video_analyzer.analyze.side_effect = analyze_side_effect

    # Act & Assert
    if expected_error:
        with pytest.raises(expected_error):
            sync_engine.scan_video_library("/fake/dir", observer=mock_observer)
    else:
        results = sync_engine.scan_video_library("/fake/dir", observer=mock_observer)
        assert len(results) == expected_count

        # Verify Observer
        if exists_return:
             # Observer should be called at least for completion
             assert mock_observer.on_progress.called
             # Check if "Scan complete" was called with total files found (scanned), not just successes
             mock_observer.on_progress.assert_any_call(expected_scanned, expected_scanned, "Scan complete.")
