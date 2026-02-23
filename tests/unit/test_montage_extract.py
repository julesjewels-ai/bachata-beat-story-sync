"""
Tests for MontageGenerator.generate and _extract_segments edge cases.
"""
import pytest
import os
from unittest.mock import patch, MagicMock
from src.core.montage import MontageGenerator
from src.core.models import (
    AudioAnalysisResult,
    VideoAnalysisResult,
    PacingConfig,
)
from src.core.interfaces import ProgressObserver

@pytest.fixture
def generator():
    return MontageGenerator()

@pytest.fixture
def audio_data():
    return AudioAnalysisResult(
        filename="test.wav",
        bpm=120.0,
        duration=10.0,
        peaks=[],
        sections=[],
        beat_times=[float(i) * 0.5 for i in range(20)],
        intensity_curve=[0.5] * 20,
    )

@pytest.fixture
def video_clips():
    return [
        VideoAnalysisResult(
            path="/videos/clip1.mp4",
            intensity_score=0.5,
            duration=10.0,
            thumbnail_data=None,
        ),
    ]

@patch("src.core.montage.shutil.which", return_value="/usr/bin/ffmpeg")
@patch("src.core.montage.subprocess.run")
@patch("src.core.montage.tempfile.mkdtemp")
@patch("src.core.montage.shutil.rmtree")
@patch("src.core.montage.os.path.exists")
@patch("src.core.montage.os.remove")
def test_generate_skips_missing_files(
    mock_remove, mock_exists, mock_rmtree, mock_mkdtemp, mock_run, mock_which,
    generator, audio_data, video_clips, tmp_path
):
    """
    Test that generate() skips segments where the source video file is missing.
    This covers the `if not os.path.exists(seg.video_path): continue` branch.
    """
    temp_dir = tmp_path / "montage_temp"
    temp_dir.mkdir()
    mock_mkdtemp.return_value = str(temp_dir)

    def exists_side_effect(path):
        if path == "/videos/clip1.mp4":
            return False
        return True
    mock_exists.side_effect = exists_side_effect

    def run_side_effect(*args, **kwargs):
        cmd = args[0] if args else kwargs.get("cmd")
        if cmd and "-f" in cmd and "concat" in cmd:
            out_file = cmd[-1]
            with open(out_file, "w") as f:
                f.write("dummy video")
        return MagicMock(returncode=0, stderr="")
    mock_run.side_effect = run_side_effect

    output_path = str(tmp_path / "output.mp4")
    generator.generate(audio_data, video_clips, output_path)

    mock_exists.assert_any_call("/videos/clip1.mp4")
    concat_list_path = str(temp_dir / "concat_output.mp4.txt")
    mock_remove.assert_called_with(concat_list_path)

@patch("src.core.montage.shutil.which", return_value="/usr/bin/ffmpeg")
@patch("src.core.montage.subprocess.run")
@patch("src.core.montage.tempfile.mkdtemp")
@patch("src.core.montage.shutil.rmtree")
@patch("src.core.montage.os.path.exists", return_value=True)
def test_generate_with_observer_and_speed_ramp(
    mock_exists, mock_rmtree, mock_mkdtemp, mock_run, mock_which,
    generator, audio_data, video_clips, tmp_path
):
    """
    Test generate() with:
    1. A ProgressObserver (covers observer callbacks)
    2. Speed ramping enabled (covers setpts filter)
    """
    temp_dir = tmp_path / "montage_temp"
    temp_dir.mkdir(exist_ok=True)
    mock_mkdtemp.return_value = str(temp_dir)

    # Mock FFmpeg success
    mock_run.return_value = MagicMock(returncode=0, stderr="")

    # Observer mock
    observer = MagicMock(spec=ProgressObserver)

    # Config with speed ramping enabled and high intensity to trigger speed change
    # Force intensity to be high for the audio
    audio_high = audio_data.model_copy(update={"intensity_curve": [0.9] * 20})

    # Pacing config: speed_ramp_enabled=True (default), high_intensity_speed != 1.0
    config = PacingConfig(
        speed_ramp_enabled=True,
        high_intensity_speed=1.5
    )

    output_path = str(tmp_path / "output_speed.mp4")

    # Need to make sure concat file is created or mock shutil.move
    # Since we are mocking run, we need to create the file during concat
    def run_side_effect(*args, **kwargs):
        cmd = args[0] if args else kwargs.get("cmd")
        # Check for concat
        if cmd and "-f" in cmd and "concat" in cmd:
            out_file = cmd[-1]
            with open(out_file, "w") as f:
                f.write("dummy video")
        return MagicMock(returncode=0, stderr="")
    mock_run.side_effect = run_side_effect

    generator.generate(
        audio_high, video_clips, output_path,
        observer=observer,
        pacing=config
    )

    # Verify observer was called
    observer.on_progress.assert_called()

    # Verify setpts filter was used in FFmpeg command
    # Look for calls to run with "setpts=PTS/1.5"
    setpts_called = False
    for call_args in mock_run.call_args_list:
        cmd = call_args[0][0] if call_args[0] else call_args[1].get("cmd", [])
        if any("setpts=PTS/1.5" in arg for arg in cmd):
            setpts_called = True
            break

    assert setpts_called, "FFmpeg command should include setpts filter for speed ramping"
