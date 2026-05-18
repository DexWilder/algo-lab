# Backlog: Post-Patch-A + Phase 1 Exit Cleanup

**Filed:** 2026-05-13
**Type:** Durable backlog (paired with memory copy in `~/.claude/projects/-Users-chasefisher/memory/project_fql_state.md`)
**Authority:** Reference / pre-decisional. All items below require operator approval before execution.
**Purpose:** Single repo-side audit document for everything queued during the Phase 1 stabilization period that will land after Patch A second-fire decision + Phase 1 exit.

---

## §1 — Patch A decision tonight (2026-05-13 ~21:00 PT)

**Template:** `docs/_DRAFT_2026-05-13_patch_a_second_fire_decision.md`
**Decision framing locked:** *"Did GitHub surface TRANSFER-aligned leads under Patch A, or is TRANSFER better routed through another surface?"* Per `feedback_channel_vs_thesis.md`.
**Five options:** CONTINUE / PARTIAL TRIM / SHIFT SURFACE / FULL REVERT / WAIT.

Outcome determines ledger update for `a95ac91` + `77e1e5f` and triggers everything in §3-§5 below.

---

## §2 — Phase 1 exit confirmed 2026-05-14 ✅

| Criterion | Required | Final | Status |
|---|---|---|---|
| Clean organic Forge fires | ≥7 | 7 (5/5, 5/6, 5/7, 5/8, 5/11, 5/12, 5/13) | ✅ |
| Patch A assessment complete | — | DECISION RENDERED 2026-05-14 (commit `a77dadf`); SHIFT SURFACE | ✅ |
| Review load YELLOW or below ≥3 consecutive days | 3 | 4 (Mon GREEN / Tue GREEN / Wed GREEN-after-closeout / Thu GREEN) | ✅ |

**Phase 1 EXITED 2026-05-14 morning.**

### Phase 1 outcomes summary

- ✅ Closed-loop tier 2 mature: scheduled testing → digest absorption → source-priority feedback applied
- ✅ All Lane B governance tooling shipped: governance_audit (with acknowledgment ledger), memory hygiene audit, morning digest with snapshot mechanism, Forge → source-helpers feedback layer, monthly system review v1.1 (awaiting first organic fire 6/6)
- ✅ Doctrine framework fully stabilized: 4-lane action model, RED/YELLOW/GREEN with recovery mode, channel-vs-thesis distinction, durable-artifacts-both-surfaces
- ✅ Patch A SHIFT SURFACE decision proves channel-vs-thesis doctrine in production
- ✅ 7 clean organic Forge fires; rotation working; pool of 19 candidates fully cycled
- ✅ Registry stable at 163 (0 unauthorized mutations across Phase 1)
- ✅ Zero tripwires fired; zero Lane A drift events
- ✅ Operator review-load metric working (Lane 2 governance bug fix landed; acknowledgment ledger discount mechanism functioning)

### Phase 2 build sequence now ELIGIBLE

Per `_PROGRESSION_PLAN_2026-05-08.md` §6, Phase 2 is "Strategy factory expansion" — estimated 2026-05-19 to 2026-06-15. Three queued builds:

