"""Application-layer orchestration for the full pipeline CLI."""

from __future__ import annotations

import argparse
import os
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from src.cli_utils import build_pacing_kwargs, detect_broll_dir, parse_duration
from src.config.app_config import PipelineConfig, load_app_config
from src.core.app import BachataSyncEngine
from src.core.audio_analyzer import AudioAnalyzer
from src.core.audio_mixer import (
    SUPPORTED_AUDIO_EXTENSIONS,
    resolve_audio_path_with_segments,
)
from src.core.models import AudioAnalysisResult, PacingConfig, VideoAnalysisResult
from src.ui.console import PipelineLogger, RichProgressObserver

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass(frozen=True)
class PipelineWorkflowDependencies:
    """Function dependencies supplied by the CLI module."""

    discover_audio_files: Callable[[str], list[str]]
    extract_track_metadata: Callable[[str, PipelineConfig], tuple[str, str]]
    scan_videos: Callable[
        [BachataSyncEngine, str, str | None],
        tuple[list[VideoAnalysisResult], list[VideoAnalysisResult] | None],
    ]
    run_dry_run_phase: Callable[
        [
            argparse.Namespace,
            BachataSyncEngine,
            AudioAnalyzer,
            list[str],
            dict[str, Any],
            PacingConfig,
            PipelineConfig,
            list[VideoAnalysisResult],
            str | None,
            PipelineLogger,
            str,
        ],
        None,
    ]
    generate_mix_video_phase: Callable[
        [
            argparse.Namespace,
            BachataSyncEngine,
            AudioAnalyzer,
            dict[str, Any],
            list[VideoAnalysisResult],
            list[VideoAnalysisResult] | None,
            str | None,
            PipelineLogger,
            str,
            list[dict[str, Any]],
        ],
        tuple[str, AudioAnalysisResult],
    ]
    process_individual_tracks: Callable[
        [
            argparse.Namespace,
            BachataSyncEngine,
            AudioAnalyzer,
            list[str],
            dict[str, Any],
            PacingConfig,
            PipelineConfig,
            list[VideoAnalysisResult],
            list[VideoAnalysisResult] | None,
            str | None,
            PipelineLogger,
            float,
            float,
        ],
        tuple[list[str], list[str], list[str]],
    ]
    generate_compilation_phase: Callable[
        [Any, argparse.Namespace, list[str], list[str], PipelineLogger],
        str | None,
    ]
    write_summary: Callable[
        [
            argparse.Namespace,
            list[str],
            dict[str, Any],
            list[VideoAnalysisResult] | None,
            PipelineLogger,
            float,
            AudioAnalysisResult | None,
        ],
        None,
    ]


class PipelineWorkflow:
    """Runs the full pipeline orchestration independent of CLI concerns."""

    def __init__(self, deps: PipelineWorkflowDependencies) -> None:
        self._deps = deps

    def run(self, args: argparse.Namespace, log: PipelineLogger) -> None:
        """Run the end-to-end pipeline workflow."""
        t0 = time.time()

        audio_dir = args.audio
        if not os.path.isdir(audio_dir):
            raise NotADirectoryError(audio_dir)

        os.makedirs(args.output_dir, exist_ok=True)
        min_dur, max_dur = parse_duration(args.shorts_duration)

        app_config = load_app_config()
        base_pacing = app_config.pacing
        pipeline_config = app_config.pipeline
        pacing_kwargs = {**base_pacing.model_dump(), **build_pacing_kwargs(args)}

        engine = BachataSyncEngine()
        analyzer = AudioAnalyzer()
        generated_files: list[str] = []

        # 1. Discover individual audio files
        log.phase("🔍 Discovering Audio")
        individual_tracks = self._deps.discover_audio_files(audio_dir)
        if not individual_tracks:
            raise FileNotFoundError(
                "No supported audio files found in "
                f"{audio_dir}. Supported formats: "
                + ", ".join(sorted(SUPPORTED_AUDIO_EXTENSIONS))
            )
        log.step(
            f"Found {len(individual_tracks)} track(s) in [bold]{audio_dir}[/bold]"
        )

        # 2. Mix tracks
        log.phase("🎵 Mixing Audio")
        with log.status(f"Mixing {len(individual_tracks)} tracks…"):
            with RichProgressObserver() as obs:
                mix_path, mix_track_starts = resolve_audio_path_with_segments(
                    audio_dir, observer=obs
                )
        log.success(f"Mix ready: [bold]{mix_path}[/bold]")

        # Build MixTrackSegments for mix video cold opens + fades (FEAT-050).
        mix_track_segments: list[dict[str, Any]] = []
        if mix_track_starts:
            for src_path, start_time in mix_track_starts:
                artist, title = self._deps.extract_track_metadata(
                    src_path, pipeline_config
                )
                mix_track_segments.append(
                    {
                        "artist": artist,
                        "title": title,
                        "start_time": start_time,
                        "audio_path": src_path,
                    }
                )

        # 3. Detect B-roll
        broll_dir = detect_broll_dir(args.video_dir, args.broll_dir)
        if broll_dir:
            log.step(f"B-roll directory: [bold]{broll_dir}[/bold]")
        else:
            log.detail("No B-roll directory detected")

        # 4. Shared scan (if enabled)
        shared_clips: list[VideoAnalysisResult] = []
        shared_broll: list[VideoAnalysisResult] | None = None
        if args.shared_scan:
            log.phase("📹 Scanning Video Library")
            with log.status("Scanning clips…"):
                shared_clips, shared_broll = self._deps.scan_videos(
                    engine, args.video_dir, broll_dir
                )
            clip_msg = f"Found {len(shared_clips)} main clip(s)"
            if shared_broll:
                clip_msg += f", {len(shared_broll)} B-roll"
            log.step(clip_msg)

        # 5. Dry-run — plan-only, skip all rendering
        if pacing_kwargs.get("dry_run"):
            self._deps.run_dry_run_phase(
                args,
                engine,
                analyzer,
                individual_tracks,
                pacing_kwargs,
                base_pacing,
                pipeline_config,
                shared_clips,
                broll_dir,
                log,
                mix_path,
            )
            return

        # 6. Generate mix video
        mix_meta: AudioAnalysisResult | None = None
        if not args.skip_mix:
            mix_result, mix_meta = self._deps.generate_mix_video_phase(
                args,
                engine,
                analyzer,
                pacing_kwargs,
                shared_clips,
                shared_broll,
                broll_dir,
                log,
                mix_path,
                mix_track_segments,
            )
            generated_files.append(mix_result)

        # 7. Per-track: video + shorts
        track_files, track_videos, track_audio_files = (
            self._deps.process_individual_tracks(
                args,
                engine,
                analyzer,
                individual_tracks,
                pacing_kwargs,
                base_pacing,
                pipeline_config,
                shared_clips,
                shared_broll,
                broll_dir,
                log,
                min_dur,
                max_dur,
            )
        )
        generated_files.extend(track_files)

        # 8. Generate compilation video
        compilation_result = self._deps.generate_compilation_phase(
            app_config, args, track_videos, track_audio_files, log
        )
        if compilation_result:
            generated_files.append(compilation_result)

        # 9. Summary
        elapsed = time.time() - t0
        last_audio_meta = mix_meta  # may be None if --skip-mix
        clips_for_summary = shared_clips if shared_clips else None
        self._deps.write_summary(
            args,
            generated_files,
            pacing_kwargs,
            clips_for_summary,
            log,
            elapsed,
            last_audio_meta,
        )
