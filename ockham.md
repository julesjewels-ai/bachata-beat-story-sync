# Ockham's Razor - Technical Debt Log

## Refactoring History

### src/core/montage.py

* **Target:** `MontageGenerator.generate`
* **Delta:** Complexity Score 16 $\rightarrow$ 4
* **Summary:** Extracted logic into `_calculate_timing`, `_collect_video_segments`, and `_cleanup_resources` to reduce cyclomatic complexity and improve readability. Ensured resource cleanup is robust by passing list references. Patched `random.shuffle` in tests to eliminate flakiness.
