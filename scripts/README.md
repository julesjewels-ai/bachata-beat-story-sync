# Benchmarking Suite

This directory contains benchmarking tools for validating the performance claims of Bachata Beat-Story Sync.

## Overview

The marketing claim: **"A 4-hour Final Cut Pro project takes 4 minutes here"**

This benchmarking suite measures:
- **Planning time**: Dry-run analysis (audio analysis, video scanning, segment planning)
- **Rendering time**: Full video render via FFmpeg
- **Speedup ratio**: Estimated manual editing time vs. automated time

## Scripts

### `benchmark.py`

Main benchmarking script. Runs the tool and times execution.

**Features:**
- Measures dry-run (planning) and full render times separately
- Supports multiple runs with min/min/max statistics
- Estimates manual editing time (default: 3 min per cut, industry baseline)
- Calculates speedup ratio
- Outputs to terminal (Rich tables or plain text)
- Supports JSON and CSV export for further analysis
- Test mode for quick validation
- Graceful error handling

**Basic Usage:**

```bash
# Single run
python scripts/benchmark.py --audio track.wav --video-dir clips/

# Multiple runs with statistics
python scripts/benchmark.py --audio track.wav --video-dir clips/ --runs 3

# Test mode (quick validation)
python scripts/benchmark.py --audio track.wav --video-dir clips/ --test-mode

# Full output with exports
python scripts/benchmark.py --audio track.wav --video-dir clips/ --runs 3 \
  --output-json results.json --output-csv results.csv

# Verbose logging for debugging
python scripts/benchmark.py --audio track.wav --video-dir clips/ --verbose
```

**Arguments:**

| Argument | Default | Description |
|----------|---------|-------------|
| `--audio` | *required* | Path to input .wav audio file |
| `--video-dir` | *required* | Directory containing .mp4 video clips |
| `--runs N` | 1 | Run the benchmark N times (for statistics) |
| `--test-mode` | false | Use test mode (4 clips, 10s max duration) |
| `--output FILE` | `benchmark_output.mp4` | Output video path for each run |
| `--output-json FILE` | none | Save detailed results to JSON |
| `--output-csv FILE` | none | Save summary stats to CSV |
| `--manual-estimate-per-cut MIN` | 3.0 | Minutes per cut for manual estimate |
| `--verbose` | false | Enable verbose logging |

**Output Example:**

```
======================================================================
BENCHMARK SUMMARY
======================================================================

Execution Times:
  Dry-run (plan):   8.45s (min: 8.23s, max: 8.67s)
  Full render:      145.32s (min: 142.10s, max: 148.50s)
  Total:            153.77s (min: 150.33s, max: 157.17s)

Manual Edit Estimate vs. Automated:
  Est. manual time: 45.0 minutes
  Automated time:   2.6 minutes
  Speedup ratio:    17.4x (min: 16.8x, max: 18.1x)

Video Statistics:
  Output duration:  60.0s
  Segments planned: 18
  Clips used:       18
  Successful renders: 3/3

======================================================================
```

### `benchmark_report.py`

Generates a marketing-ready HTML report from benchmark JSON output.

**Features:**
- Beautiful, responsive HTML design (no JS dependencies)
- Prominent speedup ratio display
- Bar chart comparing manual vs. automated time
- Mobile-friendly responsive layout
- Ready to screenshot for presentations

**Usage:**

```bash
# Generate report from benchmark results
python scripts/benchmark.py --audio track.wav --video-dir clips/ \
  --runs 3 --output-json results.json

python scripts/benchmark_report.py results.json

# Specify output file
python scripts/benchmark_report.py results.json -o my_report.html

# Customize chart dimensions
python scripts/benchmark_report.py results.json -o report.html --width 1000 --height 500
```

**Arguments:**

| Argument | Default | Description |
|----------|---------|-------------|
| `input_json` | *required* | Path to benchmark JSON file |
| `-o, --output FILE` | `report.html` (or derived) | Output HTML file |
| `--width PX` | 800 | Chart width in pixels |
| `--height PX` | 400 | Chart height in pixels |

**Output:**

An HTML file with:
- Header with project name
- Large speedup ratio display (e.g., "37x")
- Bar chart showing manual vs. automated time
- Statistics grid (duration, clips, segments, etc.)
- Methodology footer explaining the calculation

