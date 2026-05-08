# FQL Progression Plan — 2026-05-08

**Filed:** 2026-05-08
**Author:** Claude session, operator-directed
**Type:** forward-looking timeline (not a build artifact)
**Lane:** B / governance

**Operator framing:**
> Stopping new module builds during RED review load is governance, not inactivity. The autonomous machine keeps running. This plan keeps visible forward pressure toward more strategies, validation, and paper trading.

---

## §0 — One-line state

🟢 **Autonomous loop running.** 🔴 **Build gauge RED — no new modules until consolidation.** Forward path is gated, not blocked.

---

## §1 — Current state (Phase 1 — Autonomous Loop Stabilization)

**What's running without human intervention:**

| Cadence | System | Status |
|---|---|---|
| Continuous | OpenClaw gateway / watchdog 5min / claw control loop 30min | active |
| Sun + Wed 20:00 PT | source-helpers (fetches under Patch A query mix) | active |
| Weekday 17:00–18:00 PT | Lane A live ops (forward-day, daily-research, operator-digest, treasury-rolldown) | active |
| Tue/Thu 18:00 PT | twice-weekly research | active |
| Fri 18:30 PT | weekly research | active |
| **Weekday 19:00 PT** | **Forge daily-loop (rotation-fixed, 19-candidate pool, 4-day cycle)** | **organic** |
| **Weekday 08:00 PT** | **Forge morning digest (closed-loop absorption)** | **organic** |
| 1st Sat 09:00 PT | monthly system review | active (first fire 2026-06-06) |

**Working metrics:**
- Forge fires: 3 organic clean fires (5/5, 5/6, 5/7); 8 distinct PASSes; 100% registry-absorbed
- Backlog: 🟢 GREEN (0 pending review)
- Tripwires: 0
- Registry: stable at 163
- Lane A drift: 0 changes today; no unauthorized state mutations

