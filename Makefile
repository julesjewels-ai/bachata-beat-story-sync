PYTHON = python3.13
VENV = venv
BIN = $(VENV)/bin
TEST_MODE ?=
MAX_CLIPS ?=
MAX_DURATION ?=
VIDEO_STYLE ?=
AUDIO_OVERLAY ?=
AUDIO_OVERLAY_OPACITY ?=

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

ifneq ($(VIDEO_STYLE),)
  EXTRA_FLAGS += --video-style $(VIDEO_STYLE)
endif

ifneq ($(AUDIO_OVERLAY),)
  EXTRA_FLAGS += --audio-overlay $(AUDIO_OVERLAY)
endif

ifneq ($(AUDIO_OVERLAY_OPACITY),)
  EXTRA_FLAGS += --audio-overlay-opacity $(AUDIO_OVERLAY_OPACITY)
endif

.PHONY: install run test lint format check-types clean

install:
	[ -d $(VENV) ] || uv venv $(VENV) --python 3.13
	uv pip install -p $(VENV) -r requirements.txt
	uv pip install -p $(VENV) ruff pytest mypy

run:
	$(BIN)/python main.py --audio "$(AUDIO)" --video-dir "$(VIDEO_DIR)" $(EXTRA_FLAGS)

test:
	$(BIN)/pytest

lint:
	$(BIN)/ruff check src/ tests/

format:
	$(BIN)/ruff format src/ tests/
	$(BIN)/ruff check --select I --fix src/ tests/

check-types:
	$(BIN)/mypy src/ tests/

clean:
	rm -rf $(VENV)
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	rm -f *.mp4