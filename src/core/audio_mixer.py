"""
Audio mixer for combining multiple audio tracks.
"""

import logging
import os
import shutil
import tempfile

import yaml

from src.core.interfaces import ProgressObserver
from src.core.models import AudioMixConfig

logger = logging.getLogger(__name__)

FFMPEG_TIMEOUT = 600
DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "montage_config.yaml",
)
SUPPORTED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".aac"}


def load_audio_mix_config(config_path: str | None = None) -> AudioMixConfig:
    """
    Load audio mix configuration from YAML file.
    Falls back to AudioMixConfig defaults if missing or invalid.
    """
    path = config_path if config_path else DEFAULT_CONFIG_PATH
    if os.path.exists(path):
        try:
            with open(path) as f:
                raw = yaml.safe_load(f) or {}
            mix_data = raw.get("audio_mix", {})
            return AudioMixConfig(**mix_data)
        except Exception as e:
            logger.warning(
                "Failed to load audio mix config from %s: %s. Using defaults.", path, e
            )
    return AudioMixConfig()


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
        audio_path = mixer.mix_audio_folder(
            audio_path, mixed_output, observer=observer
        )
        logger.info("Mixed audio saved to: %s", audio_path)

    return audio_path


class AudioMixer:
    """
    Combines multiple audio files into a single continuous mix with crossfades.
    """

    def mix_audio_folder(
        self,
        folder_path: str,
        output_path: str,
        observer: ProgressObserver | None = None,
    ) -> str:
        """
        Discovers supported audio files in the given folder, sorts them
        alphanumerically, and concatenates them with crossfades.

        If the final output file already exists, it skips generation and
        returns the existing file, providing a simple cache.

        Args:
            folder_path: Path to directory containing audio files.
            output_path: Path where the mixed output should be saved.
            observer: Optional progress observer.

        Returns:
            The path to the output mixed audio file.
        """
        if os.path.exists(output_path):
            logger.info(
                "Mixed audio file already exists at %s, using cache.", output_path
            )
            return output_path

        audio_files = self._discover_audio_files(folder_path)
        if not audio_files:
            raise ValueError(f"No supported audio files found in {folder_path}")

        logger.info("Found %d audio files in %s", len(audio_files), folder_path)

        config = load_audio_mix_config()
        return self._mix_files(
            audio_files, output_path, config.crossfade_duration_seconds, observer
        )

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
        crossfade_duration: float,
        observer: ProgressObserver | None = None,
    ) -> str:
        """
        Sequentially concatenates audio files using FFmpeg 'acrossfade' filter.
        """
        if not shutil.which("ffmpeg"):
            raise RuntimeError("FFmpeg is not installed or not on PATH.")

        if len(audio_files) == 1:
            logger.info("Only one audio file found, skipping mix and copying.")
            shutil.copy2(audio_files[0], output_path)
            return output_path

        temp_dir = tempfile.mkdtemp(prefix="audio_mix_")
        try:
            current_input = audio_files[0]

            for i in range(1, len(audio_files)):
                next_input = audio_files[i]
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

                # We need exact crossfade because acrossfade
                # handles overlap automatically if duration
                # is specified. Filter form:
                # [0:a][1:a]acrossfade=d=duration:c1=tri:c2=tri[a]
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    current_input,
                    "-i",
                    next_input,
                    "-filter_complex",
                    f"[0:a][1:a]acrossfade=d={crossfade_duration:.3f}:c1=tri:c2=tri[a]",
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
        from src.core.ffmpeg_utils import run_ffmpeg

        run_ffmpeg(cmd, stage_name)
