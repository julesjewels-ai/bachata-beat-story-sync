"""Unit tests for mix-fade filter generation in src/core/ffmpeg_renderer.py."""

from src.core.ffmpeg_renderer import _build_mix_fade_filters
from src.core.models import MixTrackSegment, PacingConfig


def test_build_mix_fade_filters_returns_empty_when_disabled():
    config = PacingConfig(
        mix_fade_transitions=False,
        mix_track_segments=[
            MixTrackSegment(start_time=0.0),
            MixTrackSegment(start_time=10.0),
        ],
    )
    assert _build_mix_fade_filters(config) == []


def test_build_mix_fade_filters_adds_timeline_enable_windows():
    config = PacingConfig(
        mix_fade_transitions=True,
        mix_fade_duration=0.25,
        mix_track_segments=[
            MixTrackSegment(start_time=0.0),
            MixTrackSegment(start_time=12.5),
        ],
    )

    filters = _build_mix_fade_filters(config)

    assert len(filters) == 2
    assert (
        "fade=t=out:st=12.250:d=0.250:color=black:"
        "enable='between(t,12.250,12.500)'"
    ) in filters
    assert (
        "fade=t=in:st=12.500:d=0.250:color=black:"
        "enable='between(t,12.500,12.750)'"
    ) in filters


def test_build_mix_fade_filters_sorts_and_keeps_positive_boundaries():
    config = PacingConfig(
        mix_fade_transitions=True,
        mix_fade_duration=0.4,
        mix_track_segments=[
            MixTrackSegment(start_time=20.0),
            MixTrackSegment(start_time=0.0),
            MixTrackSegment(start_time=8.0),
        ],
    )

    filters = _build_mix_fade_filters(config)

    assert len(filters) == 4
    assert "st=7.600:d=0.400" in filters[0]
    assert "st=8.000:d=0.400" in filters[1]
    assert "st=19.600:d=0.400" in filters[2]
    assert "st=20.000:d=0.400" in filters[3]
