# Remaining Source Classes — Ranked Recommendations

**Date:** 2026-03-20
**Context:** 7 source helpers now active (TradingView, academic, GitHub,
Reddit, YouTube, microstructure prompts, practitioner blogs). What's
still missing that could surface unique, testable, portfolio-useful ideas?

---

## Current Stack (Implemented)

| Source Class | Helper | Mechanism | Signal/Noise |
|-------------|--------|-----------|-------------|
| TradingView | Claw autonomous | Web search | High (scripts have code) |
| Academic papers | Claw autonomous | Web search | High (peer-reviewed) |
| GitHub repos | fetch_github_leads.sh | gh CLI search | Medium (needs code review) |
| Reddit/forums | fetch_reddit_leads.py | Public JSON API | Low-Medium (high volume) |
| YouTube | fetch_youtube_leads.py | Search + transcripts | Low-Medium (lots of narrative) |
| Microstructure | Claw autonomous | Web search | High (specialist sources) |
| **Practitioner blogs** | **fetch_blog_leads.py** | **RSS feeds** | **High (curated, long-form)** |

---

## Top 3 Remaining Source Classes

### #1: Strategy Digest Databases (RECOMMENDED NEXT)

**Why it matters:** Quantpedia, QuantifiedStrategies, and similar sites
maintain curated databases of documented strategies with implementation
details, performance stats, and academic citations. These are pre-filtered
for testability — every entry is already a strategy summary, not raw
research. This is the closest thing to a "strategy catalog API."

**Signal/noise:** Very high. Every entry is a strategy. The question is
only whether it's applicable to futures.

**Expected unique contribution:** Strategy families that exist in academic
literature but aren't surfaced by general web search. Especially strong
for CARRY, VALUE, and cross-asset factors that are well-documented
academically but under-harvested by FQL.

**Ingestion approach:**
- Quantpedia has no public API, but their strategies page can be scraped
  for titles and categories
- QuantifiedStrategies publishes blog-style posts with RSS
- A simple fetcher could pull strategy titles + URLs weekly
- Claw then reads each URL and produces harvest notes

**Status recommendation:** Build next — highest expected conversion rate
of any remaining source.

### #2: Podcast / Interview Transcripts (STAGE FOR LATER)

**Why it matters:** Elite practitioners (CTAs, prop traders, quant PMs)
discuss conceptual edges in podcast interviews that they don't write
about. Shows like Top Traders Unplugged, Chat With Traders, and Flirting
with Models produce occasional deep technical discussions.

**Signal/noise:** Low overall, but HIGH when it hits. Most podcast
content is narrative/philosophical. Mechanical strategy descriptions
appear maybe 10-20% of episodes.

**Expected unique contribution:** Conceptual edges from practitioners
who don't write — especially CTA-style trend, carry, and vol strategies
that are implementation-ready but not published in papers.

**Ingestion approach:**
- Some podcasts have transcripts available on their sites
- youtube-transcript-api can extract from YouTube-hosted episodes
- A fetcher would search for recent episodes mentioning strategy keywords,
  extract transcripts, score for mechanical content
- Low cap (3-5 leads per run) due to high noise

**Status recommendation:** Stage — build after strategy digest helper.
Requires more filtering sophistication to avoid narrative waste.

### #3: Exchange / Market Structure Documentation (ADD TO CLAW PROMPTS)

**Why it matters:** CME Group, ICE, and exchange education pages document
contract specifications, session timing, roll mechanics, and delivery
logic that directly inspire STRUCTURAL and EVENT strategies. The ZN
Afternoon Reversion was born from understanding session microstructure —
more ideas like it live in exchange documentation.

**Signal/noise:** Very high per document, but very low volume. Exchange
docs change rarely. This is a "read once, extract insights" source,
not a weekly scan.

**Expected unique contribution:** STRUCTURAL edges from session mechanics
(when does the cash market close? what happens at roll?), EVENT edges
from calendar mechanics (when are options expirations? settlement
procedures?), CARRY insights from delivery and financing documentation.

**Ingestion approach:**
- No fetcher needed — add exchange docs as a Claw prompt source
- List specific URLs (CME education pages, contract specs, calendars)
  in a reference file that Claw reads during blocker_mapping (Sunday)
- One-time deep read, then periodic check for changes

**Status recommendation:** Add to Claw prompts now (zero engineering).
Just create a `source_leads/exchange_references.md` file with URLs.

---

## Implementation Priority

| Priority | Source | Action | Effort |
|----------|--------|--------|--------|
| **Done** | Practitioner blogs | fetch_blog_leads.py (RSS) | Implemented |
| **Next** | Strategy digests | Scrape Quantpedia/QS titles + URLs | ~1 hour |
| **Stage** | Podcasts | YouTube transcript extraction for podcast episodes | ~2 hours |
| **Now** | Exchange docs | Static reference file for Claw | ~10 minutes |

---

## Feeds to Add to Blog Helper (Expansion)

As the blog helper proves out, these feeds should be added:

| Feed | Category | Why |
|------|----------|-----|
| Verdad Capital blog | Value/fundamental | Strong value investing + systematic framework |
| AQR Insights | Quant research | Factor investing, carry, momentum research |
| Man AHL research | Managed futures | CTA/trend/carry research |
| Winton research | Managed futures | Statistical approaches to trading |
| Two Sigma Insights | Quant research | Broad systematic finance research |
| Kris Abdelmessih (Moontower) | Vol/options/trading | Deep vol and market structure content |
| Corey Hoffstein (Think Newfound) | Portfolio construction | Already included via Flirting with Models |
