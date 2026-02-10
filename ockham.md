# Ockham Refactoring Log

## src/core/montage.py
Target: MontageGenerator.generate
Delta: Complexity Score 16 -> 12
Summary: Extracted video segment collection logic into `_collect_video_segments` helper method to separate resource acquisition from assembly.
