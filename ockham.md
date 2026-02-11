## Refactoring Log

### MontageGenerator.generate in src/core/montage.py
- **Delta**: Complexity Score 16 -> 4
- **Summary**: Extracted timing calculation, clip collection loop, and resource cleanup into helper methods (`_calculate_timing`, `_collect_video_segments`, `_cleanup_resources`). This greatly simplified the `generate` method, removing deep nesting and large try/finally blocks.
