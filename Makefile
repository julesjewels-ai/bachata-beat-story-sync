PYTHON = python3.13
VENV = venv
BIN = $(VENV)/bin
TEST_MODE ?=
MAX_CLIPS ?=
MAX_DURATION ?=

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

.PHONY: install run test clean

install:
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -r requirements.txt

run:
	$(BIN)/python main.py --audio "$(AUDIO)" --video-dir "$(VIDEO_DIR)" $(EXTRA_FLAGS)

test:
	$(BIN)/pytest

clean:
	rm -rf $(VENV)
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -f *.mp4