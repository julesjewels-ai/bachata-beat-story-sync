"""Audio/video transcription via faster-whisper (local, no API key required).

First run downloads the model from HuggingFace (~500MB for 'small').
Subsequent runs use the cached model from ~/.cache/huggingface/.

Usage:
    from src.core.transcriber import transcribe_video
    result = transcribe_video("compilation.mp4", language="es")
"""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile

from src.core.models import TranscriptResult, TranscriptSegment, TranscriptWord

logger = logging.getLogger(__name__)

# Default model — 'small' balances Spanish accuracy with speed/size.
# Override via WHISPER_MODEL env var or the model_size argument.
_DEFAULT_MODEL = os.environ.get("WHISPER_MODEL", "small")


def _extract_audio(video_path: str, tmp_dir: str) -> str:
    """Extract mono 16kHz WAV from video using FFmpeg. Returns WAV path."""
    wav_path = os.path.join(tmp_dir, "audio.wav")
    try:
        import imageio_ffmpeg

        ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        ffmpeg_bin = "ffmpeg"

    cmd = [
        ffmpeg_bin,
        "-y",
        "-i",
        video_path,
        "-ac",
        "1",  # mono
        "-ar",
        "16000",  # 16kHz — Whisper's native rate
        "-vn",  # strip video
        wav_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)  # nosec B603
    return wav_path


def transcribe_video(
    video_path: str,
    language: str | None = "es",
    model_size: str = _DEFAULT_MODEL,
    word_timestamps: bool = True,
) -> TranscriptResult:
    """Transcribe audio/video file using faster-whisper.

    Args:
        video_path: Path to MP4, WAV, or any FFmpeg-readable file.
        language: ISO 639-1 language code. 'es' for Spanish.
        model_size: Whisper model — 'tiny', 'small', 'medium', 'large-v2'.
        word_timestamps: Request word-level timing (increases processing time ~20%).

    Returns:
        TranscriptResult with all segments and word timings.
    """
    try:
        from faster_whisper import WhisperModel  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "faster-whisper not installed. Run: make install\n"
            "(or: pip install faster-whisper)"
        ) from exc

    logger.info("Loading Whisper model '%s'…", model_size)
    model = WhisperModel(model_size, device="cpu", compute_type="int8")

    # Extract audio from video to temp WAV (handles both MP4 and WAV inputs)
    is_video = not video_path.lower().endswith((".wav", ".mp3", ".flac", ".ogg"))
    audio_path = video_path

    with tempfile.TemporaryDirectory() as tmp_dir:
        if is_video:
            logger.info("Extracting audio from %s…", os.path.basename(video_path))
            audio_path = _extract_audio(video_path, tmp_dir)

        logger.info("Transcribing with language='%s'…", language)
        raw_segments, info = model.transcribe(
            audio_path,
            language=language,
            word_timestamps=word_timestamps,
            beam_size=5,
        )

        detected_lang = info.language if hasattr(info, "language") else language
        segments: list[TranscriptSegment] = []

        for seg in raw_segments:
            words: list[TranscriptWord] = []
            if word_timestamps and seg.words:
                for w in seg.words:
                    words.append(
                        TranscriptWord(
                            word=w.word,
                            start=w.start,
                            end=w.end,
                            probability=w.probability,
                        )
                    )
            segments.append(
                TranscriptSegment(
                    start=seg.start,
                    end=seg.end,
                    text=seg.text.strip(),
                    words=words,
                )
            )
            logger.debug("[%.1f → %.1f] %s", seg.start, seg.end, seg.text.strip())

    logger.info(
        "Transcription complete: %d segments, language=%s", len(segments), detected_lang
    )
    return TranscriptResult(
        audio_path=video_path,
        language=detected_lang,
        segments=segments,
    )
