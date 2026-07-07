"""Standalone transcription CLI — transcribe any video or audio file."""

from __future__ import annotations

import argparse
import logging
import os
import sys

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transcribe a video or audio file → JSON + SRT"
    )
    parser.add_argument("video", help="Path to video or audio file to transcribe")
    parser.add_argument(
        "--language",
        default="es",
        metavar="LANG",
        help="Language code (default: es). Use 'auto' to detect.",
    )
    parser.add_argument(
        "--whisper-model",
        default="small",
        metavar="SIZE",
        help="Whisper model size: tiny, base, small, medium, large (default: small)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        metavar="DIR",
        help="Output directory (default: same dir as input file)",
    )
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    video_path = os.path.abspath(args.video)
    if not os.path.isfile(video_path):
        print(f"Error: file not found: {video_path}", file=sys.stderr)
        sys.exit(1)

    from src.core.srt_utils import transcript_stem, write_srt, write_transcript_json
    from src.core.transcriber import transcribe_video

    if args.output_dir:
        os.makedirs(args.output_dir, exist_ok=True)
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        stem = os.path.join(args.output_dir, base_name)
    else:
        stem = transcript_stem(video_path)

    json_out = f"{stem}_transcript.json"
    srt_out = f"{stem}_transcript.srt"

    language = args.language if args.language != "auto" else None
    model_size = args.whisper_model

    print(f"Transcribing: {video_path}")
    print(f"Model: {model_size}  Language: {args.language}")

    try:
        result = transcribe_video(video_path, language=language, model_size=model_size)
        write_transcript_json(result, json_out)
        write_srt(result.segments, srt_out)
        print(f"JSON: {json_out}  ({len(result.segments)} segments, lang={result.language})")
        print(f"SRT:  {srt_out}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            logger.exception("Transcription error:")
        sys.exit(1)


if __name__ == "__main__":
    main()
