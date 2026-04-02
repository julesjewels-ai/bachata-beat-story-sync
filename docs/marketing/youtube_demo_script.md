# YouTube Demo Script: Bachata Beat-Story Sync
**Working Title:** "Beat-Synced in Seconds — Auto-Edit Your Dance Videos with One Command"
**Target Length:** 7–9 minutes
**Tone:** Confident, approachable, demo-led
**Audience:** Dance studio videographers and event photographers (technical-ish)

---

## PRE-PRODUCTION NOTES

- Record terminal in a large, readable font (e.g. Warp or iTerm2, 20pt minimum, dark theme)
- Have the finished demo montage rendered and ready — it plays as the very first thing viewers see
- Use a real bachata track (3–4 minutes, with clear peaks and breaks)
- Have 10–15 source clips ready in a folder called `bachata_clips/`
- Record the tool run in real-time — do not fake or speed-cut the terminal; the realness sells it
- Final output video should be 1920×1080, ~90 seconds, golden color grade, vignette intro, fade transitions
- Screen layout suggestion: terminal left 60%, rendered output clips right 40% when showing side-by-side

---

## SECTION 1 — HOOK (0:00–0:15)

### [SCREEN]
Cut straight to the finished montage. No title card. No intro music. Just the beat-synced video playing at full volume, full screen.

The montage shows:
- A warm golden-graded bachata couple — vignette spotlight opens on the first beat
- Hard cuts synced to every 2–3 beats during the high-energy chorus
- A smooth fade transition at the section break (mid-track)
- Slow-motion pull-back at a low-energy moment
- Fast 1.2x-speed sequence during the climax
- The last cut lands exactly on the final drum hit

Let it play for 12–13 seconds. No voice. Music only.

### [VOICEOVER — starts at 0:13, over the last 2 seconds of the montage]
"That video took one command and about four minutes to render."

---

## SECTION 2 — PROBLEM (0:15–1:00)

### [SCREEN]
Cut to a split-screen. Left side: a timeline in a generic NLE (CapCut or DaVinci Resolve) — dozens of clips, manual beat markers, messy edits. Right side: a folder of raw video files (30 clips, unnamed, various lengths).

### [VOICEOVER]
"Here's what this normally looks like. You've got 30 clips from a bachata social, a track you want to use, and you're sitting there scrubbing through footage, eyeballing where the chorus hits, nudging cuts by hand.

You drag a clip. The cut's two frames early. The energy feels wrong. You try another clip. Still not quite right.

Forty-five minutes later, you've got a rough two-minute video and you still haven't touched the color grade.

And if your client needs three different versions — a full recap, a highlight reel, and a Shorts for Instagram — you're looking at half a day. Every. Single. Time.

There has to be a better way."

### [SCREEN]
Fade the NLE out. Hold on the folder of raw clips for a beat. Then cut to a clean terminal window.

---

## SECTION 3 — TOOL INTRO (1:00–1:30)

### [SCREEN]
Terminal window, empty prompt. The repo folder is the working directory. Show `ls` briefly — the viewer sees `main.py`, `montage_config.yaml`, `src/`, `bachata_clips/`.

### [VOICEOVER]
"This is Bachata Beat-Story Sync — a command-line tool that analyses your music, analyses your footage, and automatically assembles a beat-synced dance montage.

It uses librosa to map every beat and every intensity peak in your audio, and OpenCV to score the visual motion in each of your clips. Then it matches them — high-energy footage to high-energy music, slow moments to low-energy breaks — and renders the whole thing with FFmpeg.

Here's the command."

### [SCREEN]
Type the following command slowly and deliberately. Do not hit Enter yet.

```
python main.py --audio tracks/bachata_session.wav --video-dir bachata_clips/
```

Pause for 2 seconds with the cursor blinking after the command is typed.

### [VOICEOVER]
"That's it. Let's run it."

### [SCREEN]
Hit Enter.

---

## SECTION 4 — LIVE DEMO WALKTHROUGH (1:30–5:00)

### [SCREEN — Audio Analysis Phase, 1:30–2:10]
The terminal starts outputting. Show the Rich-formatted progress output in real time. Highlight these lines as they appear (use a cursor or zoom in):

