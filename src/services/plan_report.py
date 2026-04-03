"""
Dry-Run Plan Report Formatter — FEAT-026.

Produces a human-readable text report from a segment plan,
suitable for stdout or file output.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.models import (
        AudioAnalysisResult,
        PacingConfig,
        SegmentPlan,
        VideoAnalysisResult,
    )


def _fmt_time(seconds: float) -> str:
    """Format seconds as MM:SS.f (e.g. 03:42.5)."""
    mins = int(seconds) // 60
    secs = seconds - mins * 60
    return f"{mins:02d}:{secs:04.1f}"


def _segment_tag(segment: SegmentPlan) -> str:
    """Build the bracketed tag for a segment row."""
    # Forced prefix clips have section_label None and appear first
    if segment.section_label is None and segment.timeline_position == 0.0:
        return "[forced]"
    if "broll" in segment.video_path.lower():
        return "[b-roll]"
    level = segment.intensity_level
    return f"[{level}]"


def format_plan_report(
    audio: AudioAnalysisResult,
    segments: list[SegmentPlan],
    clips: list[VideoAnalysisResult],
    pacing: PacingConfig,
) -> str:
    """Format a human-readable dry-run report.

    Args:
        audio: Analyzed audio features.
        segments: The planned segment list from ``build_segment_plan()``.
        clips: All scanned video clips (used to compute skip stats).
        pacing: Active pacing configuration.

    Returns:
        A multi-line string ready for printing or writing to a file.
    """
    lines: list[str] = []

    # Header
    lines.append("DRY RUN — No video will be rendered.")
    lines.append("")

    # Audio summary
    dur_str = _fmt_time(audio.duration)
    beat_count = len(audio.beat_times)
    lines.append(
        f"Audio: {audio.filename} ({audio.bpm:.0f} BPM, {dur_str}, {beat_count} beats)"
    )

    # Clip stats
    used_paths = {s.video_path for s in segments}
    usable = len(used_paths)
    total = len(clips)
    skipped = total - usable
    lines.append(f"Clips: {total} analyzed, {usable} used in plan, {skipped} unused")

    # Estimated output duration
    if segments:
        last = segments[-1]
        est_dur = last.timeline_position + last.duration
        lines.append(f"Estimated output: {_fmt_time(est_dur)}")
    else:
        lines.append("Estimated output: 0:00.0 (empty plan)")

    lines.append("")

    # Segment table
    lines.append(f"Segment Plan ({len(segments)} segments):")
    if not segments:
        lines.append("  (no segments — check audio beats and clip availability)")
    for i, seg in enumerate(segments, start=1):
        end_time = seg.timeline_position + seg.duration
        basename = os.path.basename(seg.video_path)
        tag = _segment_tag(seg)
        lines.append(
            f"  #{i:03d}  {_fmt_time(seg.timeline_position)} → "
            f"{_fmt_time(end_time)}  {basename:<25s} {tag:<12s} "
            f"{seg.speed_factor:.1f}x  {seg.duration:.1f}s"
        )

    lines.append("")

    # Config summary
    config_items = [
        f"snap_to_beats={pacing.snap_to_beats}",
        f"broll_interval={pacing.broll_interval_seconds}s",
        f"video_style={pacing.video_style}",
    ]
    if pacing.max_clips is not None:
        config_items.append(f"max_clips={pacing.max_clips}")
    if pacing.max_duration_seconds is not None:
        config_items.append(f"max_duration={pacing.max_duration_seconds}s")
    if pacing.is_shorts:
        config_items.append("mode=shorts")
    lines.append(f"Config: {', '.join(config_items)}")

    lines.append("")
    lines.append("Run without --dry-run to render.")

    return "\n".join(lines)


def write_plan_report(
    report: str,
    output_path: str | None = None,
) -> None:
    """Print the report to stdout, or write to a file.

    Args:
        report: The formatted report string.
        output_path: If provided, write to this file instead of stdout.
    """
    if output_path:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w") as fh:
            fh.write(report + "\n")
    else:
        print(report)  # noqa: T201
