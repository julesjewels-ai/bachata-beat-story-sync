## Refactoring Log

- **Target:** `MontageGenerator.generate` in `src/core/montage.py`
- **Delta:** Complexity Score 11 -> 7
- **Summary:** Extracted clip collection logic into `_collect_video_segments` helper method to separate clip scheduling from video assembly.
