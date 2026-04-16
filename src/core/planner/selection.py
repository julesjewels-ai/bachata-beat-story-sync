"""Clip selection helpers for segment planning."""

from __future__ import annotations

import random
from collections.abc import Callable
from typing import NamedTuple

from src.core.models import VideoAnalysisResult
from src.core.pacing_views import PlanningConfig


class ClipSelection(NamedTuple):
    """Result of selecting the next clip during planning."""

    clip: VideoAnalysisResult
    forced_clip_idx: int
    broll_idx: int
    clip_idx: int
    last_broll_time: float
    target_broll_interval: float
    reason: str


def select_clip(
    *,
    forced_clips: list[VideoAnalysisResult],
    forced_clip_idx: int,
    is_broll: bool,
    broll_clips: list[VideoAnalysisResult] | None,
    broll_idx: int,
    timeline_pos: float,
    last_broll_time: float,
    config: PlanningConfig,
    pools: dict[str, list[VideoAnalysisResult]],
    pool_indices: dict[str, int],
    level: str,
    clip_idx: int,
    pick_from_pool: Callable[
        [dict[str, list[VideoAnalysisResult]], dict[str, int], str],
        VideoAnalysisResult,
    ],
) -> ClipSelection:
    """Pick the next clip and advance the relevant index."""
    target_broll_interval = config.broll_interval_seconds + random.uniform(
        -config.broll_interval_variance, config.broll_interval_variance
    )
    if forced_clip_idx < len(forced_clips):
        clip = forced_clips[forced_clip_idx]
        forced_clip_idx += 1
        reason = "Forced prefix ordering (FEAT-008)"
    elif is_broll:
        assert broll_clips is not None
        clip = broll_clips[broll_idx % len(broll_clips)]
        broll_idx += 1
        last_broll_time = timeline_pos
        reason = f"B-roll interval triggered ({target_broll_interval:.1f}s)"
    else:
        clip = pick_from_pool(pools, pool_indices, level)
        clip_idx += 1
        reason = f"Intensity matched: {level} pool (score={clip.intensity_score:.2f})"
    return ClipSelection(
        clip=clip,
        forced_clip_idx=forced_clip_idx,
        broll_idx=broll_idx,
        clip_idx=clip_idx,
        last_broll_time=last_broll_time,
        target_broll_interval=target_broll_interval,
        reason=reason,
    )
