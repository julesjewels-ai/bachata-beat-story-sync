"""Unit tests for src/core/text_overlay.py (FEAT-045, FEAT-046)."""

from __future__ import annotations

import os
import tempfile

import pytest

from src.core.text_overlay import (
    TextEvent,
    _most_repeated_lrc_line,
    _wrap_text,
    build_cold_open_events,
    build_drawtext_filter_chain,
    escape_drawtext,
    lrc_to_text_events,
    parse_lrc,
)


# ---------------------------------------------------------------------------
# escape_drawtext
# ---------------------------------------------------------------------------


def test_escape_plain_text():
    assert escape_drawtext("hello world") == "hello world"


def test_escape_single_quote():
    assert escape_drawtext("it's fine") == "it\\'s fine"


def test_escape_colon():
    assert escape_drawtext("10:00") == "10\\:00"


def test_escape_backslash():
    assert escape_drawtext("a\\b") == "a\\\\b"


def test_escape_spanish_characters_pass_through():
    text = "á é í ó ú ñ ü ¿ ¡"
    assert escape_drawtext(text) == text


# ---------------------------------------------------------------------------
# _wrap_text
# ---------------------------------------------------------------------------


def test_wrap_short_text_unchanged():
    assert _wrap_text("Short line") == "Short line"


def test_wrap_long_text_at_word_boundary():
    text = "Te vi bailar esa noche y algo en mi cambio para siempre"
    result = _wrap_text(text, max_chars=30)
    assert "\\n" in result
    for part in result.split("\\n"):
        assert len(part) <= 30


def test_wrap_exactly_at_limit_unchanged():
    text = "a" * 45
    assert _wrap_text(text, max_chars=45) == text


# ---------------------------------------------------------------------------
# build_drawtext_filter_chain
# ---------------------------------------------------------------------------


def test_empty_events_returns_empty_string():
    assert build_drawtext_filter_chain([], font_path="") == ""


def test_single_wash_event_produces_drawtext():
    events = [TextEvent(text="Una noche", start=0.0, end=4.0, style="wash")]
    result = build_drawtext_filter_chain(events, font_path="", video_w=1920)
    assert result.startswith("drawtext=")
    assert "Una noche" in result
    assert "white@0.35" in result


def test_single_lower_third_produces_drawtext():
    events = [TextEvent(text="Te vi bailar", start=7.0, end=10.0, style="lower_third")]
    result = build_drawtext_filter_chain(events, font_path="", video_w=1920)
    assert "Te vi bailar" in result
    assert "box=1" in result


def test_multiple_events_comma_separated():
    events = [
        TextEvent(text="Wash", start=0.0, end=4.0, style="wash"),
        TextEvent(text="Lower", start=7.0, end=10.0, style="lower_third"),
    ]
    result = build_drawtext_filter_chain(events, font_path="")
    parts = result.split(",drawtext=")
    assert len(parts) == 2


def test_font_path_included_when_provided():
    events = [TextEvent(text="X", start=0.0, end=4.0, style="wash")]
    result = build_drawtext_filter_chain(events, font_path="/fonts/NotoSans.ttf")
    assert "fontfile=/fonts/NotoSans.ttf" in result


def test_no_font_arg_when_path_empty():
    events = [TextEvent(text="X", start=0.0, end=4.0, style="wash")]
    result = build_drawtext_filter_chain(events, font_path="")
    assert "fontfile" not in result


# ---------------------------------------------------------------------------
# parse_lrc
# ---------------------------------------------------------------------------


def _write_lrc(lines: list[str]) -> str:
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=".lrc", delete=False, encoding="utf-8"
    )
    f.write("\n".join(lines))
    f.close()
    return f.name


def test_parse_lrc_basic():
    path = _write_lrc(["[00:12.50]Te vi bailar", "[00:16.80]y algo en mí cambió"])
    try:
        entries = parse_lrc(path)
    finally:
        os.unlink(path)

    assert len(entries) == 2
    assert abs(entries[0][0] - 12.5) < 0.01
    assert entries[0][1] == "Te vi bailar"
    assert abs(entries[1][0] - 16.8) < 0.01


def test_parse_lrc_empty_line_included():
    path = _write_lrc(["[00:10.00]Línea uno", "[00:14.00]"])
    try:
        entries = parse_lrc(path)
    finally:
        os.unlink(path)

    assert len(entries) == 2
    assert entries[1][1] == ""


def test_parse_lrc_missing_file_returns_empty():
    assert parse_lrc("/nonexistent/file.lrc") == []


def test_parse_lrc_three_digit_milliseconds():
    path = _write_lrc(["[01:02.500]Hola"])
    try:
        entries = parse_lrc(path)
    finally:
        os.unlink(path)
    assert abs(entries[0][0] - 62.5) < 0.001


# ---------------------------------------------------------------------------
# lrc_to_text_events
# ---------------------------------------------------------------------------


def test_lrc_to_text_events_basic():
    entries = [(8.0, "Te vi bailar"), (12.0, "y algo cambió"), (16.0, "")]
    events = lrc_to_text_events(entries, cold_open_end=7.0)
    assert len(events) == 2
    assert events[0].text == "Te vi bailar"
    assert abs(events[0].start - 8.0) < 0.01
    assert abs(events[0].end - 11.9) < 0.1


def test_lrc_to_text_events_skips_cold_open_window():
    entries = [(3.0, "In cold open"), (8.0, "After cold open"), (12.0, "")]
    events = lrc_to_text_events(entries, cold_open_end=7.0)
    assert len(events) == 1
    assert events[0].text == "After cold open"


def test_lrc_to_text_events_last_line_gets_extra_time():
    entries = [(8.0, "Last line")]
    events = lrc_to_text_events(entries, cold_open_end=7.0)
    assert len(events) == 1
    assert abs(events[0].end - (8.0 + 4.0)) < 0.01