```
 Analysing audio: tracks/bachata_session.wav
 ─────────────────────────────────────────────────────
  BPM detected        132.4
  Duration            3m 47s
  Beats found         299
  Peaks detected      18
  Sections detected   6
    [0:00–0:32]  intro        intensity 0.28
    [0:32–1:04]  buildup      intensity 0.51
    [1:04–2:08]  high_energy  intensity 0.81
    [2:08–2:24]  breakdown    intensity 0.31
    [2:24–3:12]  high_energy  intensity 0.79
    [3:12–3:47]  outro        intensity 0.22
```

### [VOICEOVER]
"First, it analyses the audio. Librosa gives us the BPM — 132 beats per minute here, that's a mid-tempo bachata — and it maps every single beat down to the millisecond.

Then it breaks the track into musical sections using the intensity envelope. You can see it's found six sections: an intro, a buildup, two high-energy choruses, a breakdown in the middle, and an outro.

Every cut the tool makes will be aware of where we are in the track."

---

### [SCREEN — Video Analysis Phase, 2:10–2:50]
The terminal scrolls to show video analysis output. Show a few representative lines:

```
 Scanning video library: bachata_clips/  (14 clips)
 ─────────────────────────────────────────────────────
  clip_01_social_floor.mp4    duration 0:42  intensity 0.82  scene_changes 4
  clip_02_close_couple.mp4    duration 0:28  intensity 0.44  scene_changes 1
  clip_03_spinning_group.mp4  duration 0:35  intensity 0.91  scene_changes 6
  clip_04_footwork_solo.mp4   duration 0:19  intensity 0.73  scene_changes 3
  clip_05_slow_embrace.mp4    duration 0:31  intensity 0.21  scene_changes 0
  ...  (14 clips total)
```

### [VOICEOVER]
"Now it scans every clip in your folder using OpenCV. For each one it calculates a visual intensity score — that's a 0-to-1 measure of how much motion is happening in the frame — and it counts scene changes.

The spinning group clip scores 0.91. The slow embrace scores 0.21. These aren't random labels — they're frame-by-frame optical flow measurements.

Now the engine knows what it has to work with on both sides."

---

### [SCREEN — Segment Planning Phase, 2:50–3:30]
The terminal shows the segment plan being built. Show a selection of lines from the planning log:

```
 Building segment plan...
 ─────────────────────────────────────────────────────
  t=0:00  [intro]       clip_05_slow_embrace.mp4    6.0s   0.7x speed  low
  t=0:06  [intro]       clip_02_close_couple.mp4    5.1s   0.9x speed  low
  t=0:11  [buildup]     clip_04_footwork_solo.mp4   3.8s   1.0x speed  medium
  t=0:15  [buildup]     clip_01_social_floor.mp4    4.0s   1.0x speed  medium
  t=0:19  [high_energy] clip_03_spinning_group.mp4  2.5s   1.2x speed  high
  t=0:21  [high_energy] clip_01_social_floor.mp4    2.5s   1.2x speed  high
  t=0:24  [high_energy] clip_04_footwork_solo.mp4   1.9s   1.2x speed  high
  ...
  37 segments planned  /  total 3m 42s
```

### [VOICEOVER]
"Here's the plan coming together. At zero seconds, during the intro, it picks the slow-embrace clip — low intensity, matched. It runs it at 0.7 times speed for that dreamy, unhurried feel.

When the buildup hits, it switches to footwork — more motion, back to normal speed.

Then the chorus kicks in: spinning group, social floor, footwork — all high-intensity clips, all running at 1.2 times speed, each clip lasting just two to two-and-a-half seconds so the cuts feel rapid and energetic.

Thirty-seven segments. It planned the whole thing in under a second."

---

### [SCREEN — FFmpeg Render Phase, 3:30–4:20]
Show the render progress bar. Rich progress with segment counter and estimated time:

```
 Rendering  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  37/37 segments
 Applying transitions (fade, 0.5s at section boundaries)
 Overlaying audio: tracks/bachata_session.wav
 Writing output: output/bachata_session_montage.mp4

 Done in 3m 51s
 Output: output/bachata_session_montage.mp4   (1920×1080, 3m 42s)
```

### [VOICEOVER]
"Then FFmpeg takes over. It extracts each segment, applies the speed ramps, stitches the fade transitions at the section boundaries, drops the audio on top, and writes the final file.

Three minutes and fifty-one seconds for a nearly four-minute video. On a single machine, no cloud, no subscription."

---

