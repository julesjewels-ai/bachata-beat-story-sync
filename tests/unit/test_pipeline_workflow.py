import argparse
from pathlib import Path
from typing import cast
from unittest.mock import MagicMock, Mock

import pytest
from pytest_mock import MockerFixture
from src.application.pipeline_workflow import (
    PipelineWorkflow,
    PipelineWorkflowDependencies,
)
from src.core.models import AudioAnalysisResult
from src.ui.console import PipelineLogger


@pytest.fixture
def mock_deps() -> PipelineWorkflowDependencies:
    return PipelineWorkflowDependencies(
        discover_audio_files=Mock(),
        extract_track_metadata=Mock(),
        scan_videos=Mock(),
        run_dry_run_phase=Mock(),
        generate_mix_video_phase=Mock(),
        process_individual_tracks=Mock(),
        generate_compilation_phase=Mock(),
        write_summary=Mock(),
    )


@pytest.fixture
def base_args(tmp_path: Path) -> argparse.Namespace:
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()

    video_dir = tmp_path / "video"
    video_dir.mkdir()

    out_dir = tmp_path / "out"

    args = argparse.Namespace()
    args.audio = str(audio_dir)
    args.output_dir = str(out_dir)
    args.video_dir = str(video_dir)
    args.broll_dir = None
    args.shorts_duration = "15-30"
    args.shared_scan = False
    args.skip_mix = False
    args.transcribe = False
    args.youtube_metadata = False
    args.dry_run = False
    return args


def test_workflow_basic(
    mock_deps: PipelineWorkflowDependencies, base_args: argparse.Namespace
) -> None:
    workflow = PipelineWorkflow(mock_deps)
    logger = MagicMock(spec=PipelineLogger)

    cast(Mock, mock_deps.discover_audio_files).return_value = ["track1.wav"]
    cast(Mock, mock_deps.process_individual_tracks).return_value = (
        ["out1.mp4"],
        ["vid1.mp4"],
        ["aud1.wav"],
    )
    cast(Mock, mock_deps.generate_mix_video_phase).return_value = (
        "mix.mp4",
        AudioAnalysisResult(
            filename="mix",
            duration=60.0,
            bpm=120.0,
            peaks=[],
            sections=[],
            beat_times=[],
            intensity_curve=[],
        ),
    )
    cast(Mock, mock_deps.generate_compilation_phase).return_value = "comp.mp4"

    with pytest.raises(NotADirectoryError):
        args = argparse.Namespace()
        args.audio = "/fake/dir"
        workflow.run(args, logger)