1. **Graph-backed candidate generator** — biggest unlock; requires correlation matrix (item §4 #2) as prerequisite input
2. **Auto candidate-pool proposer** — operator-approved drafts of pool additions
3. **Auto-drafted pre-flight packets** — eliminates manual pre-flight authoring

Per the post-Phase-1 build sequence (operator-approved 2026-05-13), the actual ORDER is the 6-item Forge build packet in §4 below, not the Phase 2 trio above. Phase 2 trio is "later" in §4 sequencing (graph generator after correlation; auto-pre-flights after that).

### Cleanup packet now ACTIVE

The 8 doctrine items + 3 hygiene items + 6 Forge build items + 5 monthly-review-v1.2 priority sections (§3-§5 of this doc) are now ELIGIBLE to execute. **Operator authorizes individual items; nothing auto-executes.**

---

## §3 — Doctrine cleanup packet (apply at Phase 1 exit)

### ✅ Locked NOW (2026-05-13, single memory edits, no repo doc needed)

- `feedback_channel_vs_thesis.md` — harvest thesis ≠ harvest channel
- `feedback_durable_artifacts_both_surfaces.md` — memory + repo for durable artifacts (the doctrine this file embodies)

### 🕐 Queued for Phase 1 exit cleanup (8 doctrine items + 3 hygiene items)

**Hygiene additions (operator-elevated 2026-05-13):**

- **HYG-1: Condense `project_fql_state.md`** (currently 27 KB and bloated). Reduce to current state + active queues + open future-evidence gates + next checkpoints + standing doctrine references. Move historical narrative to a separate `_HISTORY_*.md` archive doc. Prevents hidden-confusion drift on session start.
- **HYG-2: `_DRAFT_*.md` lifecycle convention.** Decide what happens to: (a) active drafts (stay as `_DRAFT_`), (b) executed decision docs (become `_DECISION_` or move to `docs/decisions/`), (c) superseded drafts (delete or move to `docs/archive/preflights/`), (d) reusable templates (move to `docs/templates/`). Prevents docs folder bloat as pre-flight count grows.
- **HYG-3: Decision artifact lifecycle convention.** Every major decision packet gets the lifecycle: **draft → decision → action → verification → archive/reference.** Applies to: Patch decisions, registry proposals, source-helper changes, phase exits, validation promotions, paper/live decisions. Each packet should be inspectable across all 5 stages with paired artifacts. Fits the "more truthful Forge" direction because every decision has an evidence trail and an outcome.

**Doctrine items (8):**

1. **UPDATE `feedback_validation_mode.md`** → rename to "Discovery-and-Validation Mode." Cheap-screen PASS is not deployment proof.
2. **CONDENSE `feedback_assembly_architecture.md`** → keep meta-principle ("don't build recombination before validated components exist"); remove executed sequencing.
3. **ADD: Candidate-canonical review doctrine** → monthly system review is *candidate* canonical until first organic fire produces an actionable finding the operator acts on.
4. **ADD: Pre-flight challenge-layer doctrine** → every major pre-flight must include strongest counter-argument + what would prove it wrong + reversal criteria.
5. **ADD: Closed-loop Tier 3 doctrine** → failed validation should down-weight similar future candidate generation.
6. **ADD: Phase progression doctrine** → phases are evidence gates, not calendar goals.
7. **ADD: Evidence hierarchy doctrine** → Live > Paper > Forward > Walk-forward/OOS > Robustness > In-sample > Cheap-screen PASS > Harvest idea. Don't let cheap-screen PASS psychologically equal validated edge.
8. **ADD: Promotion humility doctrine** → every strategy promotion must explicitly answer "what would make this fail after promotion?" (correlation / regime / session / data artifact / slippage / parameter fragility / prop-rule / duplicate exposure).

### Plus the cross-doctrine summary phrase to lock

> **"More truthful Forge before more productive Forge."** — Locked as doctrine tagline.

> **"Forge currently produces cheap-screen evidence, not validated edge evidence."** — Operating doctrine for everything that follows.

---

## §4 — Phase 2: PAPER-READINESS SPRINT (reframed 2026-05-18)

**Reframe locked 2026-05-18:** Phase 2 is no longer "better Forge infrastructure." It is a **30-day Paper-Readiness Sprint** with one scoreboard:

> **"How many candidates moved closer to paper trading?"**

NOT: commits per day / reports generated / governance cleanliness / registry size / doctrine count. See `feedback_paper_readiness_sprint.md` for the full doctrine.

**Deliverable:** 1-3 paper-readiness packets within 30 days (target: by 2026-06-17).

**Each packet:** APPROVE / DEFER / REJECT decision with evidence tier, correlation analysis, cost-adjusted metrics, walk-forward outcome, concentration check, promotion humility section, failure modes, remaining blockers.

### Candidate-readiness scoring (13 pts)

| Gate | Weight |
|---|---:|
| Cheap-screen PASS | 1 |
| Correlation cleared (not duplicate) | 1 |
| Cost-adjusted net PF ≥ 1.15 | 2 |
| Walk-forward H1/H2 > 1.0 | 3 |
| Trade count adequate | 1 |
| Concentration check passed | 2 |
| Forward-runner trades ≥30 | 2 |
| Promotion humility packet | 1 |

≥10 pts qualifies for paper consideration; ≥8 pts qualifies for DEFER decision; current 12 candidates at 1/13 each.

### Sprint sequence (~9.5 sessions over 30 days)

| # | Step | Sessions | Status |
|---|---|---|---|
| 1 | Evidence-tier labels in Forge reports | — | ✅ DONE (commit `17b98a2`, verified 2026-05-15) |
| 2 | Correlation matrix on 12 registered 2026-05-06 candidates | 1 | Spec locked 2026-05-18 (this conversation §1-§8) |
| 3 | Deduplicate the 12 into a clean candidate set | (part of #2) | Output of #2; do NOT pick top-3 from raw 12 |
| 4 | Lock 2 doctrine items (memory only, no big build): evidence hierarchy + promotion humility | 0.5 | Required for paper packets |
| 5 | Cost/slippage model: gross PF / net PF / avg trade / cost % / minimum edge cushion | 1 | |
| 6 | Minimal pool hygiene: donchian fix + reproducibility flag | 0.5 | Don't expand scope |
| 7 | **Validation funnel v0** — heaviest item | 4 | H1/H2 + cost-adjusted PF + trade count + max DD + concentration + correlation re-check |
| 8 | Select top-3 candidates from clean + validated set | 0.5 | |
| 9 | Produce 3 paper-readiness packets | 2 | THE DELIVERABLE |

### Three refinements locked into the sequence

1. **Deduplicate before top-3** — XB-ORB-Chandelier-MNQ vs XB-ORB-TimeStop-MNQ are likely 85-95% correlated. Selecting top-3 from raw 12 risks fictional diversification.
2. **Promotion humility locks BEFORE first paper packet** — the packet structure requires the doctrine.
3. **Validation funnel v0 is the heavy/core item** — ~4 sessions of real engineering. Don't pretend it's minor.

### How to apply when uncertain

Ask: *"Does this commit/build move at least one candidate closer to paper-readiness scoring?"*
- Yes → in scope
- No → defer to post-sprint queue

## §4-OLD — Prior Forge build packet (superseded 2026-05-18)

The earlier 6-item build packet (originally §4) is **superseded by the Paper-Readiness Sprint above.** The items themselves remain valid; their priority shifted. The new §4 sequence above subsumes items 1-5 (evidence-tier labels, correlation, cost/slippage, pool hygiene, stale-WATCH) and explicitly adds validation funnel + paper-readiness packets.

---

## §4-DEFERRED — Items removed from Phase 2 sprint (resume after sprint)

These were on the original §4 build packet but are now explicitly deprioritized during the 30-day sprint (per the 2026-05-18 reframe). Resume after paper packets ship.

- Graph-backed candidate generator (Phase 2 unlock under prior plan)
- Source-yield memory build
- Monthly review v1.2 expansion (let v1.1 fire organically 6/6 without changes)
- Stale-WATCH pruning + mutation lane v0 (resume unless blocks validation)
- 6 of 8 doctrine cleanup items (defer; only evidence hierarchy + promotion humility lock during sprint)
- `_DRAFT_*.md` lifecycle conventions
- `project_fql_state.md` condensation
- Source-helper expansion (no Patch B/C work during sprint)
- Candidate pool expansion to 30

### Restrictions during the sprint

- No harvest expansion
- No pool inflation just to hit 30
- No registry promotion based on cheap-screen alone (paper-readiness packets ARE allowed and ARE the deliverable)
- No graph generator before correlation exists
- No expansion of source-helper queries beyond Patch A scope
- No new feature work that doesn't move at least one candidate closer to paper-readiness scoring

## §4-HISTORICAL — Original 6-item build packet (superseded 2026-05-18 by paper-readiness sprint)

The prior §4 sequence (operator-approved 2026-05-13) was reframed on 2026-05-18 into the Paper-Readiness Sprint above. The items themselves remain in the sprint sequence — only the priority framing changed (infrastructure-first → deliverable-first). For audit purposes, the original 6-item list:

| # | Item | Lane | Effort |
|---|---|---|---|
| 1 | Evidence-tier labels | Lane 2 | ~30 min — ✅ DONE |
| 2 | Correlation matrix + retroactive on 12 | Lane 2 | ~1 session — now sprint step 2-3 |
| 3 | Cost/slippage model with edge cushion | Lane 2 | ~1 session — now sprint step 5 |
| 4 | Pool hygiene (donchian + reproducibility) | Lane 2 | ~1 session — now sprint step 6 |
| 5 | Stale-WATCH thresholds + mutation lane | Lane 1-2 | ~1 session — DEFERRED to post-sprint |
| 6 | Minimal validation funnel v0 | Lane 3-4 | ~4 sessions — now sprint step 7 |

Net change: 5 of 6 items roll into the sprint (in slightly different sequence); 1 (stale-WATCH) defers.

---

## §5 — Monthly review v1.2 backlog (do NOT implement before 2026-06-06 organic fire)

Three-party convergence. Wait until v1.1 fires organically on 2026-06-06 before evaluating.

### 5 priority additions to evaluate after 6/6

1. **Doctrine review** — are the rules still right?
2. **Forge / algo-building process improvement review** — how to improve generation & testing?
3. **Evidence quality review** — overweighting weak evidence?
4. **Source-yield conversion funnel review** — source → harvest → triage → candidate → cheap-screen → validation → paper. Where do leads die? Which channels produce useful candidates vs volume?
5. **Prior-month recommendation follow-through** — what did last month's recommendations produce? Which were acted on? Did the review create useful decisions or just more report text? **Makes monthly review accountable.**

### 6 deferred enhancements (enhance existing sections rather than adding new)

- Portfolio usefulness → enhance §12 with overlap/correlation
- Review burden → cross-link governance_audit
- Roadmap kill-list → sharpen §15 + Watchlist with subtraction discipline
- Mission alignment → enhance §4 with concrete inputs (factor mix; tooling vs strategy commit ratio; validation funnel coverage; paper-readiness gate count; distance from prop-firm readiness)
- System health → already in §7 (no action)
- Validation funnel review → defer until Phase 3 funnel exists
- Security/deployment → quarterly until paper/live nears

### Cadence rule

- Daily/weekly checks stay daily/weekly (don't duplicate in monthly)
- Per-decision checks stay per-decision (don't duplicate)
- Monthly summarizes + diagnoses, doesn't duplicate lower-cadence reports

### Implementation discipline

- "Comprehensive enough to catch drift; lean enough to be read and acted on"
- Choose only 3-5 highest-leverage additions after 6/6 evidence
- Risk to avoid: 27-section wall-of-text instead of high-signal decision review

---

## §6 — Watchlist items (preserve as low-priority signal)

- **XB-BB-EMA-AfternoonOnly-MGC** has PASSed 3× (5/8, 5/11, 5/13 morning digest reading 5/8 fire showed 1.191; 5/11 morning digest reading 5/8 showed it again). Originally DEFERRED at batch register as subset duplicate. Reconsider after Patch A.
- **4 stale-WATCH candidates** flagged ⚠️ low yield: `XB-PB-EMA-Ladder-MES` (3× WATCH), `XB-PB-EMA-Ladder-MGC`, `XB-ORB-EMA-MorningOnly-MNQ`, `XB-ORB-EMA-AfternoonOnly-MNQ`, `XB-PB-EMA-MorningOnly-MNQ`, `XB-ORB-EMA-MidlineTarget-MNQ`. Pool consolidation candidates post-Patch-A.

---

## §7 — Open governance items (active, not queued)

| Item | Status | Resolution |
|---|---|---|
| Patch A Wed 5/13 review | Due tonight 21:00 PT | Template ready at `docs/_DRAFT_2026-05-13_patch_a_second_fire_decision.md` |
| Treasury wrapper fix (`933e6a2`) | DEFERRED until 2026-06-01 | First-business-day Treasury-Rolldown rebalance |
| First organic monthly system review | Scheduled 2026-06-06 09:00 PT | First-Saturday self-guard |

---

## §8 — Cross-reference table

| Subject | Memory canonical | Repo paired (this file) | Tool |
|---|---|---|---|
| Doctrine | `~/.claude/projects/...memory/feedback_*.md` (29 files) | This backlog has the cleanup queue | — |
| Project state | `project_fql_state.md` (27 KB; due for condense at Phase 1 exit) | This backlog mirrors §3-§5 | — |
| Governance audit ledger | — (artifact lives in repo) | `docs/reports/governance/_acknowledgments.json` | `research/governance_audit.py` |
| Forge daily reports | — | `research/data/fql_forge/reports/forge_daily_*.{json,md}` | `research/fql_forge_daily_loop.py` |
| Morning digest reports | — | `docs/reports/fql_forge_morning_digest/*.md` | `research/fql_forge_morning_digest.py` |
| Patch A decision template | — | `docs/_DRAFT_2026-05-13_patch_a_second_fire_decision.md` | — |

---

*Filed 2026-05-13. Paired with `~/.claude/projects/-Users-chasefisher/memory/project_fql_state.md`. Both surfaces will be updated when items move from queued → completed.*