**What's blocked right now:**
- New module builds (review-load RED 50, threshold 35)
- Cadence increases (closed-loop hasn't proved at current rate yet)
- Patch B / Patch C of source-priority feedback (deferred 2-4 weeks)

---

## §2 — Next checkpoints (dates fixed)

| When | Trigger | Action | Decision |
|---|---|---|---|
| Tonight Fri 2026-05-08 19:00 PT | Forge day-3 fire (organic) | Auto: tests items[15:19]+wrap | none |
| Mon 2026-05-11 08:00 PT | Morning digest reads day-3 | Auto: digest produces report | none |
| Mon 2026-05-11 next session | Verification + governance audit re-check | Read the digest; re-run audit | If RED still: consolidate only. If YELLOW/GREEN: 1 small packet eligible (likely snapshot date-bug fix) |
| **Sun 2026-05-10 20:00 PT** | source-helpers fire #1 (Patch-A-influenced) | Auto: GitHub leads under new query mix | none |
| **Sun 2026-05-10 ~21:00 PT** | **Operator action: Patch A first-fire review** | Use checklist `_DRAFT_2026-05-07_patch_a_review_checklist.md` §1 | CONTINUE / PARTIAL REVERT / FULL REVERT / WAIT-FOR-WEDNESDAY |
| Tue 2026-05-12 | Twice-weekly research fire | Auto | none |
| **Wed 2026-05-13 20:00 PT** | source-helpers fire #2 | Auto | none |
| **Wed 2026-05-13 ~21:00 PT** | **Operator action: Patch A trend confirmation** | Checklist §2 | CONTINUE / PARTIAL ADJUST / REVERT / EXPAND-to-Patch-B |
| Fri 2026-05-15 18:30 PT | Weekly research fire | Auto | none |
| **Sat 2026-05-17** | **Patch A yield-shift assessment** | Re-run `forge_source_feedback.py --lookback-days 14`; checklist §3 | PROMOTE TO PERMANENT / TRIM AND KEEP / REVERT FULLY |
| Sat 2026-06-06 09:00 PT | First organic monthly system review | Auto: produces `2026-05_FQL_SYSTEM_REVIEW.md` | Operator reviews; first month-over-month delta available |

---

## §3 — Next build gates (what unlocks what)

Three queued elite upgrades from the operator's list, with explicit unlock criteria:

### Gate A — Snapshot date-bug fix + minimal queue-aging polish
**Unlocks when:**
- Review load score drops from RED to YELLOW/GREEN (likely 2026-05-12 to 2026-05-13, when 5/5–5/6 commits roll past 7d window)

**Unblocks:** queue-aging detection actually works (currently has 1-day forward drift due to source-fire-date naming bug). Small bug; clean fix.

### Gate B — Graph-backed candidate generator
**Unlocks when ALL of:**
- Patch A assessment (Sat 5/17) shows positive yield shift OR clean revert
- Review load score has been YELLOW or GREEN for ≥3 consecutive days
- ≥7 organic Forge fires on disk (current: 3; need ~4 more weekday fires)

**What it builds:** queries `relationships.components_used` as a graph; identifies untested 2-of-3 / 3-of-3 component combinations weighted by gap-fill score; proposes new candidates for the runner pool. Operator approves additions.

**Earliest realistic start:** Mon 2026-05-19 (after 5/17 assessment + governance recovery).

### Gate C — Auto-drafted pre-flight packets
**Unlocks when ALL of:**
- Gate B has shipped and produced ≥5 graph-suggested candidates
- Operator has approved ≥1 graph-suggested candidate via existing manual pre-flight (proves the candidates are register-worthy)
- Review load gauge stable in YELLOW or below

**What it builds:** when ≥3 PASS candidates accumulate without manual pre-flight, auto-drafts the pre-flight packet with evidence summary, duplication risk, proposed registry fields, recommendation per candidate. Operator approves draft → manual append.

**Earliest realistic start:** ~2026-06-01 (depends on Gate B yield).

---

## §4 — Paper-trading progression

**Where paper trading is today:** 3 XB-ORB-EMA-Ladder probation strategies (MNQ/MCL/MYM) on forward-day runner. Probation since 2026-04-06/04-08/04-13. Per `CLAUDE.md` Probation Portfolio.

**Why current PASS candidates ARE NOT yet paper-trading-eligible:**
The 12 batch-registered XB hybrids (commit `a5d75a1`) are `status: idea` only. They have:
- Cheap-screen PASS verdicts (one fire each)
- Component attribution via `relationships.components_used`
- Source memos preserved

They DO NOT yet have:
- Walk-forward H1/H2 evidence
- Cross-asset validation outside the families they were tested in
- Concentration profile (top-3, top-10, median trade, year share, DD duration — the 6 gates from `feedback_validation_gates.md`)
- Prop-sim correlation analysis vs existing probation portfolio
- Duplication score against the 3 active probation strategies

### Required validation battery (per `feedback_validation_discipline.md` + `feedback_validation_gates.md`)

For a `status: idea` to graduate to `status: probation` (and onto forward-day runner):

| Test | What | Source |
|---|---|---|
| 1 | Walk-forward H1/H2 both > 1.0 PF | `feedback_validation_gates.md` |
| 2 | Top-3 concentration < 30% | same |
| 3 | Top-10 concentration < 55% | same |
| 4 | Median trade ≥ 0 | `feedback_edge_doctrine.md` |
| 5 | Cross-asset reproducibility (≥3 assets) | same |
| 6 | Sample size adequate (n ≥ 500 workhorse / ≥ 30 tail) | `feedback_dual_archetype_factory.md` |
| 7 | Max single year < 40% | gates |
| 8 | DD duration < 900d | gates |
| 9 | Prop-sim acceptance | TBD (no formal prop-sim tool yet) |
| 10 | Correlation w/ existing probation < 0.7 | TBD (no correlation matrix yet) |

**Tests 9-10 are unbuilt.** Building those is the Phase 3 (Validation Funnel) work.

### Required clean autonomous cycles before paper expansion

Operator-set. Proposed defaults (refine as you wish):

- **≥10 organic Forge fires without tripwire** (current: 3)
- **≥4 weeks of organic morning digests with backlog ≤ YELLOW**
- **≥1 monthly system review surfacing no Lane A drift**
- **≥1 successful Patch (A or B) with measured yield shift**
- **Paper-trading queue defined** (which slots are open; which families are over/under target)

**Earliest realistic paper expansion:** ~2026-07-01 (after 8 weeks of organic cycles + Phase 3 validation funnel built).

---

## §5 — Strategy factory throughput targets (proposed; refine as needed)

These are **propositions** for operator approval. Numbers based on current pool size and observed per-fire yield.

### Pool size
- **Today:** 19 candidates in `fql_forge_batch_runner.py CANDIDATES`
- **2026-06-01 target:** 30 (via Gate B graph generator)
- **2026-08-01 target:** 50 (sustainable factory size)

### Candidates tested per week
- **Today:** 25 (5 per weekday × 5 weekdays)
- **Same target through 2026-06.** No cadence increase until Phase 3 validation funnel exists.

### PASS rate
- **Observed:** ~50% (8 PASSes / 15 fires last 3 days; smallest reliable estimate)
- **Stable target:** 30-40% sustained PASS rate. Higher means pool too soft (false PASSes); lower means pool not surfacing edges. Both indicate need to refresh candidates.

### Paper-trading candidates added per month
- **Today:** 0 / month (probation set hasn't moved since 2026-04-13)
- **2026-Q3 target:** 1 / month after Phase 3 funnel stable. The bottleneck is validation rigor, not generation.
- **2026-Q4+:** 2-3 / month if validation infrastructure is mature.

### Registry growth
- **Today:** 163 (88 idea / 8 probation / 3 core / 2 monitor / 26 archived / 36 rejected)
- **2026-06-01 target:** ~200 idea entries (graph generator producing structured exploration; 5-10 added/week as PASSes accumulate)
- **Growth signal:** if `idea` count is growing but `probation`/`core` aren't, validation funnel is the bottleneck (Phase 3 priority)

---

## §6 — Phase progression overview (the operator's 5-phase arc)

### Phase 1 — Autonomous research loop stabilization
**Where we are.** Continues through ~2026-05-17 (Patch A yield assessment).

**Exit criteria:**
- ≥7 clean organic Forge fires
- Patch A assessment complete
- Review load gauge has spent ≥3 consecutive days YELLOW or below

### Phase 2 — Strategy factory expansion
**Estimated:** 2026-05-19 to 2026-06-15 (~4 weeks).

**Builds:**
1. Graph-backed candidate generator (Gate B)
2. Auto candidate-pool proposer
3. Auto-drafted pre-flight packets (Gate C)

**Exit criteria:**
- Graph generator producing ≥5 PASS-candidates from previously-untested combinations
- Auto-pre-flights drafted for ≥3 batch register cycles
- Pool size ≥30

### Phase 3 — Validation funnel
**Estimated:** 2026-06-15 to 2026-07-15 (~4 weeks).

**Builds:**
1. Walk-forward H1/H2 automation per candidate
2. Cross-asset validation matrix (from `project_proven_trio_architecture.md` evidence)
3. Concentration / regime / session profile checks
4. Correlation matrix vs existing probation portfolio
5. Prop-sim eligibility ranker
6. Paper-trading slot recommender (which slots open, which families under target)

**Exit criteria:**
- ≥1 candidate has graduated `idea` → `probation` via the full battery
- Validation suite reproducible (every PASS gets a validation report)

### Phase 4 — Paper-trading expansion
**Estimated:** 2026-07-15 onward, paced.

**Adds:** curated probation candidates that improve diversification, fill gaps, low correlation.
**Pace:** 1-2 / month, gated by validation evidence + 4-week forward-runner verification per addition.

### Phase 5 — Live prop/cash readiness
**Out of scope of this plan; prerequisites tracked separately:**
- Watchdog hardening across all Lane A
- Kill switches per strategy
- Drift monitoring
- Broker/execution checks
- Position reconciliation
- Prop rule simulation (`feedback_validation_gates.md` extended with prop-firm rule layer)
- Daily loss controls

**Earliest realistic Phase 5 start:** 2026-Q4. Operator will gate this separately.

---

## §7 — Safety constraints (locked, do not violate)

These apply through every phase:

1. **No Lane A changes without operator approval.** Live runtime, scheduler, checkpoint, hold-state.
2. **No live/paper expansion until validation criteria are met.** Phase 3 funnel must exist.
3. **No cadence increase while review load is RED.** Build gauge governs build velocity.
4. **No automatic registry status mutations.** All `idea → probation`, `probation → core`, etc., are operator-gated.
5. **No automatic source-helper config mutations** beyond operator-approved patches.
6. **No skipping pre-flight for batch operations.** Surgical pattern (evidence → packet → pre-flight → operator approval → application) remains the standard.

---

## §8 — How this plan stays alive

This file is **a snapshot, not a tracking system.** It will go stale. To keep progression pressure visible:

- Each checkpoint date (§2) should be reviewed when its date arrives — not earlier
- Each gate (§3) should be re-evaluated when its unlock criteria are met
- Phase exit criteria (§6) trigger drafting of the next phase's plan
- Throughput targets (§5) are proposed; operator approves/refines after Phase 1 closes
- File rev: replace this file with `_PROGRESSION_PLAN_2026-XX-XX.md` after Phase 1 closes (likely ~2026-05-17 to 2026-05-20)

---

## §9 — System-wide health & roadmap review — coverage map

**The Monthly System Review (`research/monthly_system_review.py`, fires first Saturday of every month) is the canonical system-wide health and roadmap review.** All other Lane B tools are per-domain specialists that feed into it or run on faster cadences.

This section maps the operator's 7 system-wide review requirements to active tooling so no requirement is buried under vague wording.

### Coverage matrix

| # | Requirement | Primary coverage | Secondary coverage | Status |
|---|---|---|---|---|
| 1 | **Full automation review** (agents expected vs loaded, cadence correctness, log freshness, stderr, tripwires, stale reports) | Monthly system review §7 (Automation Truth Table) — `monthly_system_review.py` | Governance audit §3 (Lane B Self-Healing); Memory hygiene audit (claims vs reality); Morning digest §5 (Forge-specific) | 🟢 STRONG |
| 2 | **Full roadmap review** (built, delayed, needs adding, removed/deferred, alignment with FISH/FQL vision) | Monthly system review §8 (Roadmap Review) + §15 (Recommended Roadmap Edits) | This progression plan | 🟡 MEDIUM — vision-alignment is heuristic in v1.1 (gap below) |
| 3 | **Strategy system review** (registry counts, new candidates, verdict trends, awaiting review, stale probation, components_used/salvaged_from health) | Monthly system review §11 (Registry) + §10 (Forge) | Governance audit §1 (Evidence Absorption); Morning digest §2 + §4 | 🟢 STRONG |
| 4 | **Portfolio/gap review** (asset/family/session/regime coverage, overconcentration, missing families) | Monthly system review §12 (Portfolio / Gap Review) | Existing weekly `portfolio_gap_dashboard.py --save` produces data | 🟡 MEDIUM — data exists, monthly doesn't yet ingest it (gap below) |
| 5 | **Lane A / Lane B safety review** (protected-surface drift, unauthorized changes, Forge stays report-only) | Monthly system review §9 (Lane A Review — watchdog, transitions, forward-runner) | Memory hygiene audit; CLAUDE.md probation roster check | 🟡 MEDIUM — no explicit "diff vs prior month" check (gap below) |
| 6 | **Memory/docs/source-of-truth review** (stale counts, cadence claims, broken paths, missing plists, memory vs repo mismatch) | Memory hygiene audit (`memory_hygiene_audit.py`) — dedicated tool | Monthly system review §13 (thin sample) | 🟢 STRONG |
| 7 | **Recommendations** (keep/change/add/stop, highest-ROI build) | Monthly system review §1 (Executive) + §15 (Roadmap Edits) + §16 (Watchlist) + §18 (Recommendations) | Governance audit summary actions | 🟢 STRONG |

### Cadence map — when each requirement gets reviewed

| Cadence | Review | Tool |
|---|---|---|
| Daily AM | Forge evidence absorption (req #3 partial, #5 partial) | Morning digest |
| Weekly Fri | Integrity / kill criteria / throughput audit (req #1 partial) | `weekly-research` job |
| Ad-hoc | Memory/docs drift (req #6) | `memory_hygiene_audit.py` (manual now; not yet scheduled) |
| Ad-hoc | Review load + Lane B health + cost (req #1 partial, #5 partial) | `governance_audit.py` (manual now; not yet scheduled) |
| **Monthly (1st Sat)** | **Full system-wide health + roadmap review (req #1-7 comprehensive)** | **`monthly_system_review.py` (scheduled)** |

### Gaps explicitly named (added to roadmap below)

Three coverage gaps surfaced when mapping the requirements above. None block Phase 1; all become candidates for Phase 2 or beyond.

#### Gap 1: Vision-alignment scoring is heuristic
**Status:** monthly review §4 (Vision Alignment Score) computes GREEN/YELLOW/RED from PASS yield + cross-pollination flow. Heuristic only.
**v1.2 fix:** parse commit log to compute tooling-vs-strategy commit ratio; flag if tooling >40% of recent commits without registry growth.
**Already in:** monthly review v1.2 backlog (per `_DRAFT_2026-05-05_monthly_system_review_preflight.md` §"v1.2 polish items").
**Roadmap action:** keep in monthly review v1.2 backlog; trigger when monthly review needs its first refresh (~2026-06 after first organic fire).

#### Gap 2: Portfolio gap dashboard data not yet ingested by monthly review
**Status:** weekly job runs `python3 scripts/portfolio_gap_dashboard.py --save` and writes to `research/reports/portfolio_gap*.md`. Monthly review §12 only counts assets/families/sessions from registry; doesn't read the saved dashboards.
**v1.2 fix:** monthly review §6 reads `research/reports/portfolio_gap*.md` latest output and surfaces top-3 gaps inline.
**Already in:** monthly review v1.2 backlog (per pre-flight memo).
**Roadmap action:** keep in monthly review v1.2 backlog.

#### Gap 3: No explicit "Lane A diff vs prior month" check
**Status:** monthly review §9 reports current Lane A state (watchdog, transitions, log freshness). It does NOT explicitly compute "what changed in Lane A vs last month's snapshot."
**Risk:** if Lane A drift occurs (unauthorized scheduler change, surprise registry mutation, hold-state edit), it would surface only by comparing current state to memory — which is the current expectation but not automated.
**v1.2 fix:** monthly review compares prior-month `.snapshots/YYYY-MM_snapshot.json` Lane A fields against current; flags any registry-status-count change, any new launchd agents, any forward-runner config change.
**NOT yet in any backlog.** **Adding to roadmap as new item.**
**Roadmap action:** queue as monthly review v1.2 polish item alongside Gaps 1 + 2. Effort: SMALL (snapshot diff). Safety: HIGH (drift detection).

### What this section commits to

1. **The monthly system review is THE system-wide health and roadmap review.** Other tools are specialists; the monthly is the canonical synthesis.
2. **Every requirement in the operator's list (§1-7) maps to at least one active tool today.** No silent blind spots.
3. **Every gap (Gaps 1-3 above) is named and queued.** Drift between "we said we'd cover X" and "X is actually being checked" is itself a tracked failure mode now.
4. **Cadence map (above) sets reviewer expectations.** Daily, weekly, monthly all serve different review depths; monthly is the only comprehensive layer.

---

## §10 — Bottom line

Autonomous machine: **running.** Build gauge: **RED** (governance working). Forward pressure: **visible**, with named dates and named gates.

The gap between "stop building" and "stop progressing" is closed by:
- The autonomous machine continuing to test, digest, and surface evidence (no human work needed)
- The Patch A review checklist defining what to do at each checkpoint (no improvisation needed)
- The phase progression making clear what comes next once governance allows it (no roadmap drift)

This is how the system moves faster without getting sloppy.

---

*Filed 2026-05-08. Lane B / governance. Read-only forward-looking artifact. No mutation of any active surface. Replaces no existing artifact; supplements `roadmap_queue.md`, `feedback_closed_loop_over_cadence.md`, `_DRAFT_2026-05-07_patch_a_review_checklist.md`.*