Perfect for:
- Marketing presentations
- Screenshots for social media
- Email reports
- Website case studies

## Methodology

### Manual Editing Time Estimate

**Industry baseline: 3 minutes per beat-sync cut**

This is a conservative estimate for professional beat-synced video editing:
- Each cut requires: selecting the right clip, trimming to beat, adding transition, color grading
- For a 60-second output video with ~15-20 clips (one cut every 3-4 seconds), this is **45-60 minutes** of manual work
- Factor in review, revisions, and final polish: **60+ minutes** typical

Default formula:
```
estimated_cuts ≈ output_duration_seconds / 4
manual_time_minutes = estimated_cuts × 3
```

### Execution Timing

The benchmark measures:

1. **Dry-run time**: `--dry-run` flag
   - Audio analysis (BPM detection, beat tracking)
   - Video scanning and intensity scoring
   - Segment planning (which clips go where)
   - No video rendering

2. **Full render time**: Complete rendering
   - All of the above, plus:
   - FFmpeg clip extraction
   - Video concatenation
   - Transition rendering
   - Final file encoding

3. **Total time**: dry_run_time + full_render_time

### Speedup Ratio

```
speedup = (manual_estimate_minutes × 60 seconds) / total_time_seconds
```

A 3x speedup means the tool is **3 times faster** than manual editing.

## Examples

### Quick Validation Run

```bash
# Test mode: 4 clips, 10s max duration
python scripts/benchmark.py --audio test.wav --video-dir test_clips/ --test-mode
```

Output: ~20-30 seconds total (useful for verifying setup works)

### Production Benchmark

```bash
# Run 3 times for statistics
python scripts/benchmark.py --audio soundtrack.wav --video-dir all_clips/ \
  --runs 3 \
  --output-json results.json \
  --output-csv results.csv

# Generate marketing report
python scripts/benchmark_report.py results.json -o speedup_report.html

# Take screenshot of report.html for social media
```

Expected output: ~5-15 minutes depending on:
- Number of video clips
- Total audio duration
- Machine specs (CPU, disk speed)

### Different Manual Estimate

```bash
# If your editing standard is 4 min per cut (tighter estimate)
python scripts/benchmark.py --audio track.wav --video-dir clips/ \
  --runs 5 \
  --manual-estimate-per-cut 4.0
```

## Caveats & Notes

1. **Startup overhead**: Each run includes Python interpreter startup time (~1-2s)
   - For very fast operations, startup dominates; benchmark longer outputs for meaningful ratios

2. **System variability**: Times will vary based on:
   - CPU/GPU speed
   - Disk I/O (SSD vs HDD)
   - Background processes
   - Number and duration of clips

3. **Manual estimate is conservative**:
   - 3 min per cut is a **lower bound** for professional work
   - Actual FCP project might take 4-8 hours for a 1-minute video
   - Higher manual estimates = higher speedup ratios

4. **Full vs. Dry-run**:
   - Dry-run measures *planning* speed (algorithmic complexity)
   - Full render measures *total end-to-end* speed (what users care about)

## Integration with CI/CD

Example GitHub Actions workflow:

```yaml
name: Performance Benchmark

on:
  push:
    branches: [main]

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.13'
      - run: make install
      - run: python scripts/benchmark.py --audio test_audio.wav --video-dir test_clips/ --output-json results.json
      - uses: actions/upload-artifact@v2
        with:
          name: benchmark-results
          path: results.json
```

## Troubleshooting

### "No .mp4 files found"
Check that `--video-dir` contains `.mp4` files (not nested in subdirectories, unless you use `**/*.mp4` pattern).

### Process timeout
If benchmarks exceed 10 minutes, the process will time out. This is a safety limit; adjust in code if needed.

### Memory issues
For very large clip libraries, the video scanning phase may consume significant memory. Use `--test-mode` to validate first.

### FFmpeg not available
The script calls `ffprobe` to measure output duration. Install ffmpeg:
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg

# Windows
choco install ffmpeg
```

## Files

- `benchmark.py` - Main benchmarking script
- `benchmark_report.py` - HTML report generator
- `README.md` - This file
