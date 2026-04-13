"""Shared single-track story workflow used by CLI and UI entry points."""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Protocol, cast

from src.cli_utils import analyze_audio, detect_broll_dir, strip_thumbnails
from src.core.app import BachataSyncEngine
from src.core.interfaces import ProgressObserver
from src.core.models import (
    AudioAnalysisResult,
    PacingConfig,
    SegmentPlan,
    VideoAnalysisResult,
)
from src.core.montage import load_pacing_config
from src.services.plan_report import format_plan_report

logger = logging.getLogger(__name__)


class ObserverFactory(Protocol):
    """Factory for progress observers."""

    def __call__(self) -> ProgressObserver | Any: ...


@dataclass
class StoryWorkflowResult:
    """Results of planning or rendering a single story video."""

    resolved_audio_path: str
    audio_meta: AudioAnalysisResult
    video_clips: list[VideoAnalysisResult]
    montage_clips: list[VideoAnalysisResult]
    broll_clips: list[VideoAnalysisResult] | None
    pacing: PacingConfig
    segments: list[SegmentPlan] | None = None
    plan_report: str | None = None
    output_path: str | None = None


def build_story_pacing(overrides: dict[str, Any] | None = None) -> PacingConfig:
    """Load base YAML config and apply runtime overrides."""
    base_config = load_pacing_config()
    merged = {**base_config.model_dump(), **(overrides or {})}
    return PacingConfig(**merged)


@contextmanager
def _observer_scope(
    factory: ObserverFactory | None,
) -> ProgressObserver | None:
    """Create an observer and enter it if it supports context management."""
    if factory is None:
        yield None
        return

    observer = factory()
    enter = getattr(observer, "__enter__", None)
    exit_ = getattr(observer, "__exit__", None)

    if callable(enter) and callable(exit_):
        with observer as managed:
            yield cast(ProgressObserver, managed)
        return

    yield cast(ProgressObserver, observer)


def _scan_clips(
    engine: BachataSyncEngine,
    directory: str,
    *,
    exclude_dirs: list[str] | None = None,
    observer_factory: ObserverFactory | None = None,
) -> list[VideoAnalysisResult]:
    """Scan a clip directory with an optional progress observer."""
    with _observer_scope(observer_factory) as observer:
        return engine.scan_video_library(
            directory,
            exclude_dirs=exclude_dirs,
            observer=observer,
        )


def run_story_workflow(
    audio_path: str,
    video_dir: str,
    output_path: str,
    *,
    broll_dir: str | None = None,
    pacing_overrides: dict[str, Any] | None = None,
    engine: BachataSyncEngine | None = None,
    scan_observer_factory: ObserverFactory | None = None,
    render_observer_factory: ObserverFactory | None = None,
) -> StoryWorkflowResult:
    """Run the shared single-track orchestration for planning or rendering."""
    engine = engine or BachataSyncEngine()

    resolved_audio_path, audio_meta = analyze_audio(audio_path)

    logger.info("Scanning video library in: %s", video_dir)
    resolved_broll_dir = detect_broll_dir(video_dir, broll_dir)
    exclude_dirs = [resolved_broll_dir] if resolved_broll_dir else None

    video_clips = _scan_clips(
        engine,
        video_dir,
        exclude_dirs=exclude_dirs,
        observer_factory=scan_observer_factory,
    )
    logger.info("Found %d suitable clips.", len(video_clips))

    broll_clips = None
    if resolved_broll_dir and os.path.exists(resolved_broll_dir):
        logger.info("Scanning B-roll library in: %s", resolved_broll_dir)
        broll_clips = _scan_clips(
            engine,
            resolved_broll_dir,
            observer_factory=scan_observer_factory,
        )
        logger.info("Found %d suitable B-roll clips.", len(broll_clips))

    pacing = build_story_pacing(pacing_overrides)
    montage_clips = strip_thumbnails(video_clips)

    if pacing.dry_run:
        segments = engine.plan_story(audio_meta, montage_clips, pacing=pacing)
        plan_report = format_plan_report(audio_meta, segments, montage_clips, pacing)
        logger.info("Dry-run complete — no video rendered.")
        return StoryWorkflowResult(
            resolved_audio_path=resolved_audio_path,
            audio_meta=audio_meta,
            video_clips=video_clips,
            montage_clips=montage_clips,
            broll_clips=broll_clips,
            pacing=pacing,
            segments=segments,
            plan_report=plan_report,
        )

    with _observer_scope(render_observer_factory) as observer:
        rendered_output_path = engine.generate_story(
            audio_meta,
            montage_clips,
            output_path,
            broll_clips=broll_clips,
            audio_path=resolved_audio_path,
            observer=observer,
            pacing=pacing,
        )

    logger.info("Process complete. Output saved to: %s", rendered_output_path)
    return StoryWorkflowResult(
        resolved_audio_path=resolved_audio_path,
        audio_meta=audio_meta,
        video_clips=video_clips,
        montage_clips=montage_clips,
        broll_clips=broll_clips,
        pacing=pacing,
        output_path=rendered_output_path,
    )