### [SCREEN — Playback of Result, 4:20–5:00]
Play the finished output video at full screen. Let 35–40 seconds of it run — the opening vignette, the first chorus of rapid cuts, the fade transition into the breakdown.

### [VOICEOVER]
"And that's the output. Same video you saw at the start. One command, one render pass."

---

## SECTION 5 — FEATURE HIGHLIGHTS (5:00–7:15)

### [SCREEN]
Return to the terminal. Keep the font large. Switch quickly between terminal and short video clips to illustrate each feature as you explain it.

---

### Feature 1: Genre Presets (5:00–5:35)

### [SCREEN]
Show the command with the `--genre` flag:

```
python main.py --audio tracks/salsa_track.wav --video-dir salsa_clips/ --genre salsa
```

Then show a snippet of the resulting video — faster cuts (1.8s high-intensity), wipeleft transitions, warm color grade.

### [VOICEOVER]
"The tool ships with genre presets. Pass `--genre salsa` and the pacing changes automatically: cuts get tighter — 1.8 seconds on high-intensity clips instead of 2.5 — the speed ramp goes to 1.4 times, transitions switch to a wipe, and the color grade shifts to warm.

There are presets for bachata, salsa, reggaeton, kizomba, merengue, and pop. Each one is a tuned set of defaults — and you can still override any individual value on top of them."

---

### Feature 2: Dry-Run Planning Mode (5:35–6:05)

### [SCREEN]
Show the command with `--dry-run`:

```
python main.py --audio tracks/bachata_session.wav --video-dir bachata_clips/ --dry-run
```

Then show the Markdown plan file that gets written — a clean table of segments, timings, clip paths, intensity levels, no video rendered.

### [VOICEOVER]
"Before you commit to a full render, use `--dry-run`. The tool does all the analysis and planning, but skips FFmpeg entirely. It writes a Markdown report — every segment, every timing, every clip choice — so you can review the plan and tweak the config before you spend four minutes rendering.

If a clip is being overused, or the pacing feels wrong in the breakdown section, you catch it here, not after the render."

---

### Feature 3: Decision Explainability (6:05–6:30)

### [SCREEN]
Show the `--explain` flag:

```
python main.py --audio tracks/bachata_session.wav --video-dir bachata_clips/ --explain
```

Then briefly show the explain log — a Markdown file with per-segment reasoning:

```markdown
## t=0:19 — high_energy segment

**Clip chosen:** clip_03_spinning_group.mp4
**Reason:** Highest intensity clip in library (0.91) matched to high_energy section
(avg intensity 0.81). Snap-to-beat adjusted duration from 2.4s → 2.5s (nearest
beat boundary at 132.4 BPM).
```

### [VOICEOVER]
"Add `--explain` and the tool writes a decision log alongside the video. Every segment, it tells you which clip it picked, why, what intensity score it matched against, and whether beat-snapping adjusted the duration.

If a client asks why a certain clip appeared — or didn't — you have the answer in a text file."

---

### Feature 4: YouTube Shorts Batch (6:30–7:00)

### [SCREEN]
Show the Makefile command:

```
make run-shorts AUDIO=tracks/bachata_session.wav VIDEO_DIR=bachata_clips/
```

Then briefly show two or three 9:16 vertical clips in a file explorer — `shorts_seed_A.mp4`, `shorts_seed_B.mp4`, `shorts_seed_C.mp4`.

### [VOICEOVER]
"Need vertical content? `make run-shorts` generates a batch of 60-second YouTube Shorts from the same clips and audio. Each one uses a different seed so the clip selection and timing vary — same track, three different edits, ready to schedule across the week.

They're already cropped to 9:16. You drop them in YouTube Studio and you're done."

---

### Feature 5: Full Pipeline (7:00–7:15)

### [SCREEN]
Briefly show the full-pipeline command:

```
make full-pipeline AUDIO=tracks/ VIDEO_DIR=bachata_clips/
```

Then show a file output listing — `mix.wav`, `mix_montage.mp4`, `track_01_montage.mp4`, `track_02_montage.mp4`, `shorts/` folder.

### [VOICEOVER]
"Point it at a folder of audio tracks and `make full-pipeline` does everything in one pass: it mixes the tracks with BPM-matched crossfades, generates a combined mix video, a separate highlight reel per track, and the full Shorts batch.

One command. A full content package."

---

## SECTION 6 — CALL TO ACTION (7:15–8:00)

