# Release Guide

This document describes how to create a release for the bachata-beat-story-sync project.

## Automated Release Process

Releases are automated via GitHub Actions. The workflow is triggered by pushing a version tag to the `main` branch.

### Creating a Release

1. **Ensure all changes are committed** to `main` and pushed to GitHub.

2. **Update CHANGELOG.md**:
   - Move items from `[Unreleased]` section to a new version section
   - Use semantic versioning: `[MAJOR.MINOR.PATCH]`
   - Example:
     ```markdown
     ## [0.2.0] — 2026-04-15

     ### Added
     - New feature description

     ### Fixed
     - Bug fix description
     ```

3. **Update version in pyproject.toml**:
   - Change the `version` field in `[project]` section
   - Example: `version = "0.2.0"`

4. **Commit changes**:
   ```bash
   git add CHANGELOG.md pyproject.toml
   git commit -m "chore: prepare release v0.2.0"
   git push origin main
   ```

5. **Create and push the version tag**:
   ```bash
   git tag -a v0.2.0 -m "Release v0.2.0"
   git push origin v0.2.0
   ```

### What Happens Next

1. GitHub Actions automatically detects the tag push
2. The **validate** job runs:
   - Runs full lint checks (ruff format, ruff check)
   - Runs type checking (mypy)
   - Runs all unit tests (pytest)
3. If validation passes, the **release** job runs:
   - Creates a GitHub Release
   - Auto-generates release notes from commits since last tag
   - Uses conventional commit messages to categorize changes

### Conventional Commit Messages

The release notes are generated using conventional commits. Use these prefixes in commit messages:

- `feat:` — New features (appears in "Features" section)
- `fix:` — Bug fixes (appears in "Bug Fixes" section)
- `docs:` — Documentation changes (appears in "Documentation" section)
- `chore:`, `ci:`, `refactor:`, `test:` — Other changes (appears in "Other Changes" section)

Example:
```
feat: add support for multiple audio format inputs
fix: correct beat detection in high-energy sections
docs: update README with new API examples
```

### Release Note Categories

Auto-generated release notes are organized by:

1. **Features** — New functionality
2. **Bug Fixes** — Resolved issues
3. **Documentation** — Doc updates
4. **Other Changes** — Refactoring, CI, tests, chores

Dependencies and bot-generated changes are excluded from release notes.

### Rollback

If a release needs to be removed:

1. Delete the GitHub Release (via GitHub UI)
2. Delete the tag:
   ```bash
   git tag -d v0.2.0
   git push origin :refs/tags/v0.2.0
   ```

### Version Strategy

- Use **semantic versioning**: MAJOR.MINOR.PATCH
- Increment PATCH for bug fixes and small improvements
- Increment MINOR for new features that don't break existing APIs
- Increment MAJOR for breaking changes

Current version: **0.1.0** (pre-release development)
Target Phase 2 launch: **v1.0.0** (Week 4)
