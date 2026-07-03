"""SRT subtitle file utilities."""

from __future__ import annotations

import json
import os

from src.core.models import TranscriptResult, TranscriptSegment


def _seconds_to_srt_time(seconds: float) -> str:
    """Convert float seconds to SRT timestamp HH:MM:SS,mmm."""
    total_ms = int(round(seconds * 1000))
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1_000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def segments_to_srt(segments: list[TranscriptSegment]) -> str:
    """Render a list of TranscriptSegments as SRT text."""
    blocks: list[str] = []
    for idx, seg in enumerate(segments, start=1):
        start = _seconds_to_srt_time(seg.start)
        end = _seconds_to_srt_time(seg.end)
        text = seg.text.strip()
        blocks.append(f"{idx}\n{start} --> {end}\n{text}")
    return "\n\n".join(blocks)


def write_srt(segments: list[TranscriptSegment], output_path: str) -> str:
    """Write SRT file, return path."""
    content = segments_to_srt(segments)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    return output_path


def write_transcript_json(result: TranscriptResult, output_path: str) -> str:
    """Write full transcript as JSON, return path."""
    data = result.model_dump()
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return output_path


def transcript_stem(video_path: str) -> str:
    """Return base path (no extension) for sidecar output files."""
    base, _ = os.path.splitext(video_path)
    return base