@pytest.mark.parametrize(
    "case_desc, discover_files, has_broll, shared_scan, skip_mix, "
    "dry_run, transcribe, expected_phases, expected_exception",
    [
        (
            "dry_run_only",
            ["track1.wav"],
            False,
            False,
            False,
            True,
            False,
            ["discover", "dry_run"],
            None,
        ),
        (
            "full_pipeline_no_broll",
            ["track1.wav", "track2.wav"],
            False,
            True,
            False,
            False,
            True,
            ["discover", "scan", "mix", "process", "comp", "transcribe", "summary"],
            None,
        ),
        (
            "skip_mix_with_broll",
            ["track1.wav"],
            True,
            True,
            True,
            False,
            False,
            ["discover", "scan", "process", "comp", "summary"],
            None,
        ),
        (
            "no_audio_files_found",
            [],
            False,
            False,
            False,
            False,
            False,
            [],
            FileNotFoundError,
        ),
        (
            "invalid_audio_dir",
            ["track1.wav"],
            False,
            False,
            False,
            False,
            False,
            [],
            NotADirectoryError,
        ),
    ],
)
def test_workflow_parametrized(
    mocker: MockerFixture,
    mock_deps: PipelineWorkflowDependencies,
    base_args: argparse.Namespace,
    tmp_path: Path,
    case_desc: str,
    discover_files: list[str],
    has_broll: bool,
    shared_scan: bool,
    skip_mix: bool,
    dry_run: bool,
    transcribe: bool,
    expected_phases: list[str],
    expected_exception: type[Exception] | None,
) -> None:
    workflow = PipelineWorkflow(mock_deps)
    logger = MagicMock(spec=PipelineLogger)

    # Setup args
    base_args.shared_scan = shared_scan
    base_args.skip_mix = skip_mix
    base_args.dry_run = dry_run
    base_args.transcribe = transcribe

    if has_broll:
        broll_dir = tmp_path / "broll"
        broll_dir.mkdir()
        base_args.broll_dir = str(broll_dir)

    if expected_exception is NotADirectoryError:
        base_args.audio = "/fake/dir"

    # Setup mocks
    cast(Mock, mock_deps.discover_audio_files).return_value = discover_files
    cast(Mock, mock_deps.extract_track_metadata).return_value = ("Artist", "Title")
    cast(Mock, mock_deps.scan_videos).return_value = (
        [Mock()],
        [Mock()] if has_broll else None,
    )

    cast(Mock, mock_deps.generate_mix_video_phase).return_value = (
        "mix.mp4",
        Mock(duration=60.0),
    )
    cast(Mock, mock_deps.process_individual_tracks).return_value = (
        ["out1.mp4"],
        ["vid1.mp4"],
        ["aud1.wav"],
    )
    cast(Mock, mock_deps.generate_compilation_phase).return_value = "comp.mp4"

    mocker.patch(
        "src.application.pipeline_workflow.resolve_audio_path_with_segments",
        return_value=("mix.wav", [("track1.wav", 0.0)]),
    )
    mocker.patch(
        "src.application.pipeline_workflow.transcribe_compilation_phase",
        return_value=["comp.srt"],
    )
    mocker.patch(
        "src.application.pipeline_workflow.generate_youtube_metadata_phase",
        return_value=["yt.json"],
    )

    # Act & Assert
    if isinstance(expected_exception, type) and issubclass(
        expected_exception, Exception
    ):
        with pytest.raises(expected_exception):
            workflow.run(base_args, logger)
    else:
        workflow.run(base_args, logger)

        # Assert successful branches
        assert cast(Mock, mock_deps.discover_audio_files).called, (
            "Expected discover_audio_files to be called to find tracks"
        )

        if "scan" in expected_phases:
            assert cast(Mock, mock_deps.scan_videos).called, (
                "Expected scan_videos to be called when shared_scan is enabled"
            )
        else:
            assert not cast(Mock, mock_deps.scan_videos).called, (
                "Did not expect scan_videos to be called"
            )

        if "dry_run" in expected_phases:
            assert cast(Mock, mock_deps.run_dry_run_phase).called, (
                "Expected run_dry_run_phase to be called when dry_run is True"
            )
            assert not cast(Mock, mock_deps.generate_mix_video_phase).called, (
                "Did not expect generate_mix_video_phase to be called during dry run"
            )
            assert not cast(Mock, mock_deps.process_individual_tracks).called, (
                "Did not expect process_individual_tracks to be called during dry run"
            )
        else:
            assert not cast(Mock, mock_deps.run_dry_run_phase).called, (
                "Did not expect run_dry_run_phase to be called when dry_run is False"
            )

            if "mix" in expected_phases:
                assert cast(Mock, mock_deps.generate_mix_video_phase).called, (
                    "Expected generate_mix_video_phase to be called without skip"
                )
            else:
                assert not cast(Mock, mock_deps.generate_mix_video_phase).called, (
                    "Did not expect generate_mix_video_phase to be called with skip"
                )

            assert cast(Mock, mock_deps.process_individual_tracks).called, (
                "Expected process_individual_tracks to be called during standard run"
            )
            assert cast(Mock, mock_deps.generate_compilation_phase).called, (
                "Expected generate_compilation_phase to be called during standard run"
            )
            assert cast(Mock, mock_deps.write_summary).called, (
                "Expected write_summary to be called to finalize output"
            )
