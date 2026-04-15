# Lane A / Lane B Operating Doctrine

**Established:** 2026-04-14. Permanent standing policy.

**Core doctrine:**

> **Search relentlessly. Validate brutally. Build continuously. Preserve everything useful.**

This is not a slowdown memo. This is the permanent operating model for
FQL / Algo Lab: two lanes, explicit seam between them, both running at
full intensity in their respective domains.

---

## The two lanes

### Lane A — Protected live-system discipline

Lane A is the active machine: the forward runner, the live probation
portfolio, scheduled monitoring, the live registry, the recovery stack.

Lane A's job is **integrity**:
- No unnecessary drift in live state
- No contamination of the frozen runtime during hold windows
- No premature transitions from research to production
- Deterministic execution of strategies that have earned the right to run

Lane A moves **carefully and selectively.** Changes require evidence,
governance, and an explicit promotion event.

### Lane B — Endless strategy factory

Lane B is the research and construction engine: discovery, validation,
component extraction, crossbreeding, refinement, memory.

Lane B's job is **edge manufacture**:
- Continuous harvesting from every viable source
- Brutal validation against `docs/ELITE_PROMOTION_STANDARDS.md`
- Component extraction, memory preservation, crossbreeding
- Relentless search for elite strategies and portfolio combinations

Lane B moves **aggressively and continuously.** Its pace is capped only
by validation capacity, and validation capacity is a function of the
hardening queue's progress — meaning Lane B's own tooling grows its
own ceiling.

---

## Guiding principles

### 1. Discover broadly

Harvest constantly and from every angle:
- TradingView public scripts
- GitHub repos (systematic trading, quant research)
- Academic papers (SSRN, arXiv, journal archives)
- Quant blogs, forum archives, newsletters
- YouTube transcripts
- Reddit / X / community discussions
- Institutional research publications
- Microstructure studies
- Asset-specific, session-specific, volatility-regime-specific ideas
- Event-driven and calendar-sensitive structures
- Carry, structural, value, and event families
- Any new source lanes worth opening over time

**No stone left unturned.** If a viable source exists, it gets surveyed.

### 2. Validate brutally

Aggressive search without the discipline to reject is noise
manufacturing. Every promising candidate passes through:

- Shape classification per `docs/ELITE_PROMOTION_STANDARDS.md` (wrong-
  framework evaluation is itself a failure mode; all candidates get
  the framework their shape demands)
- Baseline backtest with honest trade economics
- Walk-forward / OOS behavior where sample size allows
- Concentration gates (top-N share, max year share, median trade,
  positive instance fraction — scale-appropriate to the shape)
- Cross-asset / cross-regime stability checks
- Parameter sensitivity sweep
- Portfolio contribution / correlation / overlap against existing active strategies
- Salvage lane when failure looks specifically fixable
- Hard rejection when the failure is structural

Kill-on-sight failure patterns (documented in `ELITE_PROMOTION_STANDARDS.md`):
concentration catastrophe, wrong-direction bias, data leakage, silent
failure, correlation breach, ill-defined factor.

The bar does not lower because the pipeline is busy.

### 3. Build continuously

Lane B is a factory, not an inbox. It doesn't just accept ideas; it
**manufactures elite algorithms.**

This means active ongoing work on:
- Discovering new parent strategies
- Improving near-miss candidates (adjusted entries, exits, filters, risk models)
- Extracting reusable components from validated strategies
- Crossbreeding validated parent parts into new hybrids
- Evolving exit architecture, sizing logic, regime filters
- Identifying true portfolio roles for new candidates
- Replacing weaker active strategies with better validated ones

The mission is **elite algorithms**, not strategy collection.

### 4. Preserve everything useful

Nothing useful disappears because it's not the current focus. The
strategy registry and memory stores:
- Winners (core, probation, archived-with-reason)
- Near-misses with the specific failure mode documented
- Rejected ideas with rejection_reason + classification_reasons
- Salvageable concepts tagged for future reuse
- Extracted components with `reusable_in` annotations
- Regime observations per strategy
- Asset/session/volatility behavioral notes
- Portfolio-role observations
- Cross-validation and convergent-source evidence

A candidate that fails today under one framework may be the parent of
a winning hybrid tomorrow. Memory compounds.

### 5. Attack portfolio gaps intentionally

Use the Genome Map, factor decomposition, and `docs/PORTFOLIO_TRUTH_TABLE.md`
open-gaps list to direct the search:
- Missing strategy families
- Weak regime coverage (trending / ranging / high-vol / low-vol)
- Weak session coverage (morning / midday / afternoon / overnight)
- Weak asset-class diversification
- Overcrowded redundant clusters (decide who stays, who goes)
- Missing tail engines
- Missing structural / event-driven primaries
- Missing factor exposures (FX and STRUCTURAL are currently open as of 2026-04-14)

Lane B's search prioritizes **candidates that improve the whole
portfolio**, not just themselves.

### 6. Capacity scales the search

Lane B's operating pace is capped only by validation capacity. The
right response to "we have too many candidates to validate properly"
is not **harvest less** — it is **scale validation capacity.**

