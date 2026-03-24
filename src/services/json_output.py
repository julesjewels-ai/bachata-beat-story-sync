"""
Structured JSON output for Bachata Beat-Story Sync (FEAT-028).

Assembles pipeline data (audio analysis, clips, segment plan, config)
into a JSON-serialisable dict and writes it to stdout or a file.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from typing import Any

from src.core.models import (
    AudioAnalysisResult,
    PacingConfig,
    SegmentPlan,
    VideoAnalysisResult,
)

VERSION = "0.1.0"


def _serialise_audio(audio: AudioAnalysisResult) -> dict[str, Any]:
    """Dump audio analysis, excluding bulky ``peaks`` list."""
    data = audio.model_dump()
    data.pop("peaks", None)
    return data


def _serialise_clip(clip: VideoAnalysisResult) -> dict[str, Any]:
    """Dump clip analysis, excluding binary ``thumbnail_data``."""
    data = clip.model_dump()
    data.pop("thumbnail_data", None)
    return data


def _serialise_pacing(pacing: PacingConfig) -> dict[str, Any]:
    """Dump pacing config, keeping only non-default values."""
    defaults = PacingConfig()
    current = pacing.model_dump()
    return {
        key: val
        for key, val in current.items()
        if val != getattr(defaults, key)
    }


def build_json_output(
    audio_meta: AudioAnalysisResult,
    clips: list[VideoAnalysisResult],
    segments: list[SegmentPlan] | None,
    pacing: PacingConfig,
    output_path: str | None = None,
    version: str = VERSION,
) -> dict[str, Any]:
    """Assemble all pipeline data into a JSON-serialisable dict.

    Args:
        audio_meta: Analyzed audio features.
        clips: Analyzed video clips with intensity scores.
        segments: Planned segment list, or ``None`` if unavailable.
        pacing: Pacing configuration used for the run.
        output_path: Path to the rendered output file (if any).
        version: Version string for schema stability.

    Returns:
        Dict ready for ``json.dumps()``.
    """
    result: dict[str, Any] = {
        "version": version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "audio": _serialise_audio(audio_meta),
        "clips": [_serialise_clip(c) for c in clips],
        "segment_plan": (
            [s.model_dump() for s in segments] if segments is not None else None
        ),
        "config": _serialise_pacing(pacing),
    }
    if output_path is not None:
        result["output_path"] = output_path
    return result


def write_json_output(data: dict[str, Any], target: str | None) -> None:
    """Write JSON to a file path or stdout.

    Args:
        data: Dict to serialise.
        target: ``'-'`` for stdout, a file path, or ``None`` (no-op).
    """
    if target is None:
        return

    payload = json.dumps(data, indent=2, default=str) + "\n"

    if target == "-":
        sys.stdout.write(payload)
    else:
        os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
        with open(target, "w") as fh:
            fh.write(payload)
