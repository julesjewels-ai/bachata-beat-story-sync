"""Unit tests for the YouTube metadata generator."""

import json
import os

from src.services.youtube_metadata import (
    TrackSegment,
    _build_backend_tags,
    _build_timecode_block,
    _pick,
    _primary_keyword,
    _timecode,
    generate_and_write,
    generate_metadata,
    write_youtube_metadata,
)

# ------------------------------------------------------------------
# Timecode formatting
# ------------------------------------------------------------------


def test_timecode_under_one_hour_is_mmss():
    assert _timecode(0) == "00:00"
    assert _timecode(75) == "01:15"


def test_timecode_over_one_hour_is_hhmmss():
    assert _timecode(3661) == "01:01:01"


# ------------------------------------------------------------------
# Deterministic template selection
# ------------------------------------------------------------------


def test_pick_is_deterministic_for_same_seed():
    templates = ["a", "b", "c", "d"]
    assert _pick(templates, "seed-x") == _pick(templates, "seed-x")


def test_pick_index_in_range():
    templates = ["a", "b"]
    for seed in ("one", "two", "three", "four"):
        assert _pick(templates, seed) in templates


def test_primary_keyword_deterministic_and_valid():
    kw = _primary_keyword("mi-cancion")
    assert kw == _primary_keyword("mi-cancion")
    assert kw in ("Música para Recordar", "Canciones de Amor")


# ------------------------------------------------------------------
# Backend tags
# ------------------------------------------------------------------


def test_backend_tags_includes_primary_and_artists():
    segs = [TrackSegment(artist="Romeo Santos", title="Propuesta", start_time=0.0)]
    csv = _build_backend_tags("Música para Recordar", segs)
    tags = [t.strip() for t in csv.split(",")]
    assert tags[0] == "música para recordar"
    assert "romeo santos" in tags
    assert "propuesta" in tags


def test_backend_tags_dedupes():
    # artist already present in base tags shouldn't duplicate
    segs = [TrackSegment(artist="bachata", title="bachata", start_time=0.0)]
    csv = _build_backend_tags("bachata", segs)
    tags = [t.strip() for t in csv.split(",")]
    assert tags.count("bachata") == 1


# ------------------------------------------------------------------
# Timecode block (tracklist)
# ------------------------------------------------------------------


def test_timecode_block_empty_when_no_tracks():
    assert _build_timecode_block([]) == ""


def test_timecode_block_lists_tracks_with_timecodes():
    segs = [
        TrackSegment(artist="A", title="Song1", start_time=0.0),
        TrackSegment(artist="B", title="Song2", start_time=185.0),
    ]
    block = _build_timecode_block(segs)
    assert "00:00 Song1 — A" in block
    assert "03:05 Song2 — B" in block


def test_timecode_block_omits_dash_when_no_artist():
    segs = [TrackSegment(artist="", title="Solo", start_time=0.0)]
    block = _build_timecode_block(segs)
    assert "00:00 Solo" in block
    assert "—" not in block.split("\n")[-1]


# ------------------------------------------------------------------
# generate_metadata per content type
# ------------------------------------------------------------------


def test_generate_metadata_mix_has_tracklist_in_description():
    segs = [TrackSegment(artist="A", title="Song1", start_time=0.0)]
    meta = generate_metadata("mix", segs, total_duration_s=200.0)
    assert meta.title
    assert "TRACKLIST" in meta.description
    assert "⏱ Duración: 03:20" in meta.description
    assert 0 < len(meta.hashtags) <= 15
    assert meta.tags_csv
    assert len(meta.thumbnail_concepts) == 3


def test_generate_metadata_song_uses_title_in_titletemplate():
    meta = generate_metadata(
        "song", [], total_duration_s=0.0, artist="Prince Royce", title="Darte un Beso"
    )
    assert "Darte un Beso" in meta.title


def test_hashtags_capped_at_15():
    segs = [
        TrackSegment(artist=f"Artist{i}", title=f"T{i}", start_time=float(i))
        for i in range(20)
    ]
    meta = generate_metadata("compilation", segs, total_duration_s=100.0)
    assert len(meta.hashtags) <= 15


# ------------------------------------------------------------------
# Writers
# ------------------------------------------------------------------


def test_write_youtube_metadata_creates_json_and_txt(tmp_path):
    meta = generate_metadata("song", [], title="X", artist="Y")
    paths = write_youtube_metadata(meta, str(tmp_path))
    assert len(paths) == 2
    json_path = [p for p in paths if p.endswith(".json")][0]
    txt_path = [p for p in paths if p.endswith(".txt")][0]
    assert os.path.isfile(json_path)
    assert os.path.isfile(txt_path)
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    assert data["title"] == meta.title
    assert data["hashtags"] == meta.hashtags


def test_generate_and_write_matches_two_step(tmp_path):
    segs = [TrackSegment(artist="A", title="Song1", start_time=0.0)]
    paths = generate_and_write(
        content_type="mix",
        track_segments=segs,
        total_duration_s=120.0,
        output_dir=str(tmp_path),
    )
    assert len(paths) == 2
    assert all(os.path.isfile(p) for p in paths)
