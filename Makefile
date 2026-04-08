PYTHON = python3.13
VENV = venv
BIN = $(VENV)/bin
TEST_MODE ?=
MAX_CLIPS ?=
MAX_DURATION ?=
VIDEO_STYLE ?=
AUDIO_OVERLAY ?=
AUDIO_OVERLAY_OPACITY ?=
AUDIO_OVERLAY_POSITION ?=
BROLL_INTERVAL ?=
BROLL_VARIANCE ?=
EXPLAIN ?=
INTRO_EFFECT ?=
INTRO_EFFECT_DURATION ?=
DRY_RUN ?=
DRY_RUN_OUTPUT ?=
GENRE ?=
WATCH ?=
ZOOM ?=

# Pipeline optional flags
SHORTS_COUNT ?= 1
SHORTS_DURATION ?= 60
OUTPUT_DIR ?= output_pipeline
SHARED_SCAN ?= 0
SMART_START ?=

# Build optional flags
EXTRA_FLAGS =

ifeq ($(TEST_MODE),1)
  EXTRA_FLAGS += --test-mode
endif

ifneq ($(MAX_CLIPS),)
  EXTRA_FLAGS += --max-clips $(MAX_CLIPS)
endif

ifneq ($(MAX_DURATION),)
  EXTRA_FLAGS += --max-duration $(MAX_DURATION)
endif

ifneq ($(GENRE),)
  EXTRA_FLAGS += --genre $(GENRE)
endif

ifneq ($(VIDEO_STYLE),)
  EXTRA_FLAGS += --video-style $(VIDEO_STYLE)
endif

ifneq ($(AUDIO_OVERLAY),)
  EXTRA_FLAGS += --audio-overlay $(AUDIO_OVERLAY)
endif

ifneq ($(AUDIO_OVERLAY_OPACITY),)
  EXTRA_FLAGS += --audio-overlay-opacity $(AUDIO_OVERLAY_OPACITY)
endif

ifneq ($(AUDIO_OVERLAY_POSITION),)
  EXTRA_FLAGS += --audio-overlay-position $(AUDIO_OVERLAY_POSITION)
endif

ifneq ($(BROLL_INTERVAL),)
  EXTRA_FLAGS += --broll-interval $(BROLL_INTERVAL)
endif

ifneq ($(BROLL_VARIANCE),)
  EXTRA_FLAGS += --broll-variance $(BROLL_VARIANCE)
endif

ifeq ($(EXPLAIN),1)
  EXTRA_FLAGS += --explain
endif

ifneq ($(INTRO_EFFECT),)
  EXTRA_FLAGS += --intro-effect $(INTRO_EFFECT)
endif

ifneq ($(INTRO_EFFECT_DURATION),)
  EXTRA_FLAGS += --intro-effect-duration $(INTRO_EFFECT_DURATION)
endif

ifeq ($(SHARED_SCAN), 1)
  EXTRA_FLAGS += --shared-scan
endif

ifeq ($(SMART_START), 0)
  EXTRA_FLAGS += --no-smart-start
endif

ifeq ($(DRY_RUN),1)
  EXTRA_FLAGS += --dry-run
endif

ifeq ($(WATCH),1)
  EXTRA_FLAGS += --watch
endif

ifneq ($(DRY_RUN_OUTPUT),)
  EXTRA_FLAGS += --dry-run-output $(DRY_RUN_OUTPUT)
endif

ifneq ($(ZOOM),)
  EXTRA_FLAGS += --zoom $(ZOOM)
endif

.PHONY: install run run-shorts full-pipeline mcp-serve test lint lint-fix format check-types refactor clean download-demo

download-demo:
	@mkdir -p demo/audio demo/clips
	@echo ""
	@echo "📦 Demo asset directory ready: demo/"
	@echo ""
	@echo "Place your royalty-free assets here:"
	@echo "  demo/audio/sample_bachata.mp3   (30-60s Latin track, ≤5MB)"
	@echo "  demo/clips/01_clip.mp4          (6-8 dance clips, 720p, ≤8MB each)"
	@echo ""
	@if [ -f demo/audio/sample_bachata.mp3 ]; then \
		echo "  ✓ Audio found"; \
	else \
		echo "  ✗ Audio missing — add demo/audio/sample_bachata.mp3"; \
	fi
	@clip_count=$$(ls demo/clips/*.mp4 2>/dev/null | wc -l | tr -d ' '); \
	if [ "$$clip_count" -gt 0 ]; then \
		echo "  ✓ $$clip_count clip(s) found"; \
	else \
		echo "  ✗ No clips — add MP4 files to demo/clips/"; \
	fi
	@echo ""

install:
	[ -d $(VENV) ] || uv venv $(VENV) --python 3.13
	uv pip install -p $(VENV) -r requirements.txt
	uv pip install -p $(VENV) ruff pytest mypy

run:
	$(BIN)/python main.py --audio "$(AUDIO)" --video-dir "$(VIDEO_DIR)" $(EXTRA_FLAGS)

run-shorts:
	$(BIN)/python -m src.shorts_maker --audio "$(AUDIO)" --video-dir "$(VIDEO_DIR)" --count $(SHORTS_COUNT) --duration "$(SHORTS_DURATION)" $(EXTRA_FLAGS)

full-pipeline:
	$(BIN)/python -m src.pipeline --audio "$(AUDIO)" --video-dir "$(VIDEO_DIR)" --output-dir "$(OUTPUT_DIR)" --shorts-count $(SHORTS_COUNT) --shorts-duration "$(SHORTS_DURATION)" $(EXTRA_FLAGS)

mcp-serve:
	$(BIN)/python mcp_server.py

test:
	$(BIN)/pytest

lint:
	$(BIN)/ruff check src/ tests/

lint-fix:
	$(BIN)/ruff check --fix src/ tests/

format:
	$(BIN)/ruff format src/ tests/
	$(BIN)/ruff check --select I --fix src/ tests/

check-types:
	$(BIN)/mypy src/ tests/

refactor: format lint-fix check-types test
	@echo ""
	@echo "✓ Refactor workflow complete:"
	@echo "  ✓ Code formatted with ruff"
	@echo "  ✓ Linting issues auto-fixed"
	@echo "  ✓ Type checking passed"
	@echo "  ✓ All tests passed"
	@echo ""
	@echo "Ready to commit! Code aligns with:"
	@echo "  • Python style (PEP 8 via ruff)"
	@echo "  • Linting rules (ruff)"
	@echo "  • Type safety (mypy)"
	@echo "  • Test coverage"
	@echo ""

clean:
	rm -rf $(VENV)
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	rm -f *.mp4