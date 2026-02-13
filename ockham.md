# Ockham Refactor Log

## 2024-05-24

Target: MontageGenerator.generate in src/core/montage.py
Delta: Complexity Score 12 -> 5
Summary: Extracted `_calculate_timing` and `_collect_video_segments` helper methods to simplify the main generation logic and separate concerns.