def test_lrc_to_text_events_drops_short_display_lines():
    # Lines with <0.8s display time are dropped
    entries = [(8.0, "Flash"), (8.5, "Next")]
    events = lrc_to_text_events(entries, cold_open_end=7.0)
    # "Flash" shows 8.0→8.4 = 0.4s (<0.8) → dropped; "Next" gets 4s
    assert all(e.text != "Flash" for e in events)


def test_lrc_to_text_events_style_is_lower_third():
    entries = [(8.0, "Una línea"), (12.0, "")]
    events = lrc_to_text_events(entries, cold_open_end=7.0)
    assert all(e.style == "lower_third" for e in events)


# ---------------------------------------------------------------------------
# _most_repeated_lrc_line
# ---------------------------------------------------------------------------


def test_most_repeated_lrc_line_finds_chorus():
    path = _write_lrc(
        [
            "[00:10.00]Verso uno",
            "[00:14.00]Te quiero",
            "[00:18.00]Verso dos",
            "[00:22.00]Te quiero",
            "[00:26.00]Verso tres",
            "[00:30.00]Te quiero",
        ]
    )
    try:
        result = _most_repeated_lrc_line(path)
    finally:
        os.unlink(path)
    assert result == "Te quiero"


def test_most_repeated_lrc_line_no_repeats_returns_empty():
    path = _write_lrc(["[00:10.00]Uno", "[00:14.00]Dos", "[00:18.00]Tres"])
    try:
        result = _most_repeated_lrc_line(path)
    finally:
        os.unlink(path)
    assert result == ""


def test_most_repeated_lrc_line_missing_file_returns_empty():
    assert _most_repeated_lrc_line("/nonexistent/file.lrc") == ""


def test_most_repeated_lrc_line_tie_broken_by_first_occurrence():
    path = _write_lrc(
        [
            "[00:10.00]Alpha",
            "[00:14.00]Beta",
            "[00:18.00]Alpha",
            "[00:22.00]Beta",
        ]
    )
    try:
        result = _most_repeated_lrc_line(path)
    finally:
        os.unlink(path)
    # Both appear twice; "Alpha" appears first
    assert result == "Alpha"


# ---------------------------------------------------------------------------
# build_cold_open_events
# ---------------------------------------------------------------------------


def _make_config(**kwargs):
    from src.core.models import PacingConfig

    return PacingConfig(
        cold_open_enabled=True,
        text_overlay_enabled=True,
        **kwargs,
    )


def test_cold_open_scene_txt_used_when_present():
    with tempfile.TemporaryDirectory() as d:
        audio = os.path.join(d, "track.wav")
        scene = os.path.join(d, "track.scene.txt")
        open(audio, "w").close()
        with open(scene, "w", encoding="utf-8") as f:
            f.write("Una noche en Santo Domingo.\n")

        config = _make_config()
        events = build_cold_open_events(config, audio_path=audio)

    wash = [e for e in events if e.style == "wash"]
    assert len(wash) == 1
    assert wash[0].text == "Una noche en Santo Domingo."
    assert wash[0].start == 0.0
    assert wash[0].end == 4.0


def test_cold_open_lrc_fallback_when_no_scene_txt():
    with tempfile.TemporaryDirectory() as d:
        audio = os.path.join(d, "track.wav")
        lrc = os.path.join(d, "track.lrc")
        open(audio, "w").close()
        with open(lrc, "w", encoding="utf-8") as f:
            f.write(
                "[00:10.00]Verso\n"
                "[00:14.00]Te quiero\n"
                "[00:20.00]Verso dos\n"
                "[00:24.00]Te quiero\n"
            )

        config = _make_config()
        events = build_cold_open_events(config, audio_path=audio)

    wash = [e for e in events if e.style == "wash"]
    assert len(wash) == 1
    assert wash[0].text == "Te quiero"


def test_cold_open_scene_txt_takes_priority_over_lrc():
    with tempfile.TemporaryDirectory() as d:
        audio = os.path.join(d, "track.wav")
        open(audio, "w").close()
        with open(os.path.join(d, "track.scene.txt"), "w", encoding="utf-8") as f:
            f.write("La noche que cambió todo.\n")
        with open(os.path.join(d, "track.lrc"), "w", encoding="utf-8") as f:
            f.write("[00:10.00]Te quiero\n[00:14.00]Te quiero\n")

        config = _make_config()
        events = build_cold_open_events(config, audio_path=audio)

    wash = [e for e in events if e.style == "wash"]
    assert wash[0].text == "La noche que cambió todo."


def test_cold_open_no_sources_no_wash():
    with tempfile.TemporaryDirectory() as d:
        audio = os.path.join(d, "track.wav")
        open(audio, "w").close()

        config = _make_config()
        events = build_cold_open_events(config, audio_path=audio)

    assert not any(e.style == "wash" for e in events)


def test_cold_open_artist_title_lower_third():
    config = _make_config(track_artist="Romeo Santos", track_title="Propuesta Indecente")
    events = build_cold_open_events(config)
    lower = [e for e in events if e.style == "lower_third"]
    assert len(lower) == 1
    assert "Romeo Santos" in lower[0].text
    assert "Propuesta Indecente" in lower[0].text
    assert lower[0].start == 4.0
    assert lower[0].end == 7.0


def test_cold_open_skipped_when_disabled():
    from src.core.models import PacingConfig

    config = PacingConfig(cold_open_enabled=False, text_overlay_enabled=True)
    # build_cold_open_events always runs; the gate is in build_text_events
    # Confirm direct call still works — just no wash
    events = build_cold_open_events(config)
    assert events == []
