"""Phase implementations for the full pipeline workflow."""

from __future__ import annotations

import argparse
import logging
import os
import uuid
from dataclasses import dataclass
from typing import Any

from src.cli_utils import generate_shorts_batch, run_dry_run_handler, strip_thumbnails
from src.config.app_config import PipelineConfig
from src.core.audio_analyzer import AudioAnalysisInput, AudioAnalyzer
from src.core.compilation import generate_compilation
from src.core.models import AudioAnalysisResult, PacingConfig, VideoAnalysisResult
from src.ui.console import PipelineLogger, RichProgressObserver

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PipelinePhaseSupport:
    """Small dependency bundle for the pipeline phase functions."""

    scan_videos: Any
    safe_filename: Any
    get_track_video_dir: Any
    get_track_video_style: Any
    extract_track_metadata: Any


def generate_video(
    engine: Any,
    audio_meta: AudioAnalysisResult,
    clips: list[VideoAnalysisResult],
    output_path: str,
    audio_path: str,
    pacing_kwargs: dict[str, Any],
    broll_clips: list[VideoAnalysisResult] | None = None,
) -> str:
    """Generate a single horizontal music video."""
    pacing = PacingConfig(**pacing_kwargs) if pacing_kwargs else None
    with RichProgressObserver() as obs:
        return engine.generate_story(
            audio_meta,
            clips,
            output_path,
            broll_clips=broll_clips,
            audio_path=audio_path,
            observer=obs,
            pacing=pacing,
        )


def run_dry_run_phase(
    support: PipelinePhaseSupport,
    args: argparse.Namespace,
    engine: Any,
    analyzer: AudioAnalyzer,
    individual_tracks: list[str],
    pacing_kwargs: dict[str, Any],
    base_pacing: PacingConfig,
    pipeline_config: PipelineConfig,
    shared_clips: list[VideoAnalysisResult],
    broll_dir: str | None,
    log: PipelineLogger,
    mix_path: str,
) -> None:
    """Phase: dry-run, plan only, skip rendering."""
    reports: list[str] = []

    if not args.skip_mix:
        mix_audio_input = AudioAnalysisInput(file_path=mix_path)
        with log.status("Analyzing mix audio…"):
            mix_meta = analyzer.analyze(mix_audio_input)
        clips_for_mix = (
            shared_clips
            if args.shared_scan
            else support.scan_videos(engine, args.video_dir, broll_dir)[0]
        )
        report = run_dry_run_handler(
            engine,
            mix_meta,
            clips_for_mix,
            pacing_kwargs,
            dry_run_output=None,
            output_json=getattr(args, "output_json", None),
            report_prefix="=== Mix ===\n",
        )
        reports.append(report)

    for idx, track_path in enumerate(individual_tracks, start=1):
        track_name = support.safe_filename(track_path)
        track_input = AudioAnalysisInput(file_path=track_path)
        with log.status(f"Analyzing track {idx} audio…"):
            track_meta = analyzer.analyze(track_input)

        track_video_dir = support.get_track_video_dir(
            track_path, pipeline_config, args.video_dir
        )
        clips_for_track = (
            shared_clips
            if args.shared_scan
            else support.scan_videos(engine, track_video_dir, broll_dir)[0]
        )

        track_pacing_kwargs = {**pacing_kwargs, "prefix_offset": idx - 1}
        track_style = support.get_track_video_style(
            track_path,
            pipeline_config,
            base_pacing.video_style,
        )
        if track_style != base_pacing.video_style:
            track_pacing_kwargs["video_style"] = track_style

        track_artist, track_title = support.extract_track_metadata(
            track_path, pipeline_config
        )
        if track_artist:
            track_pacing_kwargs["track_artist"] = track_artist
        if track_title:
            track_pacing_kwargs["track_title"] = track_title

        report = run_dry_run_handler(
            engine,
            track_meta,
            clips_for_track,
            track_pacing_kwargs,
            dry_run_output=None,
            output_json=getattr(args, "output_json", None) if not reports else None,
            report_prefix=f"=== Track {idx}: {track_name} ===\n",
        )
        reports.append(report)

    from src.services.plan_report import write_plan_report  # noqa: WPS433

    write_plan_report(
        "\n\n".join(reports),
        getattr(args, "dry_run_output", None),
    )

    log.step("Dry-run complete — no videos rendered.")


