# Feature Backlog — Bachata Beat-Story Sync

**Status:** 46 core features complete. See [`archive/completed.md`](archive/completed.md) for reference. 2 features in backlog.

---

## Backlog

---

### FEAT-047 — LRC Lyrics Overlay

**Status:** `PENDING`
**Priority:** High
**Depends on:** FEAT-045

**Goal:** Display the actual sung lyrics on screen at the moment they're sung, timed from a standard `.lrc` file. This is the primary emotional text layer — the words of the song, in the lower-third, appearing and disappearing with the music.

**Input format — LRC (standard timestamped lyrics):**
```
[00:12.50]Te vi bailar esa noche
[00:16.80]y algo en mí cambió
[00:21.00]
```
User places `bachata_track.lrc` next to the audio file. Empty timestamp lines = clear the text.

**Behaviour:**
- Each lyric line displays from its timestamp until the next timestamp
- Style: `lower_third`
- Spanish characters handled via Noto Sans + FFmpeg UTF-8 escaping
- Lines longer than ~45 chars auto-split at word boundary onto two lines
- No line is shown during the cold open window (0–7s) to avoid visual collision with FEAT-046

**LRC discovery:** system looks for `{audio_stem}.lrc` alongside the audio file. If not found, lyrics overlay is skipped silently — no error.

**New config fields in `PacingConfig`:**
```python
lyrics_overlay_enabled: bool = True    # auto-enables if .lrc file found
lyrics_lrc_path: str = ""             # explicit override path
```

---

### FEAT-048 — Lyrics Forced Alignment

**Status:** `PENDING`
**Priority:** Medium (Stage 2)
**Depends on:** FEAT-047

**Goal:** User has the lyrics as plain text but no timestamps. This feature takes `lyrics.txt` + the audio file and produces a `.lrc` file automatically, which then feeds FEAT-047.

**Why forced alignment over transcription:**
The user already has the lyrics — forced alignment maps *known* text to audio, which is more accurate and requires no correction for Spanish. Transcription (Whisper) guesses the words and will make errors.

**Architecture:**
```
src/services/lyrics_aligner.py
    align(audio_path: str, lyrics_path: str) -> str   # returns path to generated .lrc file

    Backend 1: aeneas   (preferred — forced alignment, deterministic, Spanish-capable)
    Backend 2: whisper  (fallback — auto-transcribes if no lyrics.txt provided)
    Backend 3: passthrough — if .lrc already exists, skip alignment
```

**`aeneas` integration:**
- Input: WAV audio + plain text file (one lyric line per line, no timestamps)
- Output: LRC or SRT with millisecond-precision timestamps
- Dependency: `aeneas` added to `pyproject.toml` as optional (`pip install aeneas`)
- Language hint: `es` (Spanish) passed to aeneas for better phoneme alignment

**`whisper` fallback:**
- Used when no `lyrics.txt` is provided but creator still wants auto-captions
- Word-level timestamps → grouped into lyric-length phrases → written as LRC
- Dependency: `openai-whisper` as optional

**Streamlit UI additions:**
- Upload box: `lyrics.txt` (plain text, one line per lyric line)
- Button: **"Align lyrics to audio"** → runs alignment → saves `.lrc` → FEAT-047 picks it up automatically
- Shows estimated alignment quality (aeneas confidence or whisper avg log-prob)

**New config fields:**
```python
lyrics_aligner_backend: Literal["auto","aeneas","whisper"] = "auto"
lyrics_txt_path: str = ""
```


