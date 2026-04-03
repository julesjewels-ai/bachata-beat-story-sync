# Feature Backlog — Bachata Beat-Story Sync

> **📦 Archive (2026-04-03):** All implemented features (FEAT-001 through FEAT-034) moved to [`archive/completed.md`](archive/completed.md). Backlog is clean — next feature to prioritize is listed below.

---

## Completed Features (Reference)

All 34 features are fully implemented and archived. See [`archive/completed.md`](archive/completed.md) for summaries.

---

## Next Priority: FEAT-035 — Streamlit UI Folder Picker & Status Bar Polish

**Status:** `PROPOSED`

**Summary:** Integrate FEAT-032 (native folder picker) and FEAT-034 (persistent status bar with ETA) into the Streamlit UI, then optimize the overall user experience for pre-launch.

**Motivation:** The backend is now feature-complete with per-track clips, style filters, and smart B-roll insertion all working. The UI is the primary touch point for users — polishing it directly impacts perception and reduces onboarding friction. These two features (folder picker + status bar) are the highest-impact UI improvements remaining.

**Proposed Behaviour:**
- Implement native folder/file picker dialogs for audio and video input directories
- Add persistent status bar showing real-time progress, stage name, elapsed time, and ETA
- Retain log history in collapsible detail container (not disappearing)
- Clean up button layouts and improve visual hierarchy

**Scope:** `app_ui.py`, optional `src/ui/console.py` refactor for shared `ProgressTracker` logic.

---

_Add new `PROPOSED` features below this line._