### [SCREEN]
Return to a clean terminal. Cursor blinking at the prompt. After a moment, cut to a static title card with the repo URL and a QR code:

```
github.com/[your-repo-url]
```

Hold the card for 15 seconds. Keep the bachata track playing at low volume underneath.

### [VOICEOVER]
"The link to the repo is in the description. It runs on Python 3.13, installs in about two minutes with `make install`, and there's a full configuration guide in the docs folder.

If you're a dance studio videographer who's tired of the manual cut-and-sync loop, give it a shot. The default config — what you saw in this demo — is already dialed in for bachata. If you want salsa or reggaeton, one flag changes everything.

A few things I'd love your feedback on: are there genres or pacing styles missing that would fit your workflow? Are there features you'd want before you'd use this on a client project?

Drop a comment below. I read all of them. And if this saved you time on an actual edit, I really do want to hear about it.

See you in the next one."

### [SCREEN]
Hold the title card for 5 more seconds. Fade to black on the last beat of the track.

---

## POST-ROLL (End Screen, 8:00–8:20)

Standard YouTube end screen layout:
- Subscribe button (center)
- "Next video" card (right)
- "Playlist" card (left)

Suggested end-screen overlay text:
> "Try it free — link in description"

---

## PRODUCTION CHECKLIST

- [ ] Render the final demo montage first (it opens and closes the video)
- [ ] Record terminal session in real-time (no fakes — authenticity matters for this audience)
- [ ] Zoom into terminal output for each key log line — viewers on mobile need to read it
- [ ] Add subtle captions for all spoken voiceover (YouTube auto-captions often mangle technical terms like "librosa", "OpenCV", "xfade")
- [ ] Manually correct captions for: `librosa`, `OpenCV`, `FFmpeg`, `BPM`, `atempo`, `kizomba`
- [ ] Thumbnail: Beat-synced cuts side-by-side with the single terminal command. Bold text overlay: "Beat-Synced in Seconds"
- [ ] Title options to A/B test:
  - "I Built a Tool That Edits Dance Videos Automatically (One Command)"
  - "Stop Editing Dance Videos By Hand — Beat-Synced in Seconds"
  - "Auto-Edit Bachata Videos with Audio Analysis + One CLI Command"
- [ ] Tags: bachata editing, dance video automation, video editing automation, Python video tools, beat sync editing, dance studio workflow, FFmpeg tutorial, librosa BPM detection
- [ ] Pin a comment on launch day with the direct repo link and install command

---

## APPENDIX: ACCURATE TERMINAL COMMANDS FOR ON-SCREEN USE

All commands below are verified against the actual codebase.

```bash
# Single track — story video
python main.py --audio tracks/bachata_session.wav --video-dir bachata_clips/

# With genre preset
python main.py --audio tracks/salsa_track.wav --video-dir salsa_clips/ --genre salsa

# Dry-run (plan only, no render)
python main.py --audio tracks/bachata_session.wav --video-dir bachata_clips/ --dry-run

# With explain log
python main.py --audio tracks/bachata_session.wav --video-dir bachata_clips/ --explain

# YouTube Shorts batch
make run-shorts AUDIO=tracks/bachata_session.wav VIDEO_DIR=bachata_clips/

# Full pipeline — folder of tracks → mix + per-track videos + Shorts
make full-pipeline AUDIO=tracks/ VIDEO_DIR=bachata_clips/

# Install
make install
```

**Genre presets available for on-screen callout:**
- `bachata` — golden grade, fade transitions, vignette intro, 132 BPM default feel
- `salsa` — warm grade, wipeleft transitions, bloom intro, fast pacing (1.8s high clips)
- `reggaeton` — cool grade, fade transitions, bloom intro
- `kizomba` — vintage grade, slow pacing, 0.7x slow-mo on low clips
- `merengue` — warm grade, no transitions, fastest pacing (1.5s high clips)
- `pop` — no color grade, fade transitions

**Key PacingConfig values to reference if zooming in on config:**
- `high_intensity_seconds: 2.5` — clip duration at peak energy
- `snap_to_beats: true` — cuts land on beat boundaries
- `high_intensity_speed: 1.2` — slight fast-forward during chorus
- `low_intensity_speed: 0.7` — slow-motion in quiet sections
- `video_style: golden` — warm color grade
- `transition_type: fade` — smooth fade at section changes
- `intro_effect: vignette_breathe` — spotlight reveal on first beat
