# Ockham Refactor Log

| Date | Target | Delta | Summary |
|------|--------|-------|---------|
| 2025-02-17 | src/core/montage.py:MontageGenerator.build_segment_plan | D -> C | Extracted segment property determination, clip selection, and section labeling into private helper methods to reduce cyclomatic complexity. |
