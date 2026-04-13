"""Centralized typed application configuration loading."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Mapping

import yaml
from pydantic import BaseModel, ConfigDict, Field

from src.core.genre_presets import apply_genre_preset
from src.core.models import AudioMixConfig, PacingConfig

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "montage_config.yaml"


class PipelineConfig(BaseModel):
    """Pipeline-only settings loaded from the root config file."""

    model_config = ConfigDict(extra="forbid")

    track_clips: dict[str, str] = Field(default_factory=dict)
    track_styles: dict[str, str] = Field(default_factory=dict)


class AppConfig(BaseModel):
    """Top-level application configuration."""

    model_config = ConfigDict(extra="forbid")

    pacing: PacingConfig = Field(default_factory=PacingConfig)
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    audio_mix: AudioMixConfig = Field(default_factory=AudioMixConfig)


def _resolve_path(config_path: str | None) -> Path:
    """Return the config file path to load."""
    return Path(config_path) if config_path else DEFAULT_CONFIG_PATH


def _build_app_config(raw: Mapping[str, Any]) -> AppConfig:
    """Validate raw YAML data as ``AppConfig``."""
    pacing_data = dict(raw.get("pacing", {}) or {})
    genre = pacing_data.get("genre")
    if genre:
        pacing_data = apply_genre_preset(genre, pacing_data)

    return AppConfig(
        pacing=PacingConfig(**pacing_data),
        pipeline=PipelineConfig(**(raw.get("pipeline", {}) or {})),
        audio_mix=AudioMixConfig(**(raw.get("audio_mix", {}) or {})),
    )


def load_app_config(config_path: str | None = None) -> AppConfig:
    """Load the full application configuration from YAML.

    Falls back to validated defaults if the file is missing or invalid.
    """
    path = _resolve_path(config_path)
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
            config = _build_app_config(raw)
            logger.info("Loaded app config from %s", path)
            return config
        except Exception as e:
            logger.warning(
                "Failed to load app config from %s: %s. Using defaults.", path, e
            )

    return AppConfig()


def build_pacing_config(
    overrides: Mapping[str, Any] | None = None,
    *,
    config_path: str | None = None,
) -> PacingConfig:
    """Load base pacing config and apply runtime overrides."""
    base = load_app_config(config_path).pacing
    if not overrides:
        return base
    return PacingConfig(**{**base.model_dump(), **dict(overrides)})
