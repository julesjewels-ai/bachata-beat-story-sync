"""Text overlay pipeline (FEAT-045).

Builds FFmpeg drawtext filter chains for timed text events.
Supports Spanish UTF-8 characters (á é í ó ú ñ ü ¿ ¡) via Noto Sans.

Three visual styles — no raw settings exposed:
  wash        — large, ~10% opacity, centered behind video (cinematic wash)
  lower_third — small, clean, bottom-left with dark backdrop (lyrics/story)

Usage:
    events = build_text_events(config, audio_path="track.wav")
    font   = resolve_font(config.text_overlay_font)
    chain  = build_drawtext_filter_chain(events, font)
    # chain is a -vf argument string for FFmpeg
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from src.core.models import PacingConfig

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Font resolution
# ---------------------------------------------------------------------------

_ASSETS_FONTS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "assets", "fonts")
)

_FONT_SEARCH_DIRS = [
    _ASSETS_FONTS_DIR,
    # macOS
    "/Library/Fonts",
    "/System/Library/Fonts/Supplemental",
    "/System/Library/Fonts",
    # Linux
    "/usr/share/fonts/truetype/noto",
    "/usr/share/fonts/truetype/liberation",
    "/usr/share/fonts/truetype",
    "/usr/share/fonts",
]

# Ordered candidate filenames per logical font name
_FONT_FILES: dict[str, list[str]] = {
    "NotoSans-Bold": [
        "NotoSans-Bold.ttf",
        "NotoSans_Condensed-Bold.ttf",
        "NotoSans[wdth,wght].ttf",
    ],
    "NotoSans-Regular": [
        "NotoSans-Regular.ttf",
        "NotoSans_Condensed-Regular.ttf",
    ],
    # Fallbacks — available on stock macOS, cover Latin Extended
    "Arial-Bold": ["Arial Bold.ttf", "Arial.ttf"],
    "Arial": ["Arial.ttf"],
    "Helvetica": ["Helvetica.ttc", "HelveticaNeue.ttc"],
}

_FALLBACK_CHAIN = ["Arial-Bold", "Arial", "Helvetica"]


def resolve_font(font_name: str = "NotoSans-Bold") -> str:
    """Return an absolute path to a usable font file.

    Searches bundled assets/fonts/ first, then system directories.
    Falls back through Arial → Helvetica if the requested font is absent.

    Returns an empty string if nothing is found (FFmpeg will use its
    built-in bitmap font, which lacks extended Spanish characters).
    """
    candidates = list(_FONT_FILES.get(font_name, [f"{font_name}.ttf"]))
    for fb in _FALLBACK_CHAIN:
        if fb != font_name:
            candidates.extend(_FONT_FILES.get(fb, []))

    for directory in _FONT_SEARCH_DIRS:
        if not os.path.isdir(directory):
            continue
        for filename in candidates:
            path = os.path.join(directory, filename)
            if os.path.isfile(path):
                logger.debug("Font resolved: %s → %s", font_name, path)
                return path

    logger.warning(
        "No font file found for '%s'. "
        "Download Noto Sans to assets/fonts/ for Spanish character support. "
        "Falling back to FFmpeg built-in font.",
        font_name,
    )
    return ""


# ---------------------------------------------------------------------------
# Text event model
# ---------------------------------------------------------------------------


@dataclass
class TextEvent:
    """A single timed text event to be burned into the video."""

    text: str
    start: float  # seconds from video start
    end: float  # seconds from video start
    style: Literal["wash", "lower_third"]
    # Style overrides for wash events — ignored for lower_third
    wash_font_scale: float = 0.06   # font size as fraction of video width
    wash_opacity: float = 0.35      # 0.0–1.0
    wash_fade: float = 0.8          # max fade in/out seconds


# ---------------------------------------------------------------------------
# FFmpeg drawtext helpers
# ---------------------------------------------------------------------------


def escape_drawtext(text: str) -> str:
    """Escape text for safe use in an FFmpeg drawtext filter value.

    FFmpeg drawtext uses : as a separator and ' as a string delimiter.
    Backslashes must be doubled. UTF-8 characters (Spanish accents, ñ, ¿, ¡)
    pass through unchanged — FFmpeg handles them natively when a suitable
    font is provided.
    """
    text = text.replace("\\", "\\\\")
    text = text.replace("'", "\\'")
    text = text.replace(":", "\\:")
    return text


def _wrap_text(text: str, max_chars: int = 45) -> str:
    """Wrap text at a word boundary if longer than *max_chars*.

    Returns a string with lines joined by ``\\n`` (the FFmpeg newline escape).
    """
    if len(text) <= max_chars:
        return text
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        if current and len(current) + 1 + len(word) > max_chars:
            lines.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        lines.append(current)
    return "\\n".join(lines)


def _alpha_expr(t_start: float, t_end: float, fade: float) -> str:
    """FFmpeg alpha expression: fade in, hold, fade out."""
    return (
        f"if(lt(t-{t_start:.3f},{fade:.3f}),"
        f"(t-{t_start:.3f})/{fade:.3f},"
        f"if(gt(t,{t_end - fade:.3f}),"
        f"({t_end:.3f}-t)/{fade:.3f},1))"
    )


def _drawtext_filter(
    event: TextEvent,
    font_path: str,
    video_w: int,
) -> str:
    """Build a single ``drawtext`` filter string for one TextEvent."""
    enable = f"between(t,{event.start:.3f},{event.end:.3f})"
    font_arg = f"fontfile={font_path}:" if font_path else ""

    if event.style == "wash":
        # Moderate size, centered — text "washes" over the video.
        # Wrap at 32 chars so lines stay within padded screen edges.
        # Fade duration and opacity come from event fields (set by config).
        fade = min(event.wash_fade, (event.end - event.start) / 3)
        alpha = _alpha_expr(event.start, event.end, fade)
        escaped = escape_drawtext(_wrap_text(event.text, max_chars=32))
        fontsize = min(int(video_w * event.wash_font_scale), 90)
        pad = max(60, int(video_w * 0.04))
        return (
            f"drawtext={font_arg}"
            f"text='{escaped}':"
            f"fontsize={fontsize}:"
            f"fontcolor=white@{event.wash_opacity:.2f}:"
            f"x=max({pad}\\,(W-tw)/2):y=(H-th)/2:"
            f"alpha='{alpha}':"
            f"enable='{enable}'"
        )
    else:
        # lower_third: clean subtitle-style with a dark semi-transparent backdrop
        fade = min(0.3, (event.end - event.start) / 4)
        alpha = _alpha_expr(event.start, event.end, fade)
        escaped = escape_drawtext(_wrap_text(event.text))
        fontsize = 48
        pad = 48
        return (
            f"drawtext={font_arg}"
            f"text='{escaped}':"
            f"fontsize={fontsize}:"
            f"fontcolor=white:"
            f"x={pad}:y=h-{fontsize + pad + 12}:"
            f"box=1:boxcolor=black@0.40:boxborderw=12:"
            f"alpha='{alpha}':"
            f"enable='{enable}'"
        )


def build_drawtext_filter_chain(
    events: list[TextEvent],
    font_path: str,
    video_w: int = 1920,
) -> str:
    """Return a complete FFmpeg ``-vf`` filter string for all text events.

    Multiple drawtext filters are comma-chained. Returns an empty string
    when *events* is empty (caller should skip the FFmpeg pass entirely).
    """
    if not events:
        return ""
    return ",".join(
        _drawtext_filter(e, font_path, video_w) for e in events
    )


# ---------------------------------------------------------------------------
# LRC parser (FEAT-047 foundation)
# ---------------------------------------------------------------------------

_LRC_RE = re.compile(r"\[(\d{2}):(\d{2})\.(\d{2,3})\](.*)")


def parse_lrc(lrc_path: str) -> list[tuple[float, str]]:
    """Parse an LRC file into ``(timestamp_seconds, lyric_text)`` pairs.

    Empty lyric lines (silence markers) are included as ``(ts, "")`` —
    callers can use them to determine when the previous line ends.
    Lines that don't match the LRC timestamp format are ignored.
    """
    entries: list[tuple[float, str]] = []
    try:
        with open(lrc_path, encoding="utf-8") as fh:
            for line in fh:
                m = _LRC_RE.match(line.strip())
                if not m:
                    continue
                mins = int(m.group(1))
                secs = int(m.group(2))
                frac_str = m.group(3)
                frac = int(frac_str) / (100 if len(frac_str) == 2 else 1000)
                ts = mins * 60 + secs + frac
                entries.append((ts, m.group(4).strip()))
    except OSError:
        logger.warning("Could not read LRC file: %s", lrc_path)
    return sorted(entries, key=lambda x: x[0])


def lrc_to_text_events(
    entries: list[tuple[float, str]],
    cold_open_end: float = 7.0,
) -> list[TextEvent]:
    """Convert parsed LRC entries to :class:`TextEvent` objects.

    Rules:
    - Each lyric line shows from its timestamp until just before the next.
    - The last lyric shows for up to 4 extra seconds.
    - Lines that start during the cold-open window (0–*cold_open_end*) are
      skipped to avoid collision with FEAT-046 opening text.
    - Lines shorter than 0.8s display time are dropped.
    - Empty-text entries are not displayed but are used for timing only.
    """
    # Filter to lines that have actual text (for display), keep all for timing
    all_ts = [(ts, txt) for ts, txt in entries]
    visible = [(ts, txt) for ts, txt in entries if txt]

    events: list[TextEvent] = []
    for i, (ts, text) in enumerate(visible):
        if ts < cold_open_end:
            continue

        # Determine end time
        # Find the next timestamp in the full list (including empty markers)
        next_ts: float | None = None
        for future_ts, _ in all_ts:
            if future_ts > ts:
                next_ts = future_ts
                break
        end = (next_ts - 0.1) if next_ts is not None else ts + 4.0

        if end - ts < 0.8:
            continue

        events.append(TextEvent(text=text, start=ts, end=end, style="lower_third"))

    return events


# ---------------------------------------------------------------------------
# Event builder — aggregates all text sources
# ---------------------------------------------------------------------------


def _most_repeated_lrc_line(lrc_path: str) -> str:
    """Return the most-repeated non-empty lyric line from an LRC file.

    Ties are broken by first occurrence. Returns an empty string when the file
    has no repeated lines or cannot be read.
    """
    entries = parse_lrc(lrc_path)
    counts: dict[str, int] = {}
    first_seen: dict[str, int] = {}
    for i, (_, text) in enumerate(entries):
        text = text.strip()
        if not text:
            continue
        counts[text] = counts.get(text, 0) + 1
        if text not in first_seen:
            first_seen[text] = i

    if not counts:
        return ""

    max_count = max(counts.values())
    if max_count < 2:
        # No repeated lines — nothing meaningful to surface as a scene-setter
        return ""

    # Pick the earliest-occurring line among those with the highest count
    best = min(
        (t for t, c in counts.items() if c == max_count),
        key=lambda t: first_seen[t],
    )
    logger.debug("Cold open LRC fallback: '%s' (×%d)", best, max_count)
    return best


def build_cold_open_events(
    config: "PacingConfig",
    audio_path: str | None = None,
) -> list[TextEvent]:
    """Build TextEvents for the cinematic cold open (FEAT-046).

    Sequence:
    - 0.0–4.0s: scene-setter ``wash`` text.  Sources in priority order:
        1. ``{stem}.scene.txt`` sidecar — creator-authored emotional line.
        2. Most-repeated lyric from ``{stem}.lrc`` — chorus hook fallback.
        3. Nothing — cold open wash is skipped silently.
    - 4.0–7.0s: artist/song ``lower_third``.  Source: ``config.track_artist``
      and ``config.track_title``.

    Any of the two segments is skipped when its source data is absent.
    """
    events: list[TextEvent] = []

    # 1. Scene-setter wash (0–4s) — priority: .scene.txt → LRC fallback
    scene_text = ""
    if audio_path:
        stem = os.path.splitext(audio_path)[0]

        # Priority 1: sidecar .scene.txt
        scene_path = stem + ".scene.txt"
        if os.path.isfile(scene_path):
            try:
                with open(scene_path, encoding="utf-8") as fh:
                    scene_text = fh.read().strip().splitlines()[0].strip()
                logger.debug("Cold open scene text loaded: %s", scene_path)
            except OSError:
                logger.warning("Could not read scene file: %s", scene_path)

        # Priority 2: most-repeated lyric from .lrc (chorus hook)
        if not scene_text:
            lrc_path = stem + ".lrc"
            if os.path.isfile(lrc_path):
                scene_text = _most_repeated_lrc_line(lrc_path)
                if scene_text:
                    logger.info(
                        "Cold open: using LRC chorus hook as scene-setter: '%s'",
                        scene_text,
                    )

    if scene_text:
        events.append(
            TextEvent(
                text=scene_text,
                start=0.0,
                end=4.0,
                style="wash",
                wash_font_scale=config.cold_open_wash_font_scale,
                wash_opacity=config.cold_open_wash_opacity,
                wash_fade=config.cold_open_wash_fade,
            )
        )

    # 2. Artist / song lower-third (4–7s)
    artist = (config.track_artist or "").strip()
    title = (config.track_title or "").strip()
    if artist or title:
        label = f"{artist} — {title}" if (artist and title) else (artist or title)
        events.append(TextEvent(text=label, start=4.0, end=7.0, style="lower_third"))

    return events


# How long the cold open occupies (lyrics must not start before this)
_COLD_OPEN_END = 7.0


def build_text_events(
    config: "PacingConfig",
    audio_path: str | None = None,
) -> list[TextEvent]:
    """Collect all TextEvents from configured sources.

    Handles:
    - Cinematic cold open (FEAT-046): scene-setter wash + artist/song lower-third
    - LRC lyrics (FEAT-047): from ``config.lyrics_lrc_path`` or auto-discovered
      alongside *audio_path* as ``{stem}.lrc``

    Events are returned in chronological order.
    """
    events: list[TextEvent] = []

    # Cold open — independent of lyrics_overlay_enabled
    cold_open_end = 0.0
    if config.cold_open_enabled:
        cold_open_events = build_cold_open_events(config, audio_path)
        if cold_open_events:
            events.extend(cold_open_events)
            cold_open_end = _COLD_OPEN_END

    # LRC lyrics
    if config.lyrics_overlay_enabled:
        lrc_path = config.lyrics_lrc_path or ""
        if not lrc_path and audio_path:
            candidate = os.path.splitext(audio_path)[0] + ".lrc"
            if os.path.isfile(candidate):
                lrc_path = candidate
                logger.debug("Auto-discovered LRC: %s", lrc_path)

        if lrc_path:
            entries = parse_lrc(lrc_path)
            lrc_events = lrc_to_text_events(entries, cold_open_end=cold_open_end)
            logger.info(
                "LRC overlay: %d lyric lines loaded from %s", len(lrc_events), lrc_path
            )
            events.extend(lrc_events)

    events.sort(key=lambda e: e.start)
    return events
