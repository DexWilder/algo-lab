# Source Map

**Active source lanes + standing expansion protocol.**

The source map is never closed. What's listed here is what FQL Forge
currently harvests from; what's missing is what the biweekly source
expansion cadence is meant to discover.

---

## Standing question

**What source surfaces are we not harvesting yet that may contain
differentiated strategy ideas or components?**

This is the source map's perpetual open question. The biweekly source
expansion cadence (see `cadence.md` Layer 3) answers it with at least
one concrete proposal every two weeks.

---

## Currently active source lanes (v1 baseline)

### Code / explicit strategy sources
- **TradingView public scripts** — Pine conversion lane
- **GitHub** — systematic trading repos, quant research code, factor libraries
- **Kaggle / competition writeups** (when encountered; not actively scanned)

### Academic / formal research
- **SSRN** — quantitative finance working papers
- **arXiv** — quant-finance.TR, stat.AP, q-fin.* categories
- **Journal archives** — Journal of Financial Economics, Review of Financial Studies, Journal of Portfolio Management (when accessible)

### Practitioner writing
- **Quant blogs** — individual quant bloggers, institutional research blogs
- **Substack / Medium** — practitioner writeups
- **Newsletters** — quant-focused subscription content

### Community / discussion
- **Reddit** — r/algotrading, r/quant, r/systematicinvestor
- **Twitter / X** — quant accounts, FinTwit strategies discussion
- **Forums** — Elite Trader archives, QuantConnect community

### Long-form media
- **YouTube** — systematic trading channels, conference talks, quant interviews
- **Podcasts** — *to be activated (candidate for next biweekly source expansion)*
- **Transcripts** — interview transcripts, earnings call structural analysis

### Institutional writeups
- **Fund letters** (when public)
- **Research reports** from quant-oriented houses
- **Conference talks / slide decks** from systematic-trading events

---

## Source lanes to activate (prioritized by biweekly expansion cadence)

These are named but not yet actively harvested. The biweekly cadence
selects one per cycle to test:

1. **Podcast transcripts** — long-form interviews with systematic traders often contain strategy architecture clues not written down anywhere
2. **Conference panel transcripts** — QuantCon, ICAP, AI conferences
3. **Old forum archives** — pre-2015 Elite Trader, pre-Reddit quant forums (often have strategies that never made it to modern curation)
4. **Comment threads** on strategy videos/posts — sometimes commenters describe better variants than the OP
5. **Book excerpts and older texts** — decades-old systematic trading literature
6. **Private-style writeups** if discoverable later (not sought aggressively)
7. **New platforms** as they emerge — Substack boomed recently; the next comparable platform hasn't arrived yet

---

## Per-source tracking (populated over time)

For each source lane, track:

- **Ideas harvested** (count, lifetime)
- **Ideas reaching Validation state** (count)
- **Ideas yielding reusable components** (count, even if parent failed)
- **Ideas becoming elite-watch candidates** (count)
- **Noise rate** (rejected with no reusable components / total harvested)
- **Blocker patterns** (dominant blocker type for candidates from this lane)

Template:

| Source lane | Harvested | Reached Validation | Yielded components | Elite-watch | Noise rate | Dominant blocker |
|---|---|---|---|---|---|---|
| TradingView | — | — | — | — | — | — |
| GitHub | — | — | — | — | — | — |
| SSRN/arXiv | — | — | — | — | — | — |
| Quant blogs | — | — | — | — | — | — |
| YouTube | — | — | — | — | — | — |
| Reddit | — | — | — | — | — | — |
| ... | | | | | | |

Populated during weekly source yield review (see `cadence.md` Layer 2).

---

## Source lane promotion / demotion

Criteria (established as heuristics; refine via improvement log):

**Promote a tested lane to permanent:**
- ≥ 3 ideas reaching Validation state within 2 test cycles (~4 weeks), OR
- ≥ 1 idea becoming elite-watch within 4 weeks, OR
- Consistently yielding reusable components even at low volume

**Demote a permanent lane:**
- 0 ideas reaching Validation for 4+ consecutive weekly reviews
- Noise rate > 90% sustained
- Dominant blocker type consistently `framework mismatch` or `unclear hypothesis` (indicates lane produces vague ideas)

Demotion ≠ removal. Demoted lanes get reduced harvest frequency but
remain in the source map for occasional scan.

---

## Relationship to gap-directed search

Gap-directed search (see `PORTFOLIO_TRUTH_TABLE.md` open gaps) **biases
source choice, doesn't replace it.**

Example: if FX + STRUCTURAL gaps are open, harvest prioritizes sources
historically producing structural/session-transition or FX ideas (e.g.,
forum archives from the FX-heavy mid-2000s, specific quant bloggers
known for session-structure work). But broad harvest continues in
parallel — elite ideas often come from unexpected directions.

The weekly rollup's "Gap review" section names which gaps drove this
week's source choices.

---

## The "no source map is ever complete" principle

Every biweekly source expansion cadence asks the standing question.
Every answer is a concrete proposal to test. Every test either earns
lane promotion or gets logged as "tested, low-yield."

The source map at any given moment is a snapshot of what's being
harvested. It is not an assertion that these are all the sources that
exist. The assumption is always: *there is a source we haven't
harvested yet that would produce a differentiated idea if we found it.*

This principle is the practical expression of "search relentlessly"
from the doctrine. Not "harvest until exhausted from the current map"
but "expand the map continuously and harvest with discipline."

---

## Lane B-only surface

Source map edits, harvest cadence, and per-source yield tracking are
all Lane B activities (see doctrine DOES list). They do not touch Lane
A. The only Lane A interaction is when a candidate harvested from any
source reaches the promotion seam — at which point the source lane
becomes part of the candidate's attribution but not part of the
promotion decision.
