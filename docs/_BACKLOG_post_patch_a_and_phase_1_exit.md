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

## §2 — Phase 1 exit criteria status (per `_PROGRESSION_PLAN_2026-05-08.md`)

| Criterion | Required | Current | Status |
|---|---|---|---|
| Clean organic Forge fires | ≥7 | 6 (5/5, 5/6, 5/7, 5/8, 5/11, 5/12) | 7th lands tonight 5/13 19:00 PT |
| Patch A assessment complete | — | Tonight 5/13 21:00 PT | On track |
| Review load YELLOW or below ≥3 consecutive days | 3 | Day 3 today (Mon GREEN, Tue GREEN, Wed GREEN after closeout) | **Criterion met by EOD today** |

**Phase 1 exits Thu 2026-05-14 or Fri 2026-05-15** if tonight is clean.

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

## §4 — Forge build packet (apply after Phase 1 exit, in this order)

Three-party convergence (Claude + GPT + operator) on the post-Phase-1 build sequence:

| # | Item | Lane | Effort |
|---|---|---|---|
| 1 | **Evidence-tier labels in all Forge reports** — `PASS — Cheap Screen Tier` etc. Forward-only (no historical rewrite). | Lane 2 | ~30 min |
| 2 | **Correlation matrix in cheap-screen + retroactive run on the 12 forge-hybrid registry entries** — Lane 2 for analysis; Lane 3 if registry reclassification needed | Lane 2 | ~1 session |
| 3 | **Cost/slippage model with edge cushion** — gross PF / net PF / avg trade / cost % / minimum edge cushion (slippage multiplier where PF crosses 1.0) | Lane 2 | ~1 session |
| 4 | **Pool hygiene** — fix `donchian_breakout` engine bug; add reproducibility tracking (random seed? data refresh? code drift?) | Lane 2 | ~1 session |
| 5 | **Stale-WATCH thresholds + mutation lane v0** — 2 = low-yield flag, 3 = prune/mutate/hold decision, 4 = auto-remove unless overridden | Lane 1-2 | ~1 session |
| 6 | **Minimal validation funnel v0** — H1/H2 split, walk-forward/OOS, cost model, trade-count minimum, correlation check, session/regime/year concentration. Not the whole cathedral. | Lane 3-4 | ~4 sessions |

### Restrictions during this packet

- No harvest expansion
- No pool inflation just to hit 30
- No registry promotion based on cheap-screen alone
- No paper-readiness decisions
- No graph generator before correlation exists
- No expansion of source-helper queries beyond Patch A scope

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
