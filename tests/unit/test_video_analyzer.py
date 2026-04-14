"""
Unit tests for the VideoAnalyzer module.

Uses robust, parameterized testing to cover edge cases, security, and error handling.
"""

from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest
from src.core.video_analyzer import (
    MAX_SCENE_CHANGES,
    MAX_VIDEO_DURATION_SECONDS,
    MAX_VIDEO_FRAMES,
    VideoAnalysisInput,
    VideoAnalyzer,
)


@pytest.fixture
def analyzer():
    return VideoAnalyzer()


@pytest.fixture
def mock_video_capture():
    with patch("cv2.VideoCapture") as mock:
        yield mock


@pytest.fixture
def mock_exists():
    with patch("os.path.exists", return_value=True) as mock:
        yield mock


@pytest.fixture
def mock_listdir():
    with patch("os.listdir", return_value=["dummy.mp4"]) as mock:
        yield mock


@pytest.fixture
def mock_isdir():
    with patch("os.path.isdir", return_value=False) as mock:
        yield mock


@pytest.fixture
def mock_get_video_duration():
    with patch(
        "src.core.video_analyzer.get_video_duration", return_value=10.0
    ) as mock:
        yield mock


def create_mock_cap(
    fps=30.0, frame_count=300, width=1920.0, height=1080.0, read_success=True
):
    """
    Helper to create a configured Mock VideoCapture.

    Uses robust property mapping instead of brittle call order.
    """
    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = True

    # Define property mapping
    props = {
        cv2.CAP_PROP_FPS: fps,
        cv2.CAP_PROP_FRAME_COUNT: frame_count,
        cv2.CAP_PROP_FRAME_WIDTH: width,
        cv2.CAP_PROP_FRAME_HEIGHT: height,
    }

    def get_prop(prop_id):
        return props.get(prop_id, 0.0)

    # Configure .get() side effect
    mock_cap.get.side_effect = get_prop

    # Generate dummy frames
    # 1. Middle frame (thumbnail)
    # 2. Intensity frames (let's say 10 frames)
    # 3. End of stream

    frame_shape = (int(height), int(width), 3)
    dummy_frame = np.zeros(frame_shape, dtype=np.uint8)

    if read_success:
        # One for thumbnail, then iterator for intensity
        # We need enough frames to trigger intensity calculation
        # (at least 2 processed frames)
        # If FPS=30 and ANALYSIS_FPS=3, skip=10.
        # We need frames at index 0 and 10.
        reads = [(True, dummy_frame)] + [(True, dummy_frame)] * 20 + [(False, None)]
    else:
        # 1. Thumbnail extraction fails (read returns False)
        # 2. Intensity calculation loop starts,
        #    read returns False immediately -> breaks loop
        reads = [(False, None), (False, None)]

    mock_cap.read.side_effect = reads

    return mock_cap


@pytest.mark.parametrize(
    "scenario",
    [
        {
            "desc": "Standard 1080p Video",
            "fps": 30.0,
            "frames": 300,
            "w": 1920.0,
            "h": 1080.0,
            "expect_vertical": False,
            "expect_duration": 10.0,
        },
        {
            "desc": "Vertical 9:16 Video",
            "fps": 60.0,
            "frames": 600,
            "w": 1080.0,
            "h": 1920.0,
            "expect_vertical": True,
            "expect_duration": 10.0,
        },
        {
            "desc": "Low FPS Video",
            "fps": 10.0,
            "frames": 100,
            "w": 640.0,
            "h": 480.0,
            "expect_vertical": False,
            "expect_duration": 10.0,
        },
    ],
)
def test_analyze_video_success(
    analyzer, mock_video_capture, mock_exists, mock_isdir, mock_get_video_duration, scenario
):
    """Test successful video analysis for different formats."""
    mock_cap = create_mock_cap(
        fps=scenario["fps"],
        frame_count=scenario["frames"],
        width=scenario["w"],
        height=scenario["h"],
    )
    mock_video_capture.return_value = mock_cap

    input_data = VideoAnalysisInput(file_path="test.mp4")
    result = analyzer.analyze(input_data)

    assert result.path == "test.mp4"
    assert result.duration == pytest.approx(scenario["expect_duration"])
    assert result.is_vertical == scenario["expect_vertical"]
    assert result.thumbnail_data is not None


def test_thumbnail_encode_failure(
    analyzer, mock_video_capture, mock_exists, mock_isdir
):
    """Test handling when thumbnail encoding fails."""
    mock_cap = create_mock_cap()
    mock_video_capture.return_value = mock_cap

    # Mock imencode to return False
    with patch("cv2.imencode", return_value=(False, None)):
        input_data = VideoAnalysisInput(file_path="test.mp4")
        result = analyzer.analyze(input_data)

    assert result.thumbnail_data is None
    assert result.intensity_score >= 0.0


