---
description: Full development workflow — setup, run, test, lint, and iterate on the Bachata Beat-Story Sync project
---

# Development Workflow

// turbo-all

## 1. Environment Setup (First Time Only)

```bash
cd /Users/tutorsam/Documents/Business/YouTube/01_BBB/_software/bachata-beat-story-sync
make install
```

Then copy environment config:

```bash
cp .env.example .env
```

Edit `.env` to set your API keys (GEMINI_API_KEY, YOUTUBE_API_KEY) and any custom paths.

## 2. Activate Virtual Environment

```bash
source /Users/tutorsam/Documents/Business/YouTube/01_BBB/_software/bachata-beat-story-sync/venv/bin/activate
```

## 3. Run the Application

### Basic montage (requires audio file + video clip directory):

```bash
make run AUDIO="<path-to-audio-file>" VIDEO_DIR="<path-to-clips-dir>"
```

### Test mode (limits to 4 clips, 10s of music — fast iteration):

```bash
make run AUDIO="<path-to-audio-file>" VIDEO_DIR="<path-to-clips-dir>" TEST_MODE=1
```

### With custom limits:

```bash
make run AUDIO="<path-to-audio-file>" VIDEO_DIR="<path-to-clips-dir>" MAX_CLIPS=6 MAX_DURATION=30
```

### With Excel report:

```bash
python main.py --audio "<path>" --video-dir "<dir>" --export-report report.xlsx
```

### With B-roll:

```bash
python main.py --audio "<path>" --video-dir "<dir>" --broll-dir ./broll/
```

## 4. Run Tests

```bash
make test
```

Or directly with pytest for verbose output:

```bash
venv/bin/pytest tests/ -v
```

## 5. Type Checking

```bash
venv/bin/mypy src/ main.py --config-file mypy.ini
```

## 6. Clean Up

Remove venv, caches, and generated MP4 files:

```bash
make clean
```

## 7. Project Structure Reference

```
main.py                    # CLI entry point (argparse → BachataSyncEngine)
src/
  core/
    app.py                 # BachataSyncEngine — orchestrates the pipeline
    audio_analyzer.py      # Librosa beat/onset/BPM detection
    audio_mixer.py         # Multi-track audio mixing
    video_analyzer.py      # OpenCV motion-intensity scoring
    montage.py             # FFmpeg clip extraction & assembly
    models.py              # Pydantic DTOs (AudioMetadata, VideoClip, etc.)
    validation.py          # Security: path traversal guards
    interfaces.py          # Observer protocol for progress bars
  services/
    reporting/             # Excel report generation (openpyxl)
  ui/
    console.py             # Rich progress bar observer
tests/
  unit/                    # pytest unit tests
docs/                      # User guide, architecture, API reference
montage_config.yaml        # Montage assembly configuration
Makefile                   # install / run / test / clean targets
```

## 8. Common Development Tasks

### Adding a new core module
1. Create file in `src/core/`
2. Add Pydantic models to `src/core/models.py` if new data shapes are needed
3. Wire into `BachataSyncEngine` in `src/core/app.py`
4. Write tests in `tests/unit/`
5. Run `make test` to verify

### Adding a new service
1. Create directory or file under `src/services/`
2. Follow the existing pattern (see `src/services/reporting/`)
3. Add tests and verify with `make test`

### Debugging a run
- Check logs — the app uses Python `logging` at INFO level by default
- Set `LOG_LEVEL=DEBUG` in `.env` for verbose output
- Use `--test-mode` flag to limit processing scope during iteration
