# Contributing Guide — Bachata Beat-Story Sync

> How to set up your development environment, write tests, and submit changes.

---

## Getting Started

### 1. Clone and Install

```bash
git clone <repo-url>
cd bachata-beat-story-sync

# Create virtual environment and install all dependencies
make install

# Activate the virtual environment
source venv/bin/activate
```

### 2. Verify Setup

```bash
# Run the test suite
make test

# Run type checking
python -m mypy src/
```

---

## Project Structure

```
src/
├── core/           # Business logic (audio, video, montage)
├── services/       # External integrations (reporting)
└── ui/             # User interface (console output)

tests/
├── unit/           # Unit tests per module
├── test_*.py       # Integration-level tests
```

- **Core** should have zero dependencies on Services or UI
- **Services** may depend on Core models only
- **UI** may depend on Core interfaces only

---

## Coding Standards

### Python
- **Version**: 3.9+ compatible (avoid `X | Y` union syntax, use `Optional[X]`)
- **Type hints**: Use type annotations on all public functions
- **Docstrings**: Google-style docstrings on all public methods
- **Models**: Use Pydantic `BaseModel` for any data crossing module boundaries

### Naming
| Element | Convention | Example |
|---------|-----------|---------|
| Files | `snake_case.py` | `audio_analyzer.py` |
| Classes | `PascalCase` | `AudioAnalyzer` |
| Functions | `snake_case` | `scan_video_library` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_VIDEO_FRAMES` |
| Test files | `test_<module>.py` | `test_audio_analyzer.py` |

### Input Validation
- All file path inputs **must** go through `validate_file_path()` in `validation.py`
- Use Pydantic `field_validator` for input models
- Never trust user-provided paths — reject `..`, check existence, validate extensions

---

## Testing

### Running Tests

```bash
# All tests
make test

# Specific test file
python -m pytest tests/unit/test_audio_analyzer.py -v

# With coverage (if installed)
python -m pytest --cov=src tests/ -v
```

### Test Organization

| Directory | Purpose | Style |
|-----------|---------|-------|
| `tests/unit/` | Isolated unit tests per class | pytest preferred |
| `tests/` | Module-level and integration tests | pytest or unittest |

### Writing Tests

1. **Name the file** `test_<module_name>.py`
2. **Use fixtures** for common setup (prefer `@pytest.fixture` over `setUp`)
3. **Mock external dependencies** — no real files, no network, no ffmpeg
4. **Test edge cases** — empty inputs, invalid paths, corrupt files

```python
# Example: Unit test with mocking
@patch("src.core.validation.os.path.exists", return_value=True)
def test_valid_input(self, mock_exists):
    input_data = AudioAnalysisInput(file_path="song.wav")
    assert input_data.file_path == "song.wav"
```

---

## Making Changes

### Workflow

1. **Create a branch** from `main`
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Make your changes** following the coding standards above

3. **Run validation**
   ```bash
   make test                    # Tests pass
   python -m mypy src/          # Type checking passes
   ```

4. **Commit with a descriptive message**
   ```bash
   git commit -m "feat: add crossfade transitions between clips"
   ```

5. **Push and open a PR**

### Commit Message Format

Use conventional commits:

| Prefix | Usage |
|--------|-------|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `docs:` | Documentation only |
| `test:` | Adding or fixing tests |
| `refactor:` | Code restructuring |
| `chore:` | Build/CI/tooling changes |

---

## Adding a New Analyzer

To add a new analysis module (e.g., sentiment analysis):

1. **Create the module** in `src/core/` (e.g., `sentiment_analyzer.py`)
2. **Define input model** as a Pydantic `BaseModel` with `field_validator`
3. **Define result model** in `models.py`
4. **Add unit tests** in `tests/unit/test_sentiment_analyzer.py`
5. **Wire into `BachataSyncEngine`** or `main.py`
6. **Update docs** (`api-reference.md`, `architecture.md`)
