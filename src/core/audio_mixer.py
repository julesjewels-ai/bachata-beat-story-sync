"""
Audio mixer for combining multiple audio tracks.

Supports BPM-matched crossfades (Phase 1) via FFmpeg's atempo time-stretch
filter, which prevents rhythmic clashing at track boundaries without altering
pitch. Beat-phase alignment is deferred to Phase 2.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import tempfile

from src.config.app_config import load_app_config
from src.core.interfaces import ProgressObserver
from src.core.models import AudioMixConfig

logger = logging.getLogger(__name__)

FFMPEG_TIMEOUT = 600
SUPPORTED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".aac"}

# Sidecar file stored alongside _mixed_audio.wav to detect config changes
_CACHE_PARAMS_SUFFIX = ".mix_params"


# ------------------------------------------------------------------
# Config loading
# ------------------------------------------------------------------


def load_audio_mix_config(config_path: str | None = None) -> AudioMixConfig:
    """
    Load audio mix configuration from YAML file.
    Falls back to AudioMixConfig defaults if missing or invalid.
    """
    return load_app_config(config_path).audio_mix


# ------------------------------------------------------------------
# Path resolution
# ------------------------------------------------------------------


def resolve_audio_path(
    audio_path: str,
    observer: ProgressObserver | None = None,
) -> str:
    """Resolve an audio path that may be a file or a directory.

    If *audio_path* is a directory containing multiple supported audio
    files, they are automatically mixed into a single WAV using
    :class:`AudioMixer`.  The mixed output is cached at
    ``<dir>/_mixed_audio.wav`` so repeated runs are instant.

    Args:
        audio_path: Path to a single audio file **or** a directory
            containing audio files to mix.
        observer: Optional progress observer forwarded to the mixer.

    Returns:
        The resolved path to a single audio file ready for analysis.
    """
    if not os.path.isdir(audio_path):
        return audio_path

    valid_files = [
        f
        for f in os.listdir(audio_path)
        if os.path.isfile(os.path.join(audio_path, f))
        and any(f.lower().endswith(ext.lower()) for ext in SUPPORTED_AUDIO_EXTENSIONS)
        and f != "_mixed_audio.wav"
    ]

    if len(valid_files) > 1:
        logger.info("Multiple audio files detected. Mixing tracks...")
        mixed_output = os.path.join(audio_path, "_mixed_audio.wav")
        mixer = AudioMixer()
        audio_path = mixer.mix_audio_folder(audio_path, mixed_output, observer=observer)
        logger.info("Mixed audio saved to: %s", audio_path)

    return audio_path


# ------------------------------------------------------------------
# Pure helper functions (easily unit-testable)
# ------------------------------------------------------------------


def _config_fingerprint(config: AudioMixConfig, audio_files: list[str]) -> str:
    """Return an MD5 hash of the mix-relevant config fields AND input files.

    Used as a cache key so that changing tempo_sync, sync_threshold,
    OR the set of input files triggers a fresh mix.
    """
    # Include file metadata (name + size) in the fingerprint
    file_meta = []
    for path in sorted(audio_files):
        try:
            size = os.path.getsize(path)
            file_meta.append(f"{os.path.basename(path)}:{size}")
        except OSError:
            file_meta.append(os.path.basename(path))

    data = {
        "crossfade": config.crossfade_duration_seconds,
        "tempo_sync": config.tempo_sync,
        "sync_threshold": config.sync_threshold,
        "files": file_meta,
    }
    return hashlib.md5(
        json.dumps(data, sort_keys=True).encode(), usedforsecurity=False
    ).hexdigest()


def _calculate_atempo_ratio(
    source_bpm: float,
    target_bpm: float,
    threshold: float,
) -> float | None:
    """Calculate the FFmpeg atempo ratio to align *source_bpm* to *target_bpm*.

    Returns ``None`` when the difference is negligible (< 1 BPM) or when
    the required stretch exceeds the safety *threshold* — in both cases
    no filter should be applied.

    Args:
        source_bpm: BPM of the incoming track to be stretched.
        target_bpm: BPM of the current mix (the target tempo).
        threshold: Maximum fractional shift allowed (e.g. 0.10 for ±10%).

    Returns:
        The ``atempo`` ratio as a float, or ``None`` to skip stretching.
    """
    if abs(source_bpm - target_bpm) < 1.0:
        logger.debug(
            "BPM diff < 1 BPM (%.1f→%.1f); skipping tempo sync.", source_bpm, target_bpm
        )
        return None

    ratio = target_bpm / source_bpm

    if not (1.0 - threshold) <= ratio <= (1.0 + threshold):
        logger.warning(
            "BPM diff %.1f→%.1f (ratio %.3f) exceeds threshold %.0f%%; "
            "tempo sync skipped to preserve audio quality.",
            source_bpm,
            target_bpm,
            ratio,
            threshold * 100,
        )
        return None

    return ratio


def _build_filter_complex(
    atempo_ratio: float | None,
    crossfade_duration: float,
) -> str:
    """Build the FFmpeg filter_complex string for a crossfade step.

    When *atempo_ratio* is provided, the second input stream is first
    time-stretched to match the current mix tempo, then crossfaded with
    the first stream.  When it is ``None`` the plain acrossfade filter is
    used — identical to the pre-Phase-1 behaviour.

    Args:
        atempo_ratio: Stretch ratio for the incoming track, or ``None``.
        crossfade_duration: Duration of the crossfade overlap in seconds.

    Returns:
        A filter_complex string ready to pass to ``ffmpeg -filter_complex``.
    """
    cf = f"acrossfade=d={crossfade_duration:.3f}:c1=tri:c2=tri[a]"
    if atempo_ratio is not None:
        return f"[1:a]atempo={atempo_ratio:.6f}[a1];[0:a][a1]{cf}"
    return f"[0:a][1:a]{cf}"


# ------------------------------------------------------------------
# AudioMixer class
# ------------------------------------------------------------------


class AudioMixer:
    """
    Combines multiple audio files into a single continuous mix with BPM-matched
    crossfades.
    """

    def mix_audio_folder(
        self,
        folder_path: str,
        output_path: str,
        observer: ProgressObserver | None = None,
    ) -> str:
        """
        Discovers supported audio files in the given folder, sorts them
        alphanumerically, and concatenates them with BPM-matched crossfades.

        If the final output file already exists **and** its config fingerprint
        matches current config AND file list, the cached file is reused.
        """
        config = load_audio_mix_config()
        audio_files = self._discover_audio_files(folder_path)
        if not audio_files:
            raise ValueError(f"No supported audio files found in {folder_path}")

        # --- Cache validation with config fingerprint (including files) ---
        params_path = output_path + _CACHE_PARAMS_SUFFIX
        current_fp = _config_fingerprint(config, audio_files)

        if os.path.exists(output_path):
            cached_fp = None
            if os.path.exists(params_path):
                try:
                    with open(params_path) as f:
                        cached_fp = f.read().strip()
                except OSError:
                    pass
            if cached_fp == current_fp:
                logger.info(
                    "Mixed audio cache hit at %s (config and files unchanged).", output_path
                )
                return output_path
            logger.info(
                "Mix folder or config changed; regenerating mix."
            )
            try:
                os.remove(output_path)
            except OSError:
                pass

        logger.info("Found %d audio files in %s", len(audio_files), folder_path)

        # --- Pre-analyse all source files for BPM (before any FFmpeg work) ---
        bpm_map: dict[str, float] = {}
        if config.tempo_sync and len(audio_files) > 1:
            bpm_map = self._analyse_bpm(audio_files, observer)

        result = self._mix_files(
            audio_files,
            output_path,
            config,
            bpm_map,
            observer,
        )

        # Write config fingerprint sidecar
        try:
            with open(params_path, "w") as f:
                f.write(current_fp)
        except OSError as e:
            logger.warning("Could not write mix params sidecar: %s", e)

        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _analyse_bpm(
        self,
        audio_files: list[str],
        observer: ProgressObserver | None = None,
    ) -> dict[str, float]:
        """Run BPM analysis on all source files and return a path→BPM map.

        This must be called on **original source files only**, never on
        intermediate mix files, to ensure reliable BPM detection.
        """
        # Lazy import to avoid circular dependencies at module load time
        from src.core.audio_analyzer import (  # noqa: WPS433
            AudioAnalysisInput,
            AudioAnalyzer,
        )

        analyzer = AudioAnalyzer()
        bpm_map: dict[str, float] = {}
        total = len(audio_files)

        for idx, path in enumerate(audio_files):
            if observer:
                observer.on_progress(
                    idx,
                    total,
                    f"Analysing BPM [{idx + 1}/{total}]: {os.path.basename(path)}",
                )
            try:
                result = analyzer.analyze(AudioAnalysisInput(file_path=path))
                bpm_map[path] = result.bpm
                logger.info(
                    "BPM detected: %s → %.1f BPM", os.path.basename(path), result.bpm
                )
            except Exception as e:
                logger.warning(
                    "BPM analysis failed for %s: %s — tempo sync will be skipped.",
                    os.path.basename(path),
                    e,
                )

        return bpm_map

    def _discover_audio_files(self, folder_path: str) -> list[str]:
        """
        Find all supported audio files and format them alphanumerically.
        Explicitly excludes the output cache file (_mixed_audio.wav) so it
        doesn't recursively get mixed into a new track.
        """
        files = []
        for file in os.listdir(folder_path):
            if file == "_mixed_audio.wav":
                continue
            if os.path.splitext(file)[1].lower() in SUPPORTED_AUDIO_EXTENSIONS:
                files.append(os.path.join(folder_path, file))
        return sorted(files)

    def _mix_files(
        self,
        audio_files: list[str],
        output_path: str,
        config: AudioMixConfig,
        bpm_map: dict[str, float],
        observer: ProgressObserver | None = None,
    ) -> str:
        """
        Sequentially concatenates audio files using FFmpeg 'acrossfade' filter,
        applying atempo time-stretching when BPM maps are available.
        """
        if not shutil.which("ffmpeg"):
            raise RuntimeError("FFmpeg is not installed or not on PATH.")

        if len(audio_files) == 1:
            logger.info("Only one audio file found, skipping mix and copying.")
            shutil.copy2(audio_files[0], output_path)
            return output_path

        crossfade_duration = config.crossfade_duration_seconds
        sync_threshold = config.sync_threshold

        temp_dir = tempfile.mkdtemp(prefix="audio_mix_")
        try:
            current_input = audio_files[0]
            # Track the outgoing BPM using original source BPM values only
            current_bpm: float | None = bpm_map.get(audio_files[0])

            for i in range(1, len(audio_files)):
                next_source = audio_files[i]
                next_bpm: float | None = bpm_map.get(next_source)
                is_last = i == len(audio_files) - 1

                if observer:
                    observer.on_progress(
                        i, len(audio_files), f"Mixing track {i + 1}..."
                    )

                step_output = (
                    output_path
                    if is_last
                    else os.path.join(temp_dir, f"mix_step_{i:04d}.wav")
                )

                # Calculate tempo ratio for this transition
                atempo_ratio: float | None = None
                if current_bpm is not None and next_bpm is not None:
                    atempo_ratio = _calculate_atempo_ratio(
                        next_bpm, current_bpm, sync_threshold
                    )
                    if atempo_ratio is not None:
                        logger.info(
                            "Tempo sync: %.1f→%.1f BPM (atempo=%.4f) for track %d→%d",
                            next_bpm,
                            current_bpm,
                            atempo_ratio,
                            i,
                            i + 1,
                        )

                filter_complex = _build_filter_complex(atempo_ratio, crossfade_duration)

                cmd = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    current_input,
                    "-i",
                    next_source,
                    "-filter_complex",
                    filter_complex,
                    "-map",
                    "[a]",
                    # Always output as wav internally for lossless intermediates
                    "-c:a",
                    "pcm_s16le",
                    step_output,
                ]

                self._run_ffmpeg(cmd, f"crossfade {i}/{len(audio_files) - 1}")

                if current_input != audio_files[0] and os.path.exists(current_input):
                    os.remove(current_input)

                current_input = step_output
                # Update the outgoing BPM to the source BPM of the track we merged
                current_bpm = next_bpm

            if observer:
                observer.on_progress(
                    len(audio_files), len(audio_files), "Mixing complete."
                )
            return output_path

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @staticmethod
    def _run_ffmpeg(cmd: list[str], stage_name: str) -> None:
        """Delegate to the shared FFmpeg runner."""
        from src.core.ffmpeg_utils import run_ffmpeg  # noqa: WPS433

        run_ffmpeg(cmd, stage_name)
