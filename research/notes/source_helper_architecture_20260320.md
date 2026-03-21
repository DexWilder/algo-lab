# Source Helper Architecture — Design Note

**Date:** 2026-03-20
**Status:** Design recommendation + first implementation

---

## The Problem

Claw searches autonomously via web search, but its reliability for
specific sources is unpredictable. It may or may not find a specific
GitHub repo, Reddit thread, or YouTube video on any given search. Thin
fetchers that pre-gather relevant candidates and drop them into a shared
queue give Claw higher-quality raw material to synthesize from.

## Architecture

```
Thin fetchers (cron, weekly)
    │
    ▼
~/openclaw-intake/inbox/source_leads/
    │  (simple text files with URLs + 1-line descriptions)
    │
    ▼
Claw reads source_leads/ during harvest tasks
    │  (synthesizes into standard harvest notes)
    │
    ▼
~/openclaw-intake/inbox/harvest/
    │  (standard .md notes in existing format)
    │
    ▼
Existing pipeline: dedupe → cluster → review → registry
```

The fetchers don't produce harvest notes. They produce **source leads**
— a URL and a one-line description. Claw does the hard work: reading
the source, extracting mechanical rules, assessing factor fit,
testability, blockers, and writing the full note.

This is the thinnest possible layer. Each fetcher is a single script
that writes a small text file. No databases, no APIs beyond what's
already available, no complex state management.

## Helper Assessment

### 1. GitHub Helper (RECOMMENDED FIRST)

**Why first:**
- `gh` CLI is already installed and authenticated
- GitHub search API is fast, free, and well-structured
- Quant strategy repos are easy to identify (keywords + stars)
- Output is a list of repo URLs — simplest possible lead format
- Directly addresses the weakest current lane (1 note in 61)

**Implementation:** Single script using `gh search repos`. Search for
futures/quant strategy repos updated recently, filter by stars > 5,
output URLs + descriptions to `source_leads/github_leads.md`.

**Estimated improvement:** Currently 1 GitHub note in 61 (2%). With
pre-gathered leads, expect 3-5 per cycle from higher-quality repos that
Claw might not have found on its own.

### 2. Reddit/Forum Helper (SECOND PRIORITY)

**Why second:**
- Reddit has a public JSON API (no auth needed for reading)
- `requests` is available
- r/algotrading and r/quant have systematic strategy discussions
- High noise, but fetcher can pre-filter by upvotes and keyword

**Implementation:** Single script using Reddit's public JSON endpoint
(`reddit.com/r/algotrading/search.json`). Search for futures strategy
posts with >= 10 upvotes, output URLs + titles.

**Estimated improvement:** Currently 0 Reddit notes. With pre-filtered
leads, expect 2-3 per cycle from the highest-engagement discussions.

### 3. YouTube Helper (THIRD PRIORITY)

**Why third:**
- Requires either `yt-dlp` install or YouTube Data API key
- Transcript extraction needs `youtube-transcript-api` pip install
- More complex than the other two
- YouTube content is often discretionary/narrative — lower conversion rate

**Implementation:** Install `youtube-transcript-api`, search for futures
strategy channels, extract transcripts for recent videos, write leads
with timestamps of mechanical rule sections.

**Estimated improvement:** Currently 0 YouTube notes. Moderate — YouTube
content is noisy, but a few channels (e.g., Trader Dante, No Nonsense
FX for concepts, Adam Grimes for statistical edges) produce testable ideas.

## Recommendation

**Build the GitHub helper now.** It's the simplest (one script, `gh` CLI
already installed), addresses the weakest lane, and has the highest
signal-to-noise ratio of the three.

Reddit second (public JSON API, no auth). YouTube third (needs pip install).
