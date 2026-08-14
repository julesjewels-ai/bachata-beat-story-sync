"""YouTube metadata generator for BBB pipeline.

Generates SEO-optimised title, description (with timecodes), hashtags,
backend tags (CSV), and thumbnail concepts — based on the channel's
v2.0 intention-based keyword strategy.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from typing import Any

# ---------------------------------------------------------------------------
# SEO Strategy constants (from SEO-Marketing-Strategy.md v2.0)
# ---------------------------------------------------------------------------

_PRIMARY_KEYWORDS = ["Música para Recordar", "Canciones de Amor"]

_SUPPORTING_KEYWORDS = ["bachata romántica", "música para bailar", "bachata para bailar"]

_HASHTAGS_TIER1 = [
    "#bachataromántica",
    "#músicaromántica",
    "#musicaparabailar",
    "#cancionesdeamor",
]

_HASHTAGS_TIER2 = [
    "#pararecordar",
    "#parabailar",
    "#musicalatina",
    "#nostalgic",
    "#recordar",
]

_HASHTAGS_TIER3 = [
    "#cantosdelcorazón",
    "#danza",
    "#romance",
    "#corazón",
]

# Mix title templates (utility language wins — see title-patterns.md Mixes section)
_MIX_TITLE_TEMPLATES = [
    "{primary} — El Mejor Mix de Bachata Romántica 🌹",
    "Bachata Romántica para {utility}: Mix de {primary}",
    "Música para Bailar — {primary} en Bachata | Mix Romántico 💃🏻",
    "{primary} ✨ Bachata Romántica | Selección de Oro",
    "El Mejor Mix de {primary} — Bachata Vieja y Romántica",
]

# Compilation title templates (has track listing → emphasise variety)
_COMPILATION_TITLE_TEMPLATES = [
    "{primary} — Compilación de Bachata Romántica 🌹",
    "Bachata Romántica: {primary} | Compilación Completa 💃🏻",
    "Las Mejores Canciones de Amor en Bachata — {primary}",
]

# Single-song title templates (concrete image + nostalgia anchor)
_SONG_TITLE_TEMPLATES = [
    "{title} — {primary} en Bachata Romántica 🌹",
    "{title} | {primary} — Bachata para Bailar y Recordar",
    "Bachata Romántica: {title} — {primary} 💃🏻",
]

_BACKEND_BASE_TAGS = [
    "bachata",
    "bachata romántica",
    "música para recordar",
    "canciones de amor",
    "música para bailar",
    "bachata para bailar",
    "bachata vieja",
    "música latina",
    "música romántica",
    "bachata mix",
    "recuerdos",
    "nostalgia",
    "amor",
    "corazón",
    "baile",
    "dance",
    "latin music",
    "romantic music",
    "music to remember",
    "love songs",
]

_THUMBNAIL_CONCEPTS = [
    "Couple dancing bachata silhouette against golden sunset — warm amber tones",
    "Close-up of intertwined hands with soft bokeh — deep red/rose palette",
    "Female dancer mid-spin, flowing dress — contrast with dark bg, gold accent text",
    "Vintage film-grain look: couple on dance floor — faded warm tones with title overlay",
    "Two people facing each other close — cinematic crop, coral/terracotta colour grade",
]


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class TrackSegment:
    """Single track entry with its position in the mix/compilation."""

    artist: str
    title: str
    start_time: float  # seconds into the video


@dataclass
class YouTubeMetadata:
    """All YouTube-publishable metadata for a video."""

    title: str
    description: str
    hashtags: list[str]
    tags_csv: str
    thumbnail_concepts: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "hashtags": self.hashtags,
            "tags_csv": self.tags_csv,
            "thumbnail_concepts": self.thumbnail_concepts,
        }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _timecode(seconds: float) -> str:
    """Convert seconds to MM:SS or HH:MM:SS."""
    total = int(seconds)
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def _pick(templates: list[str], seed: str) -> str:
    """Deterministic template pick based on seed string (avoids templated-feel)."""
    idx = int(hashlib.md5(seed.encode()).hexdigest(), 16) % len(templates)
    return templates[idx]


def _primary_keyword(seed: str) -> str:
    idx = int(hashlib.md5(seed.encode()).hexdigest(), 16) % 2
    return _PRIMARY_KEYWORDS[idx]


def _hashtag_selection(content_type: str, artist_names: list[str]) -> list[str]:
    """Build 10–12 hashtag list: Tier 1 always + rotating Tier 2/3."""
    tags = list(_HASHTAGS_TIER1)

    # Tier 2: always add pararecordar + parabailar for mixes/compilations
    if content_type in ("mix", "compilation"):
        tags += ["#pararecordar", "#parabailar", "#musicalatina"]
    else:
        tags += ["#pararecordar", "#musicalatina"]

    # Tier 3: 2 context-specific
    tags += ["#romance", "#corazón"]

    # Artist hashtags (clean: lowercase, no spaces, no special chars)
    for name in artist_names[:2]:
        clean = "#" + "".join(c for c in name.lower() if c.isalnum())
        if clean not in tags and len(clean) > 2:
            tags.append(clean)

    return tags[:15]  # YouTube cap


def _build_backend_tags(
    primary: str, track_segments: list[TrackSegment]
) -> str:
    """Comma-separated backend tags including artist names."""
    primary_lower = primary.lower()
    # Primary keyword goes first; drop any base-tag duplicate so it isn't listed twice
    # (e.g. "canciones de amor" is both a primary keyword and a base tag).
    tags = [t for t in _BACKEND_BASE_TAGS if t != primary_lower]
    tags.insert(0, primary_lower)

    for seg in track_segments:
        if seg.artist and seg.artist.lower() not in tags:
            tags.append(seg.artist.lower())
        if seg.title and seg.title.lower() not in tags:
            tags.append(seg.title.lower())

    return ", ".join(tags)


def _build_timecode_block(track_segments: list[TrackSegment]) -> str:
    if not track_segments:
        return ""
    lines = ["🎵 TRACKLIST:", ""]
    for seg in track_segments:
        tc = _timecode(seg.start_time)
        if seg.artist:
            lines.append(f"{tc} {seg.title} — {seg.artist}")
        else:
            lines.append(f"{tc} {seg.title}")
    return "\n".join(lines)


def _build_description(
    content_type: str,
    primary: str,
    track_segments: list[TrackSegment],
    total_duration_s: float,
) -> str:
    duration_str = _timecode(total_duration_s) if total_duration_s > 0 else ""
    timecode_block = _build_timecode_block(track_segments)

    if content_type == "mix":
        hook = (
            "Déjate llevar por la mejor bachata romántica — "
            "una mezcla perfecta de canciones de amor para recordar "
            "los momentos más especiales de tu vida. 🌹"
        )
    elif content_type == "compilation":
        hook = (
            "Una compilación completa de bachata romántica — "
            "canciones de amor seleccionadas para recordar y bailar "
            "con el corazón abierto. 💃🏻"
        )
    else:
        hook = (
            "Bachata romántica para recordar — "
            "una canción de amor que llega directo al corazón. 🌹"
        )

    parts = [hook, ""]

    if duration_str:
        parts += [f"⏱ Duración: {duration_str}", ""]

    if timecode_block:
        parts += [timecode_block, ""]

    parts += [
        "—",
        "🔔 Suscríbete para más bachata romántica, canciones de amor y música para recordar.",
        "",
        "🔎 Palabras clave: música para recordar, canciones de amor, bachata romántica, "
        "música para bailar, bachata para bailar, bachata vieja, música latina romántica, "
        "recuerdos, nostalgia, amor eterno",
    ]

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_metadata(
    content_type: str,
    track_segments: list[TrackSegment],
    total_duration_s: float = 0.0,
    artist: str = "",
    title: str = "",
) -> YouTubeMetadata:
    """Generate full YouTube metadata for a video.

    Args:
        content_type: "mix" | "compilation" | "song"
        track_segments: Ordered list of tracks with start times (for timecodes).
        total_duration_s: Total video duration in seconds.
        artist: Single artist name (used for "song" type).
        title: Single song title (used for "song" type).
    """
    seed = title or (track_segments[0].title if track_segments else "bachata")
    primary = _primary_keyword(seed)
    utility = "Bailar y Recordar"

    if content_type == "mix":
        tmpl = _pick(_MIX_TITLE_TEMPLATES, seed)
        yt_title = tmpl.format(primary=primary, utility=utility)
    elif content_type == "compilation":
        tmpl = _pick(_COMPILATION_TITLE_TEMPLATES, seed)
        yt_title = tmpl.format(primary=primary)
    else:
        tmpl = _pick(_SONG_TITLE_TEMPLATES, seed)
        yt_title = tmpl.format(primary=primary, title=title or "Bachata Romántica")

    artist_names = [seg.artist for seg in track_segments if seg.artist]
    if artist:
        artist_names.insert(0, artist)

    description = _build_description(
        content_type, primary, track_segments, total_duration_s
    )
    hashtags = _hashtag_selection(content_type, artist_names)
    tags_csv = _build_backend_tags(primary, track_segments)
    thumbnail_concepts = _THUMBNAIL_CONCEPTS[:3]

    return YouTubeMetadata(
        title=yt_title,
        description=description,
        hashtags=hashtags,
        tags_csv=tags_csv,
        thumbnail_concepts=thumbnail_concepts,
    )


def generate_and_write(
    content_type: str,
    track_segments: list[TrackSegment],
    total_duration_s: float,
    output_dir: str,
    artist: str = "",
    title: str = "",
) -> list[str]:
    """Generate YouTube metadata and write it to *output_dir*.

    Convenience wrapper combining :func:`generate_metadata` and
    :func:`write_youtube_metadata` so callers (pipeline phase + Streamlit
    runner) share one code path. Returns written file paths.
    """
    metadata = generate_metadata(
        content_type=content_type,
        track_segments=track_segments,
        total_duration_s=total_duration_s,
        artist=artist,
        title=title,
    )
    return write_youtube_metadata(metadata, output_dir)


def write_youtube_metadata(
    metadata: YouTubeMetadata,
    output_dir: str,
    stem: str = "youtube_metadata",
) -> list[str]:
    """Write metadata as .json and human-readable .txt. Returns written paths."""
    os.makedirs(output_dir, exist_ok=True)
    json_path = os.path.join(output_dir, f"{stem}.json")
    txt_path = os.path.join(output_dir, f"{stem}.txt")

    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(metadata.to_dict(), fh, indent=2, ensure_ascii=False)

    lines = [
        "=== YOUTUBE METADATA ===",
        "",
        f"TITLE:\n{metadata.title}",
        "",
        f"DESCRIPTION:\n{metadata.description}",
        "",
        "HASHTAGS (paste into description end or first comment):",
        " ".join(metadata.hashtags),
        "",
        "BACKEND TAGS (comma-separated):",
        metadata.tags_csv,
        "",
        "THUMBNAIL CONCEPTS:",
    ]
    for i, concept in enumerate(metadata.thumbnail_concepts, 1):
        lines.append(f"  {i}. {concept}")

    with open(txt_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    return [json_path, txt_path]
