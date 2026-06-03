# QA Report: localhost:8503

Date: 2026-05-04
Mode: diff-aware Standard
Target: http://localhost:8503/
Framework: Streamlit

## Summary

Baseline health score: 82
Final health score: 96
Issues found: 2
Fixes applied: 2 verified
Deferred: 0

PR summary: QA found 2 issues, fixed 2, health score 82 -> 96.

## Coverage

- Home page loaded with no browser console errors.
- Desktop and mobile screenshots captured.
- Quick Dry-Run Preview was clicked and exercised.
- Demo dry-run plan generation was checked from browser-triggered app logs and direct planner verification.
- Full pytest suite passed: 424 passed, 4 skipped.

## Issues

### ISSUE-001: Streamlit startup prints invalid config warnings

Severity: Medium
Category: Functional / Dev Experience
Evidence: app startup printed `"ui.hideFooter" is not a valid config option` and `"ui.hideSidebarNav" is not a valid config option`.
Fix status: verified
Files changed: `.streamlit/config.toml`

Fix: removed the removed Streamlit UI config keys.

### ISSUE-002: Quick demo dry-run could pass with zero planned segments

Severity: High
Category: Functional
Evidence: browser-triggered quick preview completed with `Total segments: 0` because `duration_sync_tolerance_seconds` was set to `20.0`, matching the 20 second preview target.
Fix status: verified
Files changed: `montage_config.yaml`, `tests/unit/test_app_config.py`

Fix: restored the documented strict tolerance to `0.10` and added a regression test that keeps the root config tolerance under 1 second.

## Verification

- `venv/bin/pytest tests/unit/test_app_config.py tests/unit/test_streamlit_requests.py -q`: 9 passed
- Direct demo planner check: `duration_sync_tolerance_seconds=0.1`, 4 planned segments, 20.00s coverage
- `make test`: 424 passed, 4 skipped
- Browser console after home and preview interaction: no console errors

## Screenshots

- `.gstack/qa-reports/screenshots/fixed-home.png`
- `.gstack/qa-reports/screenshots/mobile.png`
- `.gstack/qa-reports/screenshots/quick-dryrun-after-click.png`