def generate_mix_video_phase(
    support: PipelinePhaseSupport,
    args: argparse.Namespace,
    engine: Any,
    analyzer: AudioAnalyzer,
    pacing_kwargs: dict[str, Any],
    shared_clips: list[VideoAnalysisResult],
    shared_broll: list[VideoAnalysisResult] | None,
    broll_dir: str | None,
    log: PipelineLogger,
    mix_path: str,
    mix_track_segments: list[dict[str, Any]],
) -> tuple[str, AudioAnalysisResult]:
    """Phase: generate the combined mix video."""
    log.phase("🎬 Generating Mix Video")
    mix_audio_input = AudioAnalysisInput(file_path=mix_path)
    with log.status("Analyzing mix audio…"):
        mix_meta = analyzer.analyze(mix_audio_input)
    log.detail(
        f"BPM={mix_meta.bpm:.1f}  peaks={len(mix_meta.peaks)}"
        f"  duration={mix_meta.duration:.1f}s"
    )

    if args.shared_scan:
        clips, broll = shared_clips, shared_broll
    else:
        with log.status("Scanning video library…"):
            clips, broll = support.scan_videos(engine, args.video_dir, broll_dir)

    mix_out = os.path.join(args.output_dir, "mix.mp4")
    mix_pacing_kwargs = dict(pacing_kwargs)
    if mix_track_segments:
        mix_pacing_kwargs["mix_track_segments"] = mix_track_segments
        mix_pacing_kwargs["mix_fade_transitions"] = True
    with log.status("Rendering mix video…"):
        result = generate_video(
            engine,
            mix_meta,
            clips,
            mix_out,
            mix_path,
            mix_pacing_kwargs,
            broll_clips=broll,
        )
    log.success(f"Mix video: [bold]{result}[/bold]")
    return result, mix_meta


def process_individual_tracks(
    support: PipelinePhaseSupport,
    args: argparse.Namespace,
    engine: Any,
    analyzer: AudioAnalyzer,
    individual_tracks: list[str],
    pacing_kwargs: dict[str, Any],
    base_pacing: PacingConfig,
    pipeline_config: PipelineConfig,
    shared_clips: list[VideoAnalysisResult],
    shared_broll: list[VideoAnalysisResult] | None,
    broll_dir: str | None,
    log: PipelineLogger,
    min_dur: float,
    max_dur: float,
) -> tuple[list[str], list[str], list[str]]:
    """Phase: generate per-track videos and shorts."""
    generated_files: list[str] = []
    track_videos: list[str] = []
    track_audio_files: list[str] = []

    for idx, track_path in enumerate(individual_tracks, start=1):
        track_name = support.safe_filename(track_path)
        track_label = f"track_{idx:02d}_{track_name}"

        log.phase(f"🎸 Track {idx}/{len(individual_tracks)}: {track_name}")

        track_input = AudioAnalysisInput(file_path=track_path)
        with log.status("Analyzing track audio…"):
            track_meta = analyzer.analyze(track_input)
        log.detail(
            f"BPM={track_meta.bpm:.1f}  peaks={len(track_meta.peaks)}"
            f"  duration={track_meta.duration:.1f}s"
        )

        track_video_dir = support.get_track_video_dir(
            track_path, pipeline_config, args.video_dir
        )

        if args.shared_scan:
            clips, broll = shared_clips, shared_broll
        else:
            with log.status("Scanning video library…"):
                clips, broll = support.scan_videos(engine, track_video_dir, broll_dir)

        track_seed = pacing_kwargs.get("seed") or str(uuid.uuid4())
        track_pacing = {
            **pacing_kwargs,
            "prefix_offset": idx - 1,
            "seed": f"{track_seed}_track_{idx}",
        }
        track_style = support.get_track_video_style(
            track_path,
            pipeline_config,
            base_pacing.video_style,
        )
        if track_style != base_pacing.video_style:
            track_pacing["video_style"] = track_style

        track_artist, track_title = support.extract_track_metadata(
            track_path, pipeline_config
        )
        if track_artist:
            track_pacing["track_artist"] = track_artist
        if track_title:
            track_pacing["track_title"] = track_title

        track_out = os.path.join(args.output_dir, f"{track_label}.mp4")
        with log.status("Rendering track video…"):
            result = generate_video(
                engine,
                track_meta,
                clips,
                track_out,
                track_path,
                track_pacing,
                broll_clips=broll,
            )
        generated_files.append(result)
        log.success(f"Track video: [bold]{result}[/bold]")

        track_videos.append(result)
        track_audio_files.append(track_path)

        if args.shorts_count > 0:
            shorts_dir = os.path.join(args.output_dir, "shorts", f"track_{idx:02d}")
            with log.status(f"Rendering {args.shorts_count} short(s)…"):
                shorts = generate_shorts_batch(
                    engine,
                    track_meta,
                    clips,
                    track_path,
                    shorts_dir,
                    args.shorts_count,
                    min_dur,
                    max_dur,
                    track_pacing,
                    smart_start=args.smart_start,
                    dynamic_flow=getattr(args, "dynamic_flow", False),
                    human_touch=getattr(args, "human_touch", False),
                    cliffhanger=getattr(args, "cliffhanger", False),
                )
            generated_files.extend(shorts)
            log.success(f"{len(shorts)} short(s) saved in [bold]{shorts_dir}[/bold]")

    return generated_files, track_videos, track_audio_files


