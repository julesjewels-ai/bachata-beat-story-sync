"""Integration-test fixtures for real media canaries."""

from __future__ import annotations

import math
import shutil
import struct
import subprocess
import wave
from pathlib import Path

import pytest


def _write_click_track(
    path: Path,
    *,
    duration: float = 6.0,
    bpm: float = 120.0,
    sample_rate: int = 22050,
) -> None:
    """Write a simple click-track WAV with clear beat onsets."""
    total_samples = int(duration * sample_rate)
    samples = [0.0] * total_samples
    beat_interval = 60.0 / bpm
    click_len = int(0.03 * sample_rate)  # 30ms transient

    for beat in range(int(duration / beat_interval) + 1):
        start = int(beat * beat_interval * sample_rate)
        for i in range(click_len):
            idx = start + i
            if idx >= total_samples:
                break
            envelope = 1.0 - (i / click_len)
            value = 0.9 * math.sin(2 * math.pi * 880 * (i / sample_rate)) * envelope
            samples[idx] += value

    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)  # int16
        wav.setframerate(sample_rate)
        wav.writeframes(
            b"".join(
                struct.pack("<h", max(-32767, min(32767, int(sample * 32767))))
                for sample in samples
            )
        )


def _render_clip(path: Path, source_filter: str, *, duration: float = 8.0) -> None:
    """Generate a tiny synthetic MP4 clip with ffmpeg."""
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        source_filter,
        "-t",
        f"{duration:.2f}",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-crf",
        "30",
        "-pix_fmt",
        "yuv420p",
        str(path),
    ]
    subprocess.run(
        cmd,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        shell=False,
    )


@pytest.fixture(scope="session")
def synthetic_story_media(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    """Create one tiny, reusable media set for integration tests."""
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("ffmpeg/ffprobe not available for integration canaries")

    root = tmp_path_factory.mktemp("story_media")
    audio_path = root / "click_track.wav"
    clips_dir = root / "clips"
    short_clips_dir = root / "short_clips"
    clips_dir.mkdir(parents=True, exist_ok=True)
    short_clips_dir.mkdir(parents=True, exist_ok=True)

    _write_click_track(audio_path, duration=6.0, bpm=120.0)
    _render_clip(clips_dir / "clip_motion.mp4", "testsrc=size=640x360:rate=30")
    _render_clip(clips_dir / "clip_static.mp4", "color=c=blue:size=640x360:rate=30")
    _render_clip(
        short_clips_dir / "clip_short_motion.mp4",
        "testsrc=size=640x360:rate=30",
        duration=2.2,
    )
    _render_clip(
        short_clips_dir / "clip_short_static.mp4",
        "color=c=red:size=640x360:rate=30",
        duration=2.0,
    )

    return {
        "audio_path": str(audio_path),
        "clips_dir": str(clips_dir),
        "short_clips_dir": str(short_clips_dir),
        "audio_duration": "6.0",
    }
