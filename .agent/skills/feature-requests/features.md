# Feature Backlog — Bachata Beat-Story Sync

**Status:** 36 core features complete. See [`archive/completed.md`](archive/completed.md) for reference. 4 features in backlog.

---

## Backlog

| Feature | Name | Status | Scope | Summary |
|---------|------|--------|-------|---------|
| FEAT-037 | Streamlit File Upload (Audio & Video) | `IMPLEMENTED` | Single sprint (30-45 min) | Replace local path inputs with `st.file_uploader()` widgets for audio files and video clips; handle temp file storage, support drag-and-drop UX, enable deployed version to work without requiring users to upload files |
| FEAT-038 | Quick Preview Plan Visibility | `PROPOSED` | Small (15-30 min) | In Quick Preview (dry-run) mode, move the generated segment plan to the top of the output section so users see it immediately after the run completes, rather than having to scroll past other content |
| FEAT-039 | Stable Progress Expander During Refresh | `PROPOSED` | Medium (1-2 hours) | Fix the progress expander (e.g. "Analyzing clip 1 of 4") collapsing on every Streamlit rerun. The dropdown should stay open while a task is in progress; investigate using `st.empty()` containers or session-state-driven expansion state to prevent collapse on refresh |
| FEAT-040 | Disable UI Controls During Active Processing | `PROPOSED` | Medium (1-2 hours) | Disable all action buttons (Generate, Quick Preview, Run Full Demo, etc.) while any pipeline run is in progress. Buttons should show a visual disabled state with a descriptive tooltip (e.g. "Processing in progress…"). The only active control during a run should be a Cancel button. Applies to demo mode, quick preview, and full render |

