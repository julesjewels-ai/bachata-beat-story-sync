# Marketing Execution Plan

> **Context:** Solo founder, pre-launch, $0 budget, YouTube-first. Derived from [marketing_strategy.md](marketing_strategy.md).
> **Date created:** 2026-04-02 (Q2 2026 — launch window is now)

---

## Critical Path (don't skip these)

```
Week 1: Film and post hero demo video on YouTube
Week 2: GitHub README update + basic landing page live
Week 3: Seed 2-3 communities; DM 1-2 dance YouTubers for beta feedback
Week 4: Launch day — Product Hunt + HN + Reddit + Shorts clips
Ongoing: 1 YouTube video every 2-3 weeks
```

---

## Phase 1 — Pre-Launch: Build the Demo Asset (Weeks 1–3)

### Week 1 — Hero demo video (most important action)

An 8–12 minute tutorial/demo hybrid for YouTube. This single video is the primary marketing asset — everything else links back to it.

**Script structure:**

| Timestamp | Section | Content |
|-----------|---------|---------|
| 0:00–0:30 | Hook | Play 20 seconds of the finished montage. Then: "I didn't edit a single frame of that." |
| 0:30–2:00 | Problem | Show what manual beat-syncing looks like in a normal editor |
| 2:00–8:00 | Live demo | Run the tool live — real footage, real terminal, real render |
| 8:00–10:00 | Result + Explain | Play the output; show the `--explain` log; point out specific decisions the tool made |
| 10:00–end | CTA | GitHub link or waitlist |

**The video must show:**
- The tool running (terminal output, real command, real clips)
- The output (beat-synced montage with visible beat-cuts)
- Before/after timing ("manual edit ~2 hours; this took 4 minutes")
- The `--explain` output — strongest differentiator; most people have never seen an AI editor explain its own decisions

### Week 2 — Minimum viable presence

| Asset | Action |
|-------|--------|
| GitHub README | Add a GIF of tool running + rendered output side-by-side. One-command install. Prominent YouTube demo link. |
| YouTube channel | Creator-findable name — e.g. "Beat Sync Studio" or "Bachata Video Studio" (not just the repo name) |
| Landing page | GitHub Pages is sufficient. Use the outline in `marketing_strategy.md` §9. Focus: hero + how-it-works + GitHub CTA. |

### Week 3 — Pre-launch seeding (genuine, not spam)

Post in these communities **as a builder sharing work**, not as advertising:

- **r/learnprogramming** or **r/Python** — technical angle: "I built a tool to auto-sync dance videos to music beats using librosa + OpenCV — here's how it works"
- **r/bachata** or **r/salsadance** — creator angle: "I built something for dance content creators" (be transparent)
- **1–2 small dance YouTubers (10k–50k subs)** — DM offering to process one of their tracks free in exchange for honest feedback. Goal: one real testimonial before launch.

---

## Phase 2 — Launch Day (Week 4)

**Do all of these on the same day:**

1. Post the YouTube demo video
2. Tag the first release on GitHub (`v1.0.0`)
3. Submit to **Product Hunt** — link the YouTube demo as the primary demo asset
4. Post **Hacker News "Show HN"** — technical but high-visibility, costs nothing
5. Post in the Reddit communities seeded in Week 3
6. Clip the YouTube video into 2 Shorts — use your own tool if possible (great meta-content)

**Product Hunt tips:**
- Schedule for Tuesday or Wednesday, post at 00:01 PT
- Ask 5–10 people you know to upvote on day one — enough for first-page traction if the product is solid
- The maker comment matters: describe the problem you solved and why you built it personally

---

## Phase 3 — Post-Launch Growth (Ongoing)

**Flywheel:** YouTube tutorial → GitHub stars → community proof → more tutorials

**Realistic solo cadence:** 1 video every 2–3 weeks

### Video types that work for this tool

| Video type | Why it works |
|------------|--------------|
| "Bachata edit in 5 minutes" — show result first, then tool | Hooks the creator audience immediately |
| Genre comparison — same footage processed with all 6 genre presets | Shows depth; highly shareable |
| Before/after with a real creator's footage | Social proof; works as a case study |
| "How the beat detection works" — technical explainer | HN/dev audience; builds trust and authority |
| "10 YouTube Shorts in 10 minutes" | Directly addresses the Shorts creator pain point |

---

## Budget guidance

**$0 phase:** The plan above runs entirely free. Organic YouTube + GitHub + community seeding is the full strategy.

**When you have $50–100:** Run a single YouTube ad targeting "how to edit dance videos" pointing to your best-performing organic video. Do not run Meta ads — the creative overhead isn't worth it solo.

---

## Constraints this plan is built around

- Solo founder — no team to delegate content production to
- Pre-launch — no users yet, so social proof must be built before or at launch
- YouTube-primary — longer shelf life than TikTok; tutorials rank in Google search
- $0 budget — organic-first; paid only as an amplifier once there's a proven video

---

## Reference

Full strategy, personas, messaging, competitive landscape, landing page outline, and quarterly campaign roadmap: [marketing_strategy.md](marketing_strategy.md)
