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

## Day-1 source yield baseline (2026-04-15)

Derived from `research/data/strategy_registry.json` `source_category`
aggregation. This is a **lifetime** snapshot, not a weekly rate —
weekly rates begin accumulating from the first weekly rollup on
Friday 2026-04-17. The columns below are mapped from registry fields
as a best approximation; several are marked `unknown` because the
data to compute them doesn't exist yet (component tracking was not
per-source, elite-watch is a recent concept, weekly noise rate
requires weekly data).

| Source lane | Harvested (lifetime) | Reached probation / core | Yielded components | Noise rate (archived+rejected / total) | Dominant blocker |
|---|---|---|---|---|---|
| academic | 41 | 2 probation | unknown | 37% (15/41) | unknown |
| tradingview | 28 | 1 probation | unknown | 61% (17/28) | unknown |
| internal | 21 | 3 core | unknown | 71% (15/21) | unknown |
| expansion | 7 | 0 | unknown | 57% (4/7) | unknown |
| practitioner | 5 | 0 | unknown | 20% (1/5) | unknown |
| ict | 3 | 0 | unknown | 100% (3/3) | unknown |
| user | 3 | 0 | unknown | 100% (3/3) | unknown |
| factory | 3 | 1 probation | unknown | 67% (2/3) | unknown |
| internal_crossbreeding_cross_asset_extension | 2 | 2 probation | unknown | 0% (0/2) | unknown |
| claw_synthesis | 1 | 0 | unknown | 100% (1/1) | unknown |
| falsification_discovery | 1 | 1 probation | unknown | 0% (0/1) | unknown |
| internal_crossbreeding | 1 | 1 probation | unknown | 0% (0/1) | unknown |

### Initial observations (not conclusions — need weekly data)

- `internal_crossbreeding*` lanes look extraordinarily efficient on this lifetime view (both items reached probation), but sample size is trivial (N=2, N=1). Worth watching whether this holds as volume grows.
- `ict` and `user` lanes show 100% noise on lifetime data. Candidates for demotion consideration after observation — but again, small samples.
- `academic` lane has the highest volume (41) with 2 probation. 5% probation yield is low in absolute terms but may reflect the lane's inherent selectivity; academic papers require more framework-fitting than TradingView scripts.
- `tradingview` lane has 28 items, 61% noise, only 1 reaching probation. Historically a high-volume/low-yield lane.
- `internal` lane produced all 3 current core strategies — the highest-value lane historically, but also possibly because early work was predominantly internal and had the benefit of custom framework fit.
- **Every lane's "yielded components" is `unknown`** because per-source component attribution wasn't tracked historically. v2+ should add this instrumentation — current registry has `component_validation_history` per strategy but not aggregated by source. Log this as improvement-log candidate.

### Lanes to activate (prioritized for biweekly source expansion)

Unchanged from baseline list above — reminder that **podcasts / interview transcripts** are the next queued expansion test (prioritized for first biweekly expansion cycle, target: 2026-04-17 weekly rollup + 2026-04-24 biweekly expansion review).

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
