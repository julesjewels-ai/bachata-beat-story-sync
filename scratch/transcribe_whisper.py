#!/usr/bin/env python3
"""
Helper utility to transcribe audio files using Whisper Tiny and output synced LRC lyrics.
Usage:
    python scratch/transcribe_whisper.py --audio path/to/track.wav --output path/to/track.lrc
"""

import argparse
import os
import sys

def main():
    parser = argparse.ArgumentParser(description="Transcribe audio to LRC using Whisper Tiny.")
    parser.add_argument("--audio", required=True, help="Path to input audio file (WAV/MP3).")
    parser.add_argument("--output", help="Path to output LRC file (defaults to {audio_stem}.lrc).")
    parser.add_argument("--language", default=None, help="Language code (e.g. 'es' for Spanish, 'en' for English). Auto-detected if not specified.")
    args = parser.parse_args()

    if not os.path.exists(args.audio):
        print(f"Error: Audio file not found at '{args.audio}'", file=sys.stderr)
        sys.exit(1)

    # Resolve output path
    output_path = args.output
    if not output_path:
        output_path = os.path.splitext(args.audio)[0] + ".lrc"

    print("Loading whisper (requires 'pip install openai-whisper torch')...")
    try:
        import whisper
    except ImportError:
        print("Error: openai-whisper not installed.", file=sys.stderr)
        print("Please run: venv/bin/pip install openai-whisper torch", file=sys.stderr)
        sys.exit(1)

    print("Loading Whisper 'tiny' model...")
    model = whisper.load_model("tiny")

    print(f"Transcribing '{args.audio}'...")
    transcribe_kwargs = {}
    if args.language:
        transcribe_kwargs["language"] = args.language

    result = model.transcribe(args.audio, **transcribe_kwargs)

    print(f"Formatting timestamps and writing to '{output_path}'...")
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            for segment in result.get("segments", []):
                start = segment["start"]
                text = segment["text"].strip()
                if not text:
                    continue

                # Convert start time in seconds to LRC format: [mm:ss.xx]
                minutes = int(start // 60)
                seconds = int(start % 60)
                # Centiseconds (two digits)
                centiseconds = int(round((start % 1) * 100))
                # Handle edge case where rounding makes centiseconds 100
                if centiseconds >= 100:
                    seconds += 1
                    centiseconds -= 100
                if seconds >= 60:
                    minutes += 1
                    seconds -= 60

                lrc_timestamp = f"[{minutes:02d}:{seconds:02d}.{centiseconds:02d}]"
                f.write(f"{lrc_timestamp} {text}\n")
        print(f"Success! LRC file written to: {output_path}")
    except Exception as e:
        print(f"Error writing LRC file: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