Concretely, that means the hardening queue (items 3 → 5 → 1 → 2 → 4):
shared dead-strategy guards, execution-shape fields, atomic lifecycle
updaters, authority-consistency validators, stale-reference audits.
Those are not side hygiene — they are **Lane B's own validation-scaling
infrastructure.** Every hardening item shipped raises Lane B's safe
throughput ceiling.

---

## Lane B ↔ Lane A seam — the promotion protocol

Lane B can harvest, test, validate, refine, and reject at any pace.
**The moment a candidate touches the active runner universe, the
intraday monitor baseline, or a `controller_action != OFF` value — that
is a Lane A transition.** Transitions are governed, not implicit.

### Lane B candidates in the registry

Lane B candidates live in the registry with one of the following states:

| Registry state | What Lane B has done | Can the runner pick it up? |
|---|---|---|
| `lifecycle_stage: "discovery"` | Harvested, tagged, not yet converted | No (no strategy code yet) |
| `lifecycle_stage: "first_pass"` | Converted, first-pass backtested | No (`status=testing` / `controller_action=OFF` default) |
| `lifecycle_stage: "validation"` | Passed first-pass, running deeper validation | No (same) |
| `lifecycle_stage: "watch"` | Passed validation but awaiting Lane A authorization for promotion | No (still `controller_action=OFF`) |

**Lane B's authority ends at `lifecycle_stage: "watch"` with `controller_action=OFF`.**

### Lane A authorization required for

- Setting `status=core` or `status=probation`
- Setting `controller_action` to any eligible value (`FULL_ON`, `REDUCED_ON`, `PROBATION`)
- Setting or updating `promoted_date`
- Adding a strategy to `live_drift_monitor.py BASELINE["strategies"]`
- Adding a strategy to the runner universe via `build_portfolio_config`
- Adding any new scheduled job to `fql_research_scheduler.py`
- Adding any new launchd agent
- Changing `execution_path` field of an active strategy
- Removing a strategy from the `excluded_from_strategy_drift` list
- Any edit to `engine/strategy_universe.py` DEAD_STATUSES or the status guard

### The promotion event (Lane B → Lane A)

When Lane B has a candidate ready for Lane A, the promotion event is a
deliberate operator decision that carries:

1. **Framework attestation:** the candidate was evaluated under the
   correct shape framework per `docs/ELITE_PROMOTION_STANDARDS.md`,
   and the evaluation passed.
2. **Plumbing readiness:** the infrastructure to host the candidate
   exists and is verified — data pipeline includes the asset, runner
   can load the shape (or an out-of-band execution path exists),
   monitor baseline can classify it, scorecards know it.
3. **Portfolio role:** the candidate fills a documented gap or displaces
   a weaker incumbent via a documented replacement scoring.
4. **Atomic registry transition:** `status`, `controller_action`,
   `execution_path`, `promoted_date`, and any shape-specific fields
   update together in one commit. Partial updates are rejected.
5. **Post-promotion verification:** within 24 hours of promotion, a
   verification pass confirms the strategy appears correctly in the
   runner, the monitor, and any scorecards.

If any of these five are incomplete, the promotion does not happen.
Lane B waits or fixes the gap. No partial promotions.

---

## Lane B DOES (full aggressive scope)

Lane B runs continuously and aggressively on all of the following.
None of these require Lane A authorization; all are in-lane.

- **Harvest:** scan `~/openclaw-intake/inbox/*`, GitHub, TradingView,
  SSRN, arXiv, blogs, YouTube, Reddit, X, all configured source lanes
- **Triage:** dedupe, classify, cluster, tag, prioritize
- **Convert:** Pine → Python, natural-language spec → strategy.py
- **First-pass test:** `research/batch_first_pass.py` or appropriate
  framework per shape
- **Deep validation:** walk-forward matrix, cross-asset, parameter
  sensitivity, salvage/rescreen, prop-firm simulation
- **Component extraction:** identify reusable entries, exits, filters,
  regimes, sizing modules
- **Crossbreeding:** combine validated components into new hybrids per
  `docs/CROSSBREEDING_PLAYBOOK.md`
- **Registry enrichment:** update `lifecycle_stage`,
  `classification`, `rejection_reason`, `reusable_as_component`,
  `convergent_sources`, `component_validation_history`
- **Genome map updates:** classify new candidates, update
  `docs/PORTFOLIO_TRUTH_TABLE.md` gap analysis
- **Salvage work:** re-test promising failures with adjusted
  evaluation, explore framework-mismatch cases
- **Memory writes:** every useful observation lands in the registry
  or genome map; nothing useful disappears
- **Replacement scoring:** compare candidates against incumbents via
  `research/replacement_scoreboard.py` logic
- **Gap-directed search:** use portfolio truth table's open gaps to
  steer harvest priorities
- **Research documentation:** new entries in `research_log.md`,
  `research/specs/`, strategy postmortems

Lane B does all of this. Every day. At whatever pace validation
capacity sustains. And the hardening queue continually raises that
ceiling.

---

## Lane B DOES NOT

Lane B must never (without Lane A authorization):

