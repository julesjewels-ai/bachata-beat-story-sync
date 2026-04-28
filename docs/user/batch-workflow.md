# Batch Workflow — Bachata Beat-Story Sync

This repo now participates in the batch pipeline from lyric generation to video render.

## What It Accepts

- one batch JSON file from the lyric pipeline
- one or many songs in that batch
- an audio asset path for each song
- a clip directory for each render

## Run MCP Server

```bash
cd /Users/tutorsam/Documents/Business/YouTube/01_BBB/_software/bachata-beat-story-sync
./venv/bin/python mcp_server.py
```

## Batch Tools

The MCP server exposes these batch-aware tools:

- `load_batch`
- `save_batch`
- `plan_batch_song`
- `render_batch_song`

## Flow

1. Create or load the batch JSON in the lyric pipeline.
2. Generate and validate lyrics.
3. Add audio asset paths.
4. Point `video_dir` at the clip library.
5. Render each song with `render_batch_song`.

## Stop Points

The render step stops early if:

- the batch has no audio path
- the clip directory is missing
- FFmpeg cannot build the output

That is intentional. It keeps the manual audio and clip steps visible.

## Recommended Local Setup

- keep the lyric pipeline and video repo in separate folders
- pass the video repo path through `BACHATA_SYNC_REPO` when needed
- keep batch JSON paths relative to the batch directory