def generate_compilation_phase(
    app_config: Any,
    args: argparse.Namespace,
    track_videos: list[str],
    track_audio_files: list[str],
    log: PipelineLogger,
) -> str | None:
    """Phase: generate compilation video if enabled."""
    compilation_enabled = app_config.compilation.enabled
    if args.no_compilation:
        compilation_enabled = False
    elif args.compilation:
        compilation_enabled = True

    if not (compilation_enabled and track_videos):
        return None

    log.phase("🎞️  Generating Compilation Video")
    compilation_out = os.path.join(args.output_dir, "compilation.mp4")
    with log.status("Concatenating track videos…"):
        try:
            result = generate_compilation(
                track_videos,
                track_audio_files,
                compilation_out,
                app_config.compilation,
            )
            log.success(f"Compilation video: [bold]{result}[/bold]")

            chapters_path = compilation_out.replace(".mp4", "_chapters.json")
            if os.path.exists(chapters_path):
                chapters_txt = compilation_out.replace(".mp4", "_chapters.txt")
                log.detail(
                    f"Chapter markers: [bold]{chapters_txt}[/bold] "
                    "(paste into YouTube description)"
                )
            return result
        except Exception as e:
            log.warn(f"Compilation generation failed: {e}")
            logger.exception("Compilation error:")
            return None


def write_summary(
    args: argparse.Namespace,
    generated_files: list[str],
    pacing_kwargs: dict[str, Any],
    clips: list[VideoAnalysisResult] | None,
    log: PipelineLogger,
    elapsed: float,
    last_audio_meta: AudioAnalysisResult | None,
) -> None:
    """Phase: emit pipeline summary and optional JSON output."""
    log.summary(generated_files, elapsed)

    summary_path = os.path.join(args.output_dir, "pipeline_summary.txt")
    summary_lines = [
        f"Pipeline complete in {elapsed:.0f}s",
        f"Total files generated: {len(generated_files)}",
        "",
    ]
    for path in generated_files:
        summary_lines.append(f"  {path}")
    with open(summary_path, "w") as fh:
        fh.write("\n".join(summary_lines) + "\n")

    if getattr(args, "output_json", None) and last_audio_meta:
        from src.services.json_output import build_json_output, write_json_output

        data = build_json_output(
            last_audio_meta,
            strip_thumbnails(clips) if clips else [],
            None,
            PacingConfig(**pacing_kwargs),
        )
        data["generated_files"] = generated_files
        write_json_output(data, args.output_json)