- Edit `engine/strategy_universe.py` `DEAD_STATUSES` or status guard
- Edit `research/live_drift_monitor.py` BASELINE structure (including
  adding or removing strategies from `strategies` or
  `excluded_from_strategy_drift`)
- Edit `research/fql_research_scheduler.py` JOBS dict
- Create or modify files in `~/Library/LaunchAgents/`
- Set any registry strategy's `status` to `core` or `probation`
- Set any registry strategy's `controller_action` to an eligible value
- Write to `logs/trade_log.csv`, `logs/daily_report.csv`,
  `logs/spread_rebalance_log.csv`, or `logs/signal_log.csv`
- Edit `scripts/run_fql_forward.sh` pre-flight gate logic
- Edit `scripts/fql_watchdog.sh` recovery logic
- Edit `run_forward_paper.py` runner logic
- Edit any strategy's `strategy.py` once it has `status in {core, probation}`
- Modify authority docs (CLAUDE.md, PROBATION_REVIEW_CRITERIA.md,
  XB_ORB_PROBATION_FRAMEWORK.md, ELITE_PROMOTION_STANDARDS.md,
  HOLD_STATE_CHECKLIST.md, LANE_A_B_OPERATING_DOCTRINE.md) without
  explicit operator consent

These are Lane A's surfaces. Lane B reads them freely and cites them
freely. Lane B does not modify them.

**Lane B CAN, without authorization:**

- Edit any file under `research/data/` *except* `strategy_registry.json`
  fields that govern lifecycle (`status`, `controller_action`,
  `promoted_date`, `lifecycle_stage`, `execution_path`)
- Edit any file under `strategies/<candidate>/` where the candidate is
  still in discovery / first_pass / validation / watch
- Edit any `first_pass/*.json` or `research/reports/*`
- Add files to `research/specs/`
- Add files to `research/postmortems/`
- Add new research scripts to `research/` (e.g., new analysis tools)
  **that are not scheduled**
- Update `research/data/strategy_genome_map.json`
- Update `research/data/harvest_*`, `research/data/crossbreeding_*`
- Update registry non-lifecycle fields (notes, component_validation_history,
  tags, classification, rejection_reason, reusable_as_component)
- Write to `research/logs/*` research-output files
  (but NOT to `logs/*` forward-runner files)

---

## Relationship to hold discipline

During an active hold (e.g., the 2026-04-14 → 2026-05-01 window
governed by `docs/HOLD_STATE_CHECKLIST.md`):

- **Lane A surfaces are frozen** per the hold checklist
- **Lane B surfaces remain fully active** — harvest, validation, memory
  writes, component extraction, crossbreeding, genome map updates all
  continue at full pace
- **Promotion events are suspended during hold** — Lane B can produce
  candidates ready for Lane A, but the promotion event itself waits
  for hold expiry + the governing checkpoint outcome
- **Candidates that ripen during hold** accumulate at `lifecycle_stage:
  "watch"` with `controller_action=OFF`. When hold exits, they are
  evaluated together against any relevant gap-fill authorization.

**Hold does not idle Lane B. Hold only suspends the seam.**

---

## Operating tempo

Lane B's daily rhythm:

- **Always advancing** in at least one of: harvest, triage, conversion,
  validation, salvage, component extraction, memory enrichment,
  gap-directed search, candidate refinement
- **Pace is sustainable-maximum**, not artificial-maximum. Idle is
  acceptable when validation queue is saturated; the response is to
  invest in the hardening queue, not to force more harvest that the
  queue can't digest
- **Throughput metric is validated artifacts**, not ideas touched.
  100 harvested ideas → 1 validated elite candidate is worth more than
  1000 harvested ideas → 1 "probably fine" candidate
- **Brutality does not decay under load.** If the bar would have to
  drop to clear the queue, the queue doesn't clear — capacity grows,
  not standards.

---

## What this doctrine enables

- **Continuous edge discovery** even during Lane A hold windows
- **No lost ideas** — every harvested concept lives in memory
- **Elite strategies emerge from sustained broad search**, not from
  short bursts of frantic harvest
- **Plumbing failures become impossible** — the promotion protocol
  catches what FXBreak-6J's framework mismatch and MYM's pipeline
  gap would have bypassed
- **The portfolio improves every cycle** through gap-directed search
  and intentional replacement
- **The system compounds** — every validation run, every extracted
  component, every rejected-with-reason strategy feeds the next
  discovery cycle

---

## Doctrine permanence

This document is standing policy, not a one-off. It governs Lane B's
posture until explicitly replaced by a revised doctrine with equal
operator authorization.

Amendments to this doctrine follow the same rule as edits to other
authority documents: explicit operator consent required. Lane B does
not amend its own governance.

---

**Closer:**

> **Standing doctrine: relentless strategy discovery and elite strategy
> construction in parallel with protected live-system discipline.**

Lane A protects the machine. Lane B grows the empire.

Every day the system does not break is a day Lane B gets to compound.
Every day Lane B compounds is a day the portfolio becomes stronger.
Every day the portfolio becomes stronger is a day the lab is closer
to elite.

There is no end state. There is only the next cycle.
