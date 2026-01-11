# Bachata Beat-Story Sync

An automated video editing tool that analyzes .wav Bachata tracks to detect rhythm, breaks, and emotional peaks, then intelligently syncs these audio segments with a library of .mp4 video clips. It uses AI to match the visual narrative intensity with the musical dynamics to construct a cohesive viewer story.

## Tech Stack

- Python
- Librosa
- OpenCV
- MoviePy
- TensorFlow/PyTorch
- Gemini 3 Pro (Multimodal)

## Features

- Audio Beat & Onset Detection
- Sentiment-based Clip Matching
- Automated Video Montage Generation
- Rhythmic Transition Syncing
- Narrative Arc Construction

## Quick Start

```bash
# Clone and setup
git clone <repo-url>
cd bachata-beat-story-sync
make install

# Run the application
make run
```

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
make install && make run
```

## Development

```bash
make install  # Create venv and install dependencies
make run      # Run the application
make test     # Run tests
make clean    # Remove cache files
```

## Testing

```bash
pytest tests/ -v
```