def test_analyze_video_dos_frames(
    analyzer, mock_video_capture, mock_exists, mock_isdir
):
    """Test DoS protection against excessive frame count."""
    # Use helper with excessive frames
    mock_cap = create_mock_cap(frame_count=MAX_VIDEO_FRAMES + 1)
    mock_video_capture.return_value = mock_cap

    input_data = VideoAnalysisInput(file_path="huge.mp4")

    with pytest.raises(ValueError, match="exceeds maximum allowed frames"):
        analyzer.analyze(input_data)


def test_analyze_video_dos_duration(
    analyzer, mock_video_capture, mock_exists, mock_isdir, mock_get_video_duration
):
    """Test DoS protection against excessive duration."""
    # Mock get_video_duration to return a duration that exceeds the max
    mock_get_video_duration.return_value = MAX_VIDEO_DURATION_SECONDS + 1
    mock_cap = create_mock_cap(fps=1.0, frame_count=MAX_VIDEO_DURATION_SECONDS + 1)
    mock_video_capture.return_value = mock_cap

    input_data = VideoAnalysisInput(file_path="long.mp4")

    with pytest.raises(ValueError, match="exceeds maximum duration"):
        analyzer.analyze(input_data)


def test_analyze_video_open_failure(
    analyzer, mock_video_capture, mock_exists, mock_isdir
):
    """Test failure when video cannot be opened."""
    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = False
    mock_video_capture.return_value = mock_cap

    input_data = VideoAnalysisInput(file_path="corrupt.mp4")

    with pytest.raises(IOError, match="Could not open video file"):
        analyzer.analyze(input_data)


def test_analyze_video_read_failure(
    analyzer, mock_video_capture, mock_exists, mock_isdir
):
    """Test when video exists but frames cannot be read."""
    mock_cap = create_mock_cap(read_success=False)
    mock_video_capture.return_value = mock_cap

    input_data = VideoAnalysisInput(file_path="empty_stream.mp4")
    result = analyzer.analyze(input_data)

    # Should succeed but with 0 intensity and no thumbnail
    assert result.intensity_score == 0.0
    assert result.thumbnail_data is None


def test_validate_path_not_found(mock_exists):
    """Test validation failure for missing file."""
    with patch("os.path.exists", return_value=False):
        with pytest.raises(ValueError, match="File not found"):
            VideoAnalysisInput(file_path="missing.mp4")


def test_validate_path_traversal():
    """Test security check for path traversal."""
    with pytest.raises(ValueError, match="Path traversal attempt detected"):
        VideoAnalysisInput(file_path="../secret.mp4")


def test_validate_extension(mock_exists, mock_isdir):
    """Test validation for unsupported extension."""
    with pytest.raises(ValueError, match="Unsupported extension"):
        VideoAnalysisInput(file_path="test.exe")


def test_thumbnail_extraction_failure(
    analyzer, mock_video_capture, mock_exists, mock_isdir, mock_get_video_duration
):
    """Test that analysis proceeds even if thumbnail extraction fails."""
    mock_cap = create_mock_cap()

    # Configure read to fail ONLY for the first call (thumbnail)
    # 1. Middle frame (thumbnail) -> Fail
    # 2. Intensity frames -> Success

    frame_shape = (1080, 1920, 3)
    dummy_frame = np.zeros(frame_shape, dtype=np.uint8)

    # Fail first read, succeed subsequent reads
    reads = [(False, None)] + [(True, dummy_frame)] * 10 + [(False, None)]
    mock_cap.read.side_effect = reads

    mock_video_capture.return_value = mock_cap

    input_data = VideoAnalysisInput(file_path="test.mp4")
    result = analyzer.analyze(input_data)

    assert result.thumbnail_data is None
    assert result.duration == 10.0


def test_thumbnail_exception(analyzer, mock_video_capture, mock_exists, mock_isdir, mock_get_video_duration):
    """Test exception handling during thumbnail extraction."""
    mock_cap = create_mock_cap()
    mock_video_capture.return_value = mock_cap

    # Mock imencode to raise exception
    with patch("cv2.imencode", side_effect=Exception("Encode failed")):
        input_data = VideoAnalysisInput(file_path="test.mp4")
        result = analyzer.analyze(input_data)

    assert result.thumbnail_data is None
    assert result.duration == 10.0


def test_cap_set_failure(analyzer, mock_video_capture, mock_exists, mock_isdir):
    """Test warning logging when cap.set fails."""
    mock_cap = create_mock_cap()
    # cap.set returns False
    mock_cap.set.return_value = False
    mock_video_capture.return_value = mock_cap

    input_data = VideoAnalysisInput(file_path="test.mp4")
    result = analyzer.analyze(input_data)

    # Should still succeed
    assert result.intensity_score >= 0.0


def test_zero_frame_count(analyzer, mock_video_capture, mock_exists, mock_isdir):
    """Test handling of zero frame count in thumbnail extraction."""
    # Frame count 0 leads to thumbnail extraction returning None
    mock_cap = create_mock_cap(frame_count=0)

    # We still want reads to succeed for intensity calculation to prove it continues
    # create_mock_cap default behavior provides reads

    mock_video_capture.return_value = mock_cap

    input_data = VideoAnalysisInput(file_path="test.mp4")
    result = analyzer.analyze(input_data)

    assert result.thumbnail_data is None
    # Verify intensity was still calculated (meaning it didn't crash)
    assert result.intensity_score >= 0.0


def test_small_video_no_resize(analyzer, mock_video_capture, mock_exists, mock_isdir):
    """Test that small videos are not resized during thumbnail extraction."""
    # Width 100 < 160
    mock_cap = create_mock_cap(width=100, height=100)
    mock_video_capture.return_value = mock_cap

    # Use real cv2.imencode to verify it works with small frame
    # We don't mock imencode here

    input_data = VideoAnalysisInput(file_path="small.mp4")
    result = analyzer.analyze(input_data)

    assert result.thumbnail_data is not None


# ---------------------------------------------------------------------------
# FEAT-020: Scene-change detection and opening intensity
# ---------------------------------------------------------------------------


def _create_scene_change_cap(
    fps=30.0,
    frame_count=300,
    change_interval=5,
):
    """Create a mock cap that alternates black/white frames every N frames.

    This produces large absdiff values at every ``change_interval`` boundary,
    simulating scene changes.  The ``change_interval`` is in *raw* frame
    indices (not sampled frames).
    """
    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = True

    props = {
        cv2.CAP_PROP_FPS: fps,
        cv2.CAP_PROP_FRAME_COUNT: frame_count,
        cv2.CAP_PROP_FRAME_WIDTH: 320.0,
        cv2.CAP_PROP_FRAME_HEIGHT: 180.0,
    }
    mock_cap.get.side_effect = lambda p: props.get(p, 0.0)
    mock_cap.set.return_value = True

    # Build frame sequence: alternate black / white at change_interval
    black = np.zeros((180, 320, 3), dtype=np.uint8)
    white = np.full((180, 320, 3), 255, dtype=np.uint8)

    reads = []
    # First read is for thumbnail extraction
    reads.append((True, black.copy()))
    # Remaining reads for intensity / scene-change loop
    for i in range(int(frame_count)):
        is_white = (i // change_interval) % 2 == 1
        reads.append((True, white.copy() if is_white else black.copy()))
    reads.append((False, None))

    mock_cap.read.side_effect = reads
    return mock_cap


def test_scene_changes_detected(analyzer, mock_video_capture, mock_exists, mock_isdir):
    """FEAT-020: Alternating black/white frames produce scene-change timestamps."""
    # change_interval=10 at fps=30 → scene change every ~0.33s
    mock_cap = _create_scene_change_cap(fps=30.0, frame_count=90, change_interval=10)
    mock_video_capture.return_value = mock_cap

    input_data = VideoAnalysisInput(file_path="scene_test.mp4")
    result = analyzer.analyze(input_data)

    assert len(result.scene_changes) > 0, "Expected at least one scene change"
    # Timestamps should be positive floats
    for t in result.scene_changes:
        assert t > 0.0


def test_scene_changes_capped_at_max(
    analyzer,
    mock_video_capture,
    mock_exists,
    mock_isdir,
):
    """FEAT-020: At most MAX_SCENE_CHANGES entries are returned."""
    # Many rapid changes to exceed cap
    mock_cap = _create_scene_change_cap(
        fps=30.0,
        frame_count=600,
        change_interval=10,
    )
    mock_video_capture.return_value = mock_cap

    input_data = VideoAnalysisInput(file_path="many_changes.mp4")
    result = analyzer.analyze(input_data)

    assert len(result.scene_changes) <= MAX_SCENE_CHANGES


def test_no_scene_changes_for_uniform_video(
    analyzer,
    mock_video_capture,
    mock_exists,
    mock_isdir,
):
    """FEAT-020: All-black frames produce no scene changes."""
    mock_cap = create_mock_cap()  # All identical black frames
    mock_video_capture.return_value = mock_cap

    input_data = VideoAnalysisInput(file_path="uniform.mp4")
    result = analyzer.analyze(input_data)

    assert result.scene_changes == []


def test_opening_intensity_computed(
    analyzer,
    mock_video_capture,
    mock_exists,
    mock_isdir,
):
    """FEAT-020: opening_intensity is non-zero for frames with motion in first 2s."""
    # Scene changes in the first 2 seconds produce high opening_intensity
    mock_cap = _create_scene_change_cap(fps=30.0, frame_count=90, change_interval=10)
    mock_video_capture.return_value = mock_cap

    input_data = VideoAnalysisInput(file_path="opener.mp4")
    result = analyzer.analyze(input_data)

    assert result.opening_intensity > 0.0


def test_opening_intensity_zero_for_static(
    analyzer,
    mock_video_capture,
    mock_exists,
    mock_isdir,
):
    """FEAT-020: Static frames produce opening_intensity == 0.0."""
    mock_cap = create_mock_cap()
    mock_video_capture.return_value = mock_cap

    input_data = VideoAnalysisInput(file_path="static.mp4")
    result = analyzer.analyze(input_data)

    assert result.opening_intensity == 0.0
