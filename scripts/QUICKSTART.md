# Benchmark Quickstart

Get started with benchmarking Bachata Beat-Story Sync in 5 minutes.

## Prerequisites

- Python 3.13+
- The main project installed (`make install`)
- Audio file (WAV format)
- Folder with MP4 video clips

## 1. Quick Test (30 seconds)

Validate your setup works:

```bash
python scripts/benchmark.py --audio your_track.wav --video-dir your_clips/ --test-mode
```

Expected output: ~30 seconds, uses only 4 clips and 10s of audio.

## 2. Single Production Run (5-15 minutes)

Run one full benchmark:

```bash
python scripts/benchmark.py --audio your_track.wav --video-dir your_clips/ \
  --output-json results.json
```

This measures:
- Planning time (dry-run)
- Full rendering time
- Speedup ratio vs. manual editing

## 3. Generate Marketing Report (5 seconds)

Create an HTML report from results:

```bash
python scripts/benchmark_report.py results.json -o report.html
```

Open `report.html` in your browser and screenshot the speedup metric!

## 4. Multiple Runs for Statistics (Optional)

Run 3 times and get min/max/average:

```bash
python scripts/benchmark.py --audio your_track.wav --video-dir your_clips/ \
  --runs 3 \
  --output-json results.json \
  --output-csv results.csv
```

Both JSON and CSV exported for further analysis.

## Expected Speedup Numbers

For a ~60s montage with 15-20 video clips:
- **Manual editing**: 45-60 minutes (3 min/cut baseline)
- **Automated**: 2-5 minutes
- **Speedup**: **10-20x faster**

Your mileage will vary based on:
- Number of clips
- Total duration
- Your machine's CPU/disk speed

## Full Workflow

```bash
# 1. Single run with JSON output
python scripts/benchmark.py --audio track.wav --video-dir clips/ --output-json results.json

# 2. Generate HTML report
python scripts/benchmark_report.py results.json -o speedup_report.html

# 3. Open in browser and screenshot
# Copy report.html to your marketing materials
```

## Customization

### Different Manual Estimate

If your baseline is higher (e.g., 4 min per cut):

```bash
python scripts/benchmark.py --audio track.wav --video-dir clips/ \
  --manual-estimate-per-cut 4.0 \
  --output-json results.json
```

### Different Output Video Name

```bash
python scripts/benchmark.py --audio track.wav --video-dir clips/ \
  --output my_benchmark_output.mp4
```

### Verbose Logging

See all the details:

```bash
python scripts/benchmark.py --audio track.wav --video-dir clips/ --verbose
```

## Output Files

| File | Purpose |
|------|---------|
| `results.json` | Detailed metrics (all runs + summary) |
| `results.csv` | Summary statistics only |
| `report.html` | Marketing-ready visual report |

## Common Issues

**"No .mp4 files found"**
- Check `--video-dir` contains .mp4 files at the top level
- Subdirectories are searched recursively, so nesting should be fine

**Process timeout**
- Increase the timeout in `benchmark.py` if your renders take >10 min
- Or use `--test-mode` to validate first

**Memory issues with large clip library**
- Use `--test-mode` first to validate
- Or reduce number of clips in the directory

## Tips for Marketing

1. **Run multiple times** (`--runs 3+`) for more credible statistics
2. **Use realistic data**: Include typical audio length and number of clips from actual projects
3. **Screenshot HTML report**: The visual format is cleaner than terminal tables
4. **Note the methodology**: Mention "3 min per cut" baseline in your marketing materials
5. **Be conservative**: Assume manual estimate might be higher (4-5 min per cut)

Example claim with data:

> We benchmarked a 60-second montage with 18 video clips:
> - **Manual editing**: ~45 minutes (3 min per beat-sync cut)
> - **Bachata Sync**: ~2.5 minutes
> - **Result**: **18x faster**

## Next Steps

See `README.md` for:
- Detailed methodology
- Complete argument reference
- Integration with CI/CD
- Troubleshooting guide
