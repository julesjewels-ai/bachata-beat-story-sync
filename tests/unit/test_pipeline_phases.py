"""Tests for pipeline phase resilience (graceful degradation)."""

from argparse import Namespace
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from src.application.pipeline_phases import (
    PipelinePhaseSupport,
    generate_mix_video_phase,
)
from src.core.models import AudioAnalysisResult, VideoAnalysisResult


def _fake_log() -> MagicMock:
    """A PipelineLogger stand-in whose status() is a context manager."""
    log = MagicMock()

    @contextmanager
    def _status(_msg):
        yield

    log.status.side_effect = _status
    return log


def _mix_meta() -> AudioAnalysisResult:
    return AudioAnalysisResult(
        filename="_mixed_audio.wav",
        bpm=120.0,
        duration=180.0,
        peaks=[],
        sections=[],
        beat_times=[float(i) * 0.5 for i in range(16)],
        intensity_curve=[0.5] * 16,
    )


def _clips() -> list[VideoAnalysisResult]:
    return [
        VideoAnalysisResult(
            path="/videos/clip1.mp4",
            intensity_score=0.7,
            duration=30.0,
            thumbnail_data=None,
        ),
    ]


def _support() -> PipelinePhaseSupport:
    return PipelinePhaseSupport(
        scan_videos=MagicMock(),
        safe_filename=MagicMock(),
        get_track_video_dir=MagicMock(),
        get_track_video_style=MagicMock(),
        extract_track_metadata=MagicMock(),
    )


@patch("src.application.pipeline_phases.generate_video")
def test_mix_phase_returns_none_on_render_failure_instead_of_raising(
    mock_generate, tmp_path
):
    """A mix render failure degrades to (None, mix_meta) so the pipeline
    can continue with individual track videos rather than aborting."""
    mock_generate.side_effect = ValueError(
        "Invalid segment plan: under-covers target duration"
    )
    mix_path = tmp_path / "_mixed_audio.wav"
    mix_path.write_bytes(b"RIFF")
    analyzer = MagicMock()
    mix_meta = _mix_meta()
    analyzer.analyze.return_value = mix_meta
    log = _fake_log()
    args = Namespace(shared_scan=True, output_dir=str(tmp_path), video_dir="/videos")

    result, returned_meta = generate_mix_video_phase(
        _support(),
        args,
        engine=MagicMock(),
        analyzer=analyzer,
        pacing_kwargs={},
        shared_clips=_clips(),
        shared_broll=None,
        broll_dir=None,
        log=log,
        mix_path=str(mix_path),
        mix_track_segments=[],
    )

    assert result is None
    assert returned_meta is mix_meta
    log.warn.assert_called_once()


@patch("src.application.pipeline_phases.generate_video")
def test_mix_phase_returns_path_on_success(mock_generate, tmp_path):
    """Happy path still returns the rendered mix path."""
    expected = str(tmp_path / "mix.mp4")
    mock_generate.return_value = expected
    mix_path = tmp_path / "_mixed_audio.wav"
    mix_path.write_bytes(b"RIFF")
    analyzer = MagicMock()
    analyzer.analyze.return_value = _mix_meta()
    args = Namespace(shared_scan=True, output_dir=str(tmp_path), video_dir="/videos")

    result, _ = generate_mix_video_phase(
        _support(),
        args,
        engine=MagicMock(),
        analyzer=analyzer,
        pacing_kwargs={},
        shared_clips=_clips(),
        shared_broll=None,
        broll_dir=None,
        log=_fake_log(),
        mix_path=str(mix_path),
        mix_track_segments=[],
    )

    assert result == expected
