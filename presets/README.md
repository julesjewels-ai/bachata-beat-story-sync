# Bachata Beat Story Sync — Community Preset Library

Welcome to the community preset library! This directory contains genre and style presets that tune the montage engine for different music and dance styles.

## What is a Preset?

A preset is a YAML file that overrides `PacingConfig` settings to give you great results with a single flag. Instead of manually tweaking 40+ pacing parameters, you can now just say:

```bash
make run AUDIO=track.wav VIDEO_DIR=clips/ --genre k_pop
```

And get optimized K-pop cutting, speed ramping, color grading, transitions, and visual effects all at once.

## Built-in Presets

The project includes these built-in genre presets (defined in `src/core/genre_presets.py`):

| Genre | Pacing | Speed Ramps | Style | Transitions | Best For |
|-------|--------|-------------|-------|-------------|----------|
| **bachata** | Medium (2.5s/4s/6s) | Gentle (1.2/1.0/0.9) | Golden | Fade (0.5s) | Latin romantic, sensual movement |
| **salsa** | Fast (1.8s/2.8s/4s) | Energetic (1.4/1.1/1.0) | Warm | Wipe Left (0.3s) | High-energy Latin, quick cuts |
| **reggaeton** | Medium-Fast (2.2s/3.5s/5s) | Punchy (1.3/1.0/0.85) | Cool | Fade (0.4s) | Urban, modern dance, hip-hop style |
| **kizomba** | Slow (3.5s/5s/7s) | Minimal (1.0/0.9/0.7) | Vintage | Fade (0.8s) | Intimate, graceful, slow grinding |
| **merengue** | Very Fast (1.5s/2.5s/3.5s) | Very Energetic (1.5/1.2/1.0) | Warm | None (hard cuts) | Frenetic, rapid movement |
| **pop** | Medium (2.5s/3.5s/5s) | Standard (1.1/1.0/0.95) | None | Fade (0.5s) | Mainstream pop, generic music |

## Community Presets

Community presets are stored in `presets/community/` and are contributed by creators like you. Some examples:

- `example_k_pop.yaml` — K-pop style (fast cuts, high energy, cool tones)
- `example_ballroom.yaml` — Ballroom dance (graceful, longer clips, warm tones)

## Using a Community Preset

### Option 1: Using the CLI flag (coming soon)

Once we add support for community presets in the CLI, you'll be able to use them like:

```bash
# Load a community preset by name
make run AUDIO=track.wav VIDEO_DIR=clips/ --genre k_pop

# Or specify a path directly
make run AUDIO=track.wav VIDEO_DIR=clips/ --genre-path presets/community/k_pop.yaml
```

### Option 2: Manual YAML override

For now, you can copy the preset into your `montage_config.yaml`:

1. Open `montage_config.yaml` at the project root
2. Copy the values from the community preset into the `pacing:` section
3. Run normally: `make run AUDIO=track.wav VIDEO_DIR=clips/`

## Preset Format

All presets follow the same structure. See `presets/template.yaml` for a fully commented template with every field explained.

Key sections:
- **Clip Duration** — how long clips last per intensity level
- **Speed Ramping** — playback speed per intensity (fast for high-energy, slow for dreamy)
- **Video Style** — color grading (warm, cool, vintage, golden, black & white, none)
- **Transitions** — cut type (fade, wipe, hard cut, etc.)
- **Visual Effects** — intro effects, pacing effects, beat-synced elements
- **Audio Overlay** — optional waveform or frequency-bar visualizer
- **Section Detection** — how the montage responds to song structure

## Creating Your Own Preset

See `CONTRIBUTING.md` for a step-by-step guide to create and submit a new preset.

Quick version:

1. Copy `presets/template.yaml` to `presets/community/my_genre.yaml`
2. Read the comments and adjust values for your genre
3. Test locally: `make run AUDIO=track.wav VIDEO_DIR=clips/ --genre-path presets/community/my_genre.yaml`
4. Submit a PR with your preset

## Preset Ideas

Some genres/styles that would make great presets:

- **K-pop** — fast, synchronized cuts; cool color grade; dynamic transitions
- **Brazilian Funk (Favela Funk)** — punchy, minimal clips; bright colors; wipe transitions
- **Ballroom** — long, graceful clips; warm color; smooth fades; organic speed curves
- **Afrobeats** — medium pacing; warm/golden tones; groove-synced speed; head-lock rhythm
- **Tango** — dramatic, staccato cuts; black & white; vignette intro; vintage mood
- **Hip-Hop** — sharp, snappy clips; cool or neutral color; hard cuts or quick wipes
- **Country Line Dance** — rhythmic, stepping-synced; warm/golden; no fancy effects
- **EDM/Rave** — ultrafast cuts; heavy effects (jitters, light leaks); cool color
- **Waltz** — flowing, longer clips; graceful transitions; romantic color grade
- **Flamenco** — sharp, dramatic cuts; warm/golden; staccato effect; passion and fire

## FAQ

**Q: Can I use multiple presets together?**
A: Not yet. Load one preset into your `montage_config.yaml`. Future versions may support layering.

**Q: What if my preset looks bad?**
A: Start with a similar built-in preset and tweak one or two values at a time. Test frequently. See the `CONTRIBUTING.md` testing guide for tips.

**Q: Can I override just one field from a preset?**
A: Yes! CLI flags always override preset values. For example:
```bash
# Use K-pop preset but force no transitions
make run AUDIO=track.wav VIDEO_DIR=clips/ --genre-path presets/community/k_pop.yaml --transition-type none
```

**Q: Can I submit a preset for a music style not listed?**
A: Absolutely! Open an issue or PR with your preset. We welcome all genres and dance styles.

## Resources

- **Template:** `presets/template.yaml` — all fields fully documented
- **Contributing:** `presets/CONTRIBUTING.md` — step-by-step submission guide
- **Source Code:** `src/core/genre_presets.py` — built-in presets and how they load
- **Config Model:** `src/core/models.py` → `PacingConfig` — all available fields

---

**Have an idea for a preset?** Please contribute! See `CONTRIBUTING.md` for details.
