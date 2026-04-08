# Demo Assets

This directory contains sample assets for the demo mode.

## Structure

```
demo/
├── audio/
│   └── sample_bachata.mp3    # 30–60s royalty-free bachata track
├── clips/
│   ├── 01_clip.mp4           # 5–10s dance clips, 720p
│   ├── 02_clip.mp4
│   ├── ...
│   └── 08_clip.mp4
└── README.md
```

## Fetching Assets

Run `make download-demo` to fetch the demo assets from the release archive.

Assets are **not** committed to git — they are hosted externally and downloaded on first use.

## Sourcing New Assets

- **Audio:** [Pixabay Music](https://pixabay.com/music/), [Free Music Archive](https://freemusicarchive.org/)
- **Video:** [Pexels Videos](https://www.pexels.com/videos/), [Pixabay Videos](https://pixabay.com/videos/), [Mixkit](https://mixkit.co/)
- Search: "bachata dance", "latin dance", "couple dancing"
- Format: MP4, 720p, ≤8MB each
