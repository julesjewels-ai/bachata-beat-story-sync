"""Unit tests for centralized app configuration loading."""

from __future__ import annotations

import textwrap

from src.config.app_config import build_pacing_config, load_app_config
from src.core.audio_mixer import load_audio_mix_config
from src.core.montage import load_pacing_config


def test_load_app_config_reads_all_sections(tmp_path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        textwrap.dedent(
            """\
            pacing:
              genre: salsa
            pipeline:
              track_clips:
                intro.wav: clips/intro
              track_styles:
                intro.wav: warm
            audio_mix:
              tempo_sync: false
            """
        )
    )

    config = load_app_config(str(config_file))

    assert config.pacing.genre == "salsa"
    assert config.pacing.video_style == "warm"
    assert config.pipeline.track_clips == {"intro.wav": "clips/intro"}
    assert config.pipeline.track_styles == {"intro.wav": "warm"}
    assert config.audio_mix.tempo_sync is False


def test_loader_wrappers_delegate_to_root_config(tmp_path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        textwrap.dedent(
            """\
            pacing:
              min_clip_seconds: 2.2
            audio_mix:
              sync_threshold: 0.07
            """
        )
    )

    pacing = load_pacing_config(str(config_file))
    audio_mix = load_audio_mix_config(str(config_file))

    assert pacing.min_clip_seconds == 2.2
    assert audio_mix.sync_threshold == 0.07


def test_build_pacing_config_merges_overrides(tmp_path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        textwrap.dedent(
            """\
            pacing:
              video_style: golden
              max_clips: 4
            """
        )
    )

    pacing = build_pacing_config(
        {"video_style": "bw", "max_duration_seconds": 12.0},
        config_path=str(config_file),
    )

    assert pacing.video_style == "bw"
    assert pacing.max_clips == 4
    assert pacing.max_duration_seconds == 12.0
