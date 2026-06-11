# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- GitHub Actions release automation (version tagging, changelog generation)
- Release workflow with automated versioning on tag push

### Changed

### Fixed
- Beat-sync drift guards were effectively disabled: `montage_config.yaml` had
  `duration_sync_tolerance_seconds` raised to 20.0 (via 3.0) in unrelated
  commits, letting renders drift up to 20s from the audio before any check
  fired — large drift was silently end-trimmed/padded instead of raised,
  producing out-of-sync output. Restored the documented 0.10s tolerance and
  added a config-rot regression test
  (`test_checked_in_config_keeps_sync_guards_effective`) that fails if the
  checked-in tolerance leaves the documented 0.05–1.0s range.

### Deprecated

### Removed

### Security

## [1.0.0] — Phase 2 Launch (Planned)

- Initial public release with full feature set

## [0.1.0] — Initial Release (Current)

- Bachata beat-to-clip synchronization engine
- MoviePy v2 clip manipulation
- FFmpeg rendering backend
- Audio analysis (BPM, peaks, beat tracking)
- Video analysis (intensity scoring, scene detection)
- Multi-track audio mixing with tempo sync
- YouTube Shorts generation
- Streamlit UI
- Comprehensive test suite
- Type checking and linting infrastructure
