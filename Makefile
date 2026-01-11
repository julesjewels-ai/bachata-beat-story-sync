PYTHON = python3
VENV = venv
BIN = $(VENV)/bin

.PHONY: install run test clean

install:
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -r requirements.txt

run:
	$(BIN)/python main.py

test:
	$(BIN)/pytest

clean:
	rm -rf $(VENV)
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -f *.mp4