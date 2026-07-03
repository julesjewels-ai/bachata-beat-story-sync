"""Unit tests for SRT subtitle utilities."""

import json
import os

from src.core.models import TranscriptResult, TranscriptSegment
from src.core.srt_utils import (
    _seconds_to_srt_time,
    segments_to_srt,
    transcript_stem,
    write_srt,
    write_transcript_json,
)


def _seg(start: float, end: float, text: str) -> TranscriptSegment:
    return TranscriptSegment(start=start, end=end, text=text)


# ------------------------------------------------------------------
# Timestamp formatting
# ------------------------------------------------------------------


def test_seconds_to_srt_time_zero():
    assert _seconds_to_srt_time(0.0) == "00:00:00,000"


def test_seconds_to_srt_time_milliseconds():
    assert _seconds_to_srt_time(1.234) == "00:00:01,234"


def test_seconds_to_srt_time_hours_minutes():
    # 1h 2m 3.5s
    assert _seconds_to_srt_time(3723.5) == "01:02:03,500"


def test_seconds_to_srt_time_rounds_to_nearest_ms():
    assert _seconds_to_srt_time(0.0006) == "00:00:00,001"
    assert _seconds_to_srt_time(0.00049) == "00:00:00,000"


# ------------------------------------------------------------------
# SRT block rendering
# ------------------------------------------------------------------


def test_segments_to_srt_numbers_from_one():
    srt = segments_to_srt([_seg(0.0, 1.0, "hola"), _seg(1.0, 2.0, "mundo")])
    blocks = srt.split("\n\n")
    assert len(blocks) == 2
    assert blocks[0].startswith("1\n")
    assert blocks[1].startswith("2\n")


def test_segments_to_srt_arrow_format_and_text():
    srt = segments_to_srt([_seg(0.5, 2.25, "  bailar  ")])
    assert "00:00:00,500 --> 00:00:02,250" in srt
    # text is stripped
    assert srt.endswith("bailar")


def test_segments_to_srt_empty():
    assert segments_to_srt([]) == ""


# ------------------------------------------------------------------
# File writers
# ------------------------------------------------------------------


def test_write_srt_returns_path_and_writes_content(tmp_path):
    out = os.path.join(str(tmp_path), "out.srt")
    returned = write_srt([_seg(0.0, 1.0, "uno")], out)
    assert returned == out
    with open(out, encoding="utf-8") as f:
        assert "00:00:00,000 --> 00:00:01,000" in f.read()


def test_write_transcript_json_roundtrip(tmp_path):
    result = TranscriptResult(
        audio_path="/videos/comp.mp4",
        language="es",
        segments=[_seg(0.0, 1.0, "corazón")],
    )
    out = os.path.join(str(tmp_path), "t.json")
    returned = write_transcript_json(result, out)
    assert returned == out
    with open(out, encoding="utf-8") as f:
        data = json.load(f)
    assert data["language"] == "es"
    assert data["audio_path"] == "/videos/comp.mp4"
    assert data["segments"][0]["text"] == "corazón"


# ------------------------------------------------------------------
# Stem helper
# ------------------------------------------------------------------


def test_transcript_stem_strips_extension():
    assert transcript_stem("/a/b/compilation.mp4") == "/a/b/compilation"


def test_transcript_stem_no_extension():
    assert transcript_stem("/a/b/compilation") == "/a/b/compilation"
