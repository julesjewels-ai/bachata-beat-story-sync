"""Unit tests for planner clip selection helpers."""

from src.core.models import PacingConfig, VideoAnalysisResult
from src.core.planner.selection import select_clip


def _clip(path: str, intensity: float = 0.5) -> VideoAnalysisResult:
    return VideoAnalysisResult(
        path=path,
        intensity_score=intensity,
        duration=10.0,
        is_vertical=False,
        thumbnail_data=None,
    )


def test_select_clip_prefers_forced_prefix() -> None:
    forced = [_clip("/videos/1_intro.mp4")]
    regular = _clip("/videos/regular.mp4")

    selected = select_clip(
        forced_clips=forced,
        forced_clip_idx=0,
        is_broll=False,
        broll_clips=None,
        broll_idx=0,
        timeline_pos=0.0,
        last_broll_time=0.0,
        config=PacingConfig(),
        pools={"high": [regular], "medium": [], "low": []},
        pool_indices={"high": 0, "medium": 0, "low": 0},
        level="high",
        clip_idx=0,
        pick_from_pool=lambda pools, indices, level: pools[level][0],
    )

    assert selected.clip.path == "/videos/1_intro.mp4"
    assert selected.forced_clip_idx == 1
    assert "Forced prefix ordering" in selected.reason


def test_select_clip_uses_broll_when_requested() -> None:
    broll = [_clip("/videos/broll_01.mp4")]

    selected = select_clip(
        forced_clips=[],
        forced_clip_idx=0,
        is_broll=True,
        broll_clips=broll,
        broll_idx=0,
        timeline_pos=12.0,
        last_broll_time=0.0,
        config=PacingConfig(),
        pools={"high": [], "medium": [], "low": []},
        pool_indices={"high": 0, "medium": 0, "low": 0},
        level="low",
        clip_idx=0,
        pick_from_pool=lambda pools, indices, level: _clip("/videos/fallback.mp4"),
    )

    assert selected.clip.path == "/videos/broll_01.mp4"
    assert selected.broll_idx == 1
    assert selected.last_broll_time == 12.0
    assert "B-roll interval triggered" in selected.reason


def test_select_clip_falls_back_to_pool_selection() -> None:
    regular = _clip("/videos/regular.mp4", intensity=0.9)
    called = {"value": False}

    def pick_from_pool(pools, indices, level):  # noqa: ANN001
        called["value"] = True
        return pools[level][0]

    selected = select_clip(
        forced_clips=[],
        forced_clip_idx=0,
        is_broll=False,
        broll_clips=None,
        broll_idx=0,
        timeline_pos=3.0,
        last_broll_time=0.0,
        config=PacingConfig(),
        pools={"high": [regular], "medium": [], "low": []},
        pool_indices={"high": 0, "medium": 0, "low": 0},
        level="high",
        clip_idx=4,
        pick_from_pool=pick_from_pool,
    )

    assert called["value"] is True
    assert selected.clip.path == "/videos/regular.mp4"
    assert selected.clip_idx == 5
    assert "Intensity matched" in selected.reason
