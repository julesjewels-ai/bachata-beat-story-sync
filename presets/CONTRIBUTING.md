# Contributing a Preset to Bachata Beat Story Sync

Thanks for contributing to the community preset library! This guide walks you through creating, testing, and submitting your preset.

## Before You Start

- Have you tested the project locally? (`make install`, `make run`)
- Do you have some video clips and an audio file ready to test with?
- Familiar with YAML syntax? (It's just key-value pairs, indentation matters)

## Step 1: Plan Your Preset

Think about the music/dance style you're creating for:

- **Clip Pacing** — How long should clips last?
  - High energy: 1.5–2.5s (snappy, quick cuts)
  - Medium: 3.0–4.5s (standard, balanced)
  - Low energy: 5.0–8.0s (breathing room, slow)

- **Speed Ramping** — How should playback speed respond to intensity?
  - Energetic styles: high:1.2–1.4, medium:1.0, low:0.8–0.9
  - Graceful styles: high:1.0–1.1, medium:1.0, low:0.85–0.9
  - Very energetic: high:1.4+, medium:1.1, low:1.0

- **Color Grading** — Which visual style matches your genre?
  - `warm` (orange/gold) — energetic, cozy, inviting
  - `cool` (blue) — calm, ethereal, modern
  - `golden` — romantic, rich, cinematic
  - `vintage` — nostalgic, gritty, warm
  - `bw` (black & white) — dramatic, timeless, artistic
  - `none` — natural, ungraded

- **Transitions** — How should clips cut together?
  - `fade` — smooth, universal, safe (0.3–0.8s)
  - `wipeleft` / `wiperight` — dynamic, trendy (0.2–0.5s)
  - `slideup` / `slidedown` — fluid, less jarring (0.3–0.6s)
  - `none` — hard cuts, snappy, high-energy (0.0s)

- **Intro Effect** — Special effect for the first clip?
  - `bloom` — soft, glowing reveal (dreamy)
  - `vignette_breathe` — spotlight with pulse (dramatic)
  - `none` — hard cut (energetic)

## Step 2: Create Your Preset File

1. Copy the template:
   ```bash
   cp presets/template.yaml presets/community/YOUR_GENRE.yaml
   ```

2. Replace `YOUR_GENRE` with a lowercase, underscore-separated name:
   - Good: `k_pop.yaml`, `brazilian_funk.yaml`, `ballroom.yaml`
   - Avoid: `K-Pop.yaml`, `k-pop.yaml` (consistency matters)

3. Open the file and customize the values:
   ```yaml
   pacing:
     high_intensity_seconds: 2.0    # Quick cuts for K-pop
     medium_intensity_seconds: 3.0
     low_intensity_seconds: 4.5
     high_intensity_speed: 1.25     # Energetic speed
     medium_intensity_speed: 1.0
     low_intensity_speed: 0.9
     video_style: cool              # Modern K-pop aesthetic
     transition_type: wipeleft      # Trendy wipes
     transition_duration: 0.3       # Snappy transitions
     intro_effect: bloom            # Soft, stylish intro
   ```

4. Keep comments minimal — the template already has full documentation. Only add comments if your choice is unusual.

5. Only include fields you want to override. Omit the rest (project defaults will be used).

## Step 3: Test Your Preset

### Quick Test (Dry Run)

```bash
# Plan the montage without rendering (fast feedback)
make run AUDIO=path/to/track.wav VIDEO_DIR=path/to/clips/ \
  --genre-path presets/community/YOUR_GENRE.yaml --dry-run
```

This will:
- Analyze the audio and video
- Plan the montage
- Print decision logs (clips chosen, timing, reasoning)
- NOT render (no FFmpeg)

Review the logs. Does the clip selection make sense? Are clips the right length?

### Full Test

```bash
# Render the full montage
make run AUDIO=path/to/track.wav VIDEO_DIR=path/to/clips/ \
  --genre-path presets/community/YOUR_GENRE.yaml
```

This takes longer (FFmpeg rendering), but you'll get a real video (`output.mp4`).

### Testing Checklist

- [ ] Audio analysis completed (correct BPM detected?)
- [ ] Clips are the expected length for each intensity level
- [ ] Color grading matches the intended aesthetic
- [ ] Transitions feel natural and match the vibe
- [ ] Intro effect (if any) looks good
- [ ] Speed ramping feels right (fast sections snappy, slow sections smooth)
- [ ] Overall pacing matches the genre (too fast? too slow? too many short cuts?)
- [ ] Video quality is good (no artifacts from speed ramping or effects)

### Troubleshooting

**Clips are too short/long:**
- Adjust `high_intensity_seconds`, `medium_intensity_seconds`, `low_intensity_seconds`
- Check `high_intensity_threshold` and `low_intensity_threshold` (may need to reclassify clips)

**Speed ramping looks jerky:**
- Try `interpolation_method: blend` for smooth slow-motion
- Reduce `randomize_speed_ramps` (or disable)

**Color grading doesn't match:**
- Try a different `video_style`
- Ensure `video_style` is set in your preset, not using the default

**Transitions feel jarring:**
- Increase `transition_duration` (0.3s → 0.5s)
- Switch to `fade` for smoothness or `wipeleft` for dynamics

**Too much/too little B-roll:**
- Adjust `broll_interval_seconds` (lower = more B-roll)
- Set to 0 to disable B-roll

### Test with Multiple Tracks

If possible, test with several different audio files (different BPMs, genres, energy levels). Your preset should work across different music, not just one specific song.

## Step 4: Document Your Preset

At the top of your preset file, add a brief comment explaining the style:

```yaml
# K-Pop Preset
# Optimized for Korean pop and idol music: fast synchronised cuts,
# energetic speed ramping, cool modern color grade, trendy wipes.
# Works best with 100–140 BPM tracks.

pacing:
  ...
```

## Step 5: Submit Your Preset

### Option A: Direct PR (Recommended)

1. Fork the repository (if you haven't)
2. Create a new branch: `git checkout -b preset/your_genre`
3. Add your preset file: `presets/community/your_genre.yaml`
4. Commit:
   ```bash
   git add presets/community/your_genre.yaml
   git commit -m "Add K-pop preset"
   ```
5. Push and open a PR

### PR Title Format

Use this format for clarity:

```
Add [Genre] preset

Examples:
  Add K-pop preset
  Add Ballroom preset
  Add Brazilian Funk preset
```

### PR Description Template

Include in your PR description:

```markdown
## Preset: [Genre Name]

### Summary
Brief description of the style and what it's optimized for.

### Key Tunings
- Clip duration: 2.0s / 3.0s / 4.5s (high/medium/low)
- Speed ramping: 1.25x / 1.0x / 0.9x
- Color grade: cool
- Transitions: wipeleft (0.3s)

### Testing
Tested with:
- [Song title / Genre] at [BPM]
- [Song title / Genre] at [BPM]

All tests passed, clips feel natural, colors match the intended aesthetic.

### Notes
Any special considerations or inspirations for this preset?
```

### Option B: File an Issue

If you're unsure about opening a PR directly:

1. Open a GitHub issue: **"New preset idea: [Genre]"**
2. Paste your preset YAML in the issue
3. Describe the style and how to use it
4. A maintainer can review and integrate it

## Maintenance & Iteration

After your preset is merged:

- **Feedback?** We may ask you to refine values or test on other tracks
- **Bug fixes?** Feel free to open follow-up PRs
- **Questions?** Open an issue or reach out in discussions

## Preset Naming Conventions

To keep the library organized:

- Use **lowercase with underscores**: `k_pop.yaml`, `brazilian_funk.yaml`
- **Avoid numbers** unless they're essential (e.g., `house_80s.yaml`)
- **Be specific**: `salsa` (already built-in), so try `salsa_timba.yaml` or `caribbean_salsa.yaml`
- **One preset per file**

## FAQ

**Q: Can I submit a preset for music I didn't create?**
A: Yes! The library is for any music genre, regardless of origin. Just be respectful and accurate.

**Q: What if my preset overlaps with a built-in one?**
A: That's fine! Community variants are welcome. You might create `bachata_fast.yaml` or `salsa_minimalist.yaml` to offer alternatives.

**Q: Do I need to test with a lot of videos?**
A: At least 2–3 different tracks. More is better, but it takes time. Focus on variety (different BPMs, energy levels).

**Q: What if the maintainer asks for changes?**
A: We'll work with you! Requests are usually small tweaks (e.g., "try 1.2x speed instead of 1.3x"). No big deal.

**Q: Can I update my preset after it's merged?**
A: Yes, just open a new PR with refinements.

---

**Thank you for contributing!** Your presets help the community create better videos. 🎬
