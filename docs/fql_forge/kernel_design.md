# FQL Forge — Always-On Kernel Design (v1)

**Status:** Design only. No code changes. Drafted 2026-04-16 during the
2026-04-14 → 2026-05-01 hold window. Implementation deferred to a
post-checkpoint go/no-go after May 1.

**Purpose:** Convert FQL Forge from a daily human operating practice into
a continuous offline research engine. Lane B runs hot at all times wherever
local historical data exists; Lane A stays protected and gated.

**Expected impact:** Replace twice-weekly batch model with continuous
gap-targeted research. Time-to-validation for a candidate drops from
~3–4 days (next twice-weekly fire + Friday rollup) to hours. Selectivity
ensures the throughput is signal, not noise.

**Anchoring direction:** see memory `feedback_forge_always_on.md`,
`docs/LANE_A_B_OPERATING_DOCTRINE.md`, and the standing principles
(elite standard, continuous discovery, selective deployment). Selectivity
(gap-targeted work) is part of the kernel, not a downstream filter.

This document specifies six things:

1. Kernel components and how they map to existing code
2. Cadence layer 0 (machine pacing) under existing layers 1–4
3. Selectivity policy — the engine is gap-driven, not brute-force
4. Guardrails / anti-sprawl controls
5. Artifact and state outputs (file paths, schemas)
6. How the kernel stays hot without producing junk or fake motion

Plus: implementation gating, v1.1 evidence-driven refinements, and v2
open questions.

---

## 1. Kernel components

The kernel is a fixed set of services that run on schedules. Most exist
as code already; the kernel adds a thin orchestrator + state files +
selectivity wiring around them. Components in **bold** need no new
implementation logic; only scheduling and state plumbing.

| # | Component | Existing code | New work |
|---|-----------|---------------|----------|
| 1 | **Intake / harvest loop** | `research/harvest_engine.py --scan/--run` | Kernel-driven invocation; rate-limit |
| 2 | **Gap detector** | `research/data/strategy_genome_map.json` | Read-only consumer; selectivity wiring |
| 3 | Candidate generator | — (logic embedded in evolution + crossbreeding) | New thin layer: pick gap → route to generator → enqueue |
| 4 | **Crossbreeder** | `research/crossbreeding/crossbreeding_engine.py` | Gap-targeted invocation |
| 5 | **Mutation engine** | `research/evolution/mutations.py` + `evolution_scheduler.py` | Gap-targeted invocation |
| 6 | **Batch backtest runner** | `research/batch_first_pass.py` + `research/mass_screen.py` | Continuous-throttled invocation |
| 7 | **Validation battery scheduler** | `research/validation/run_validation_battery.py` | New: queue drainer for FIRST_PASS_PASSED items |
| 8 | Result logger / registry writer | `research/data/strategy_registry.json`, `research/data/first_pass/` | Reuse existing writers; add cycle log |
| 9 | Stale queue sweeper | `docs/fql_forge/stale_checks.md` (currently manual) | Promote rules 2/4/5/8/9 to code; emit findings only |
| 10 | Integrity monitor | `docs/fql_forge/anti_drift_checks.md` (currently manual) | Promote 4 metrics to code; emit health JSON |

**Net new code surface (design only — to be validated at impl):**

- `research/forge_kernel/orchestrator.py` — top-level scheduler/dispatcher
- `research/forge_kernel/selector.py` — gap → generator routing (rule-budget aware)
- `research/forge_kernel/cycle_log.py` — append-only cycle journal
- `research/forge_kernel/queue.py` — typed queue with WIP caps + dedup
- `research/forge_kernel/integrity.py` — yield/noise + anti-drift metrics
- `research/forge_kernel/stale.py` — codified stale rules
- `research/forge_kernel/digest_hook.py` — emits kernel section into operator digest
- 1 new launchd plist for the kernel tick
- Kernel state files (see §5)

Existing engines are imported and called as libraries. Nothing in
`engine/`, `strategies/`, or the existing `research/data/strategy_*.json`
schema changes.

### Nomenclature

- **Cycle** — one fired iteration of a Layer 0c work cycle. Has a unique `cycle_id`.
- **Candidate** — a strategy variant produced by a generator inside a cycle. Lives in pre-validation queue until first-pass result.
- **Strategy** — a candidate that passed first-pass and got a registry entry. May or may not advance to validation battery.
- **Promotion candidate** — a strategy that passed validation battery; awaits operator review for probation.

---

## 2. Cadence — Layer 0 under existing layers

Existing cadence (human-paced, in `docs/fql_forge/cadence.md`):

- Layer 1: daily operating cadence (operator)
- Layer 2: weekly review (operator)
- Layer 3: biweekly source expansion (operator)
- Layer 4: integrity self-check (operator + automation hooks)

The kernel adds Layer 0 underneath — machine pacing. Layers 1–4 are
unchanged. Layer 0 produces inputs and metrics that Layer 1 reads each
morning.

### Layer 0 cadence

| Sub-layer | Period | Job | Bounded by |
|-----------|--------|-----|------------|
| 0a — tick | 15 min | Claw inbox scan + dedup intake | already exists in `claw_control_loop.py`; kernel adds intake-only mode at 15 min |
| 0b — short cycle | hourly | Stale sweeper + integrity heartbeat | <60s wallclock budget |
| 0c — work cycle | every 2h | Selector picks 1 gap → generator → backtest queue | hard cap: ≤5 candidates enqueued per cycle |
| 0d — drain | every 4h | Backtest runner drains queue; validation runner drains FIRST_PASS_PASSED | compute budget ≤30 min wallclock |
| 0e — daily | 02:00 ET | Crossbreeding pass on validated parents (one family per day, rotating) | hard cap: ≤10 hybrids per pass |
| 0f — daily | 03:00 ET | Yield report → writes `forge_yield_daily.json` for operator | <2 min |

**Why these intervals (and not faster):**

- 15-min tick is fast enough for Claw output to flow without operator wait
- 2h work cycle gives time for a backtest cohort to actually finish before the next batch arrives — prevents queue pileup
- 4h drain matches typical backtest+validation runtime for 5–10 candidates on owned data
- Daily crossbreed is rotated by family so each family gets attention weekly without flooding the queue
- Nothing runs every minute; "always on" ≠ "always firing"

### Pause windows (mandatory)

Kernel does NOT fire any Layer 0 sub-layer during these windows:

- **17:00–17:30 ET weekdays** — forward-trading agent runs (Lane A)
- **17:30–18:00 ET weekdays** — daily research agent runs
- **18:00–19:00 ET Tue/Thu** — twice-weekly research + mass_screen
- **18:30–19:30 ET Fri** — weekly research rollup
- **2026-04-30 00:00 ET → 2026-05-02 00:00 ET** — Treasury-Rolldown May 1 verification carveout. Operator attention belongs to Lane A; kernel resumes after checkpoint.

Pause is mode change, not shutdown. Kernel writes
`forge_kernel_state.json.mode = "paused"`, `pause_reason = "<window>"`,
and resumes on next tick after window ends.

### How Layer 0 interacts with existing scheduled agents

| Existing agent | Schedule | Status under kernel |
|----------------|----------|---------------------|
| `com.fql.claw-control-loop` | 30 min | Unchanged. Kernel intake is additive, not replacement. |
| `com.fql.daily-research` | weekday 17:30 | Unchanged. Kernel daily yield report at 03:00 is supplementary. |
| `com.fql.twice-weekly-research` (mass_screen) | Tue/Thu 18:00 | **Demoted to safety net.** Kernel work cycles handle the same job continuously. Twice-weekly stays as weekly catch-all to detect anything the kernel missed. |
| `com.fql.weekly-research` | Fri 18:30 | Unchanged. Reads kernel cycle log + integrity JSON for rollup. |
| `com.fql.forward-trading` | weekday 17:00 | Unchanged. Lane A. |
| `com.fql.watchdog` | 5 min | Add kernel heartbeat to its checks. |

### Reconciliation with the existing 5-state queue (`docs/fql_forge/queues.md`)

The 5-state model (Inbox / In Progress / Validation / Validated / Rejected)
is the **operator-facing** view. Kernel queues (pre-validation backtest,
validation battery) are **sub-states inside "In Progress"**. They roll up
to the operator-facing view; they don't replace it. When kernel writes
state, it also updates the operator-facing position.

---

## 3. Selectivity policy

Always-on without selectivity = junk factory. The selector is the gate
that prevents that.

### Selector input (read every work cycle, 0c)

- `research/data/strategy_genome_map.json` — current gap list
- `research/data/strategy_registry.json` — current strategy inventory + status
- `docs/PORTFOLIO_TRUTH_TABLE.md` (parsed sections) — open portfolio gaps
- `research/data/forge_kernel/strategy_memory.json` — failed-but-salvageable list
- `research/data/forge_kernel/recent_yield.json` — last N cycle outcomes (for adaptive throttling)
- `research/data/forge_kernel/rule_budget.json` — running consumption per selector rule
- `research/data/forge_kernel/forge_priority.txt` — operator override (optional)

### Selectivity priority — weekly budget per rule (NOT first-match)

Earlier draft used first-match-wins. That had a structural flaw: rules 2–3
(portfolio + regime gaps) almost always have qualifying targets, so rules
5/6/7 would never fire. Rule 7 in particular (validated-parent recombination)
is the empirical workhorse path that built the XB-ORB family — putting it
last under first-match would prevent the engine from doing what has
historically worked best.

Replace with weekly budget per rule:

| Rule | Weekly budget | What it targets |
|------|---------------|-----------------|
| 1 | as needed | Operator-flagged via `forge_priority.txt` |
| 2 | 25% | Critical portfolio gap (PORTFOLIO_TRUTH_TABLE) |
| 3 | 25% | Regime gap (genome map cell, current strategies underperform) |
| 4 | 15% | Asset gap with owned local data |
| 5 | 10% | Time-of-day / session gap |
| 6 | 10% | Salvageable failed idea (strategy memory) |
| 7 | 15% | Validated parent recombination |

Selector picks the rule whose budget is most under-consumed (relative to
weekly target), then picks the best target within that rule. Budget
resets weekly Sunday 00:00 ET. Unused budget → integrity flag
`UNUSED_BUDGET:rule_<n>` → operator review (signals exhausted source for
that rule type, possibly time to expand source map).

### Selector output (one per work cycle)

A single **target spec**:

```json
{
  "cycle_id": "fk-2026-04-17T14:00:00-04:00-c03",
  "fired_at": "2026-04-17T14:00:00-04:00",
  "selector_rule": 3,
  "rule_budget_remaining": 0.41,
  "target_gap": {
    "type": "regime_gap",
    "key": "commodity+afternoon+mean_reversion",
    "rationale": "Genome map shows 0 strategies in cell; portfolio truth table flags energy gap",
    "cooldown_state": "active"
  },
  "generator": "mutation",
  "parent_or_seed": "xb_orb_ema_ladder|MCL|baseline",
  "budget": {
    "max_candidates": 5,
    "max_compute_minutes": 25
  },
  "skip_if": [
    "queue_pre_validation > 30",
    "recent_yield_streak < 0.05",
    "gap_key_in_cooldown"
  ]
}
```

### Why weekly budget, not first-match or RL

- **vs first-match:** weekly budget guarantees every rule path gets exercised; surfaces source exhaustion as a flag rather than silent starvation
- **vs RL:** v1 keeps the selector explicit and inspectable. Every cycle log entry names which rule fired and budget remaining. Drift is trivially diagnosable. Learned routing is v2+ once we have cycle data to evaluate it

---

## 4. Guardrails / anti-sprawl controls

The selector chooses *what* to work on. Guardrails bound *how much* and
*how aggressively* — so a buggy selector can't melt the queue.

### Queue caps

| Queue / counter | Cap | Behavior on cap |
|-----------------|-----|-----------------|
| Pre-validation backtest queue | 30 items | Reject new enqueue; selector skips work cycle until drained < 20 |
| Validation battery queue | 15 items | Reject new enqueue; selector skips until drained < 10 |
| Crossbreed candidates per family per week | 25 | Family rotation skips that family for the week |
| Mutation candidates per parent per day | 8 | Selector picks different parent next cycle |
| Total registry adds per day | 20 | Hard ceiling; surfaces ALERT if hit 3 days in a row |
| **Daily compute budget (all cycles combined)** | **180 min wallclock** | **Kernel enters paused mode until 00:00 ET reset; surfaces ALERT** |
| Per-cycle compute budget | 30 min wallclock | Runner kills jobs that exceed; logs `BUDGET_EXCEEDED` |

### Dedup before enqueue

Every candidate hashes:

- **Genome 9-tuple** → if a registered strategy already occupies the cell, require novelty score > 0.30 (novelty = parameter-space distance to nearest existing entry, computed by selector)
- **Parameter signature** → reject exact param matches against registry
- **Strategy logic hash** → AST-normalized (whitespace + var renames stripped) hash of strategy file; reject byte-equivalent regenerations

### Hard prohibitions (kernel cannot do these — period)

- Touch any file under `state/` (account state, data update state)
- Modify any `*_state.json` outside `research/data/forge_kernel/`
- Modify `engine/strategy_universe.py` probation list
- Modify `research/data/portfolio_activation_matrix.json`
- Modify the `status` field of any existing entry in `research/data/strategy_registry.json` (only append new entries)
- Edit any file in `strategies/` (only generates new files in `research/evolution/generated_candidates/`)
- Promote a strategy to probation (operator-only — see §6.4)
- Run `git commit` or `git push` (auto-commits would pollute history; operator commits kernel state if desired)
- Run during any pause window (§2)

### Soft throttles (yield-driven)

If `recent_yield_streak < 0.05` (last 20 cycles produced <5% advance
rate), selector enters **conservative mode**:

- skip rule 7 entirely
- raise novelty score threshold from 0.30 → 0.50
- halve enqueue caps
- emit `LOW_YIELD_THROTTLE` to integrity JSON

Conservative mode auto-clears after yield ≥ 0.10 over 3 consecutive cycles
(v1 default — flagged as v1.1 refinement candidate, see §9).

### Graduated gap-key cooldown

Same `gap_key` targeted with zero advance triggers a cooldown:

- 3 cycles in 24h with zero advance → 1-day cooldown
- 5 cycles in 72h with zero advance → 3-day cooldown
- 8 cycles in 7d with zero advance → 7-day cooldown

Cooldown means selector skips that key when picking targets within its
rule. Operator can manually clear via `forge_priority.txt`.

### Stop-the-world halt

Operator can fully stop the kernel by creating empty file
`research/data/forge_kernel/forge_kernel_halt`. Kernel checks for this on
every tick; if present, exits cleanly (writes `mode = "halted"`, completes
in-flight cycle if safe, then sleeps until file removed). This is the
emergency switch — cleaner than disabling launchd.

### Generator exception handling

Any generator (mutation, crossbreeding, validation) that raises an
unhandled exception inside a kernel cycle:

1. Exception caught by orchestrator
2. Cycle marked `outcome: FAILED`, exception type + first-line of traceback logged
3. Kernel continues to next sub-layer (does NOT halt)
4. If same generator FAILS 3+ times in 24h → that generator is auto-disabled and surfaces ALERT

---

## 5. Artifact / state outputs

All kernel state lives under `research/data/forge_kernel/`. Existing
state files are unchanged.

### State files

| File | Type | Updated by | Read by |
|------|------|-----------|---------|
| `forge_kernel_state.json` | snapshot | every tick | watchdog, operator digest |
| `forge_cycle_log.jsonl` | append-only | every cycle | weekly rollup, operator |
| `forge_queue_state.json` | snapshot | every enqueue/drain | selector, operator |
| `forge_integrity.json` | snapshot | hourly | operator digest, watchdog |
| `forge_yield_daily.json` | snapshot | daily 03:00 | weekly rollup, digest |
| `forge_promotion_candidates.json` | append + operator-clear | validation runner | operator |
| `forge_rule_budget.json` | snapshot | every selector fire | selector, integrity |
| `strategy_memory.json` | append-on-rejection | validation runner | selector (rule 6) |
| `forge_priority.txt` | operator-edited | operator only | selector (rule 1) |
| `forge_kernel_halt` | operator-created | operator only | every kernel tick |
| `archive/forge_cycle_log_<week>.jsonl` | rotated weekly | log rotation job | post-mortem |

### Operator-controlled files (the ones humans write)

- `forge_priority.txt` — one rule override target per line, plain text
- `forge_kernel_halt` — empty file presence = halt
- `forge_promotion_candidates.json` — operator clears entries after promotion decision

### `forge_kernel_state.json` schema

```json
{
  "kernel_version": "1.0",
  "last_tick": "2026-04-17T14:15:03-04:00",
  "last_work_cycle": "2026-04-17T14:00:00-04:00",
  "last_drain": "2026-04-17T12:00:00-04:00",
  "last_crossbreed_pass": "2026-04-17T02:00:00-04:00",
  "mode": "normal | conservative | paused | halted",
  "pause_reason": null,
  "active_cycle": null,
  "data_snapshot_id": "ds-2026-04-17T13:00:00",
  "disabled_generators": []
}
```

All timestamps are ISO 8601 with `-04:00` offset (Eastern). UTC stored
elsewhere is converted on read.

### `forge_cycle_log.jsonl` entry

One line per work cycle:

```json
{"cycle_id":"fk-2026-04-17T14:00:00-04:00-c03","fired_at":"2026-04-17T14:00:00-04:00","selector_rule":3,"target_gap":{"type":"regime_gap","key":"commodity+afternoon+mr"},"generator":"mutation","parent":"xb_orb_ema_ladder|MCL","candidates_generated":4,"candidates_passed_first_pass":1,"candidates_advanced_to_validation":0,"compute_minutes":17,"per_component_runtime":{"selector":0.4,"mutation":2.1,"backtest":14.2,"log":0.3},"outcome":"OK","notes":"1 SALVAGE, 3 REJECT"}
```

`per_component_runtime` enables bottleneck spotting without separate
profiling infra.

### `forge_integrity.json` schema (the four anti-drift metrics, codified)

```json
{
  "as_of": "2026-04-17T14:00:00-04:00",
  "harvest_to_closure_ratio_7d": 0.61,
  "median_queue_age_days": 3.2,
  "active_with_action_pct": 0.78,
  "closed_with_memory_pct": 0.95,
  "selector_rule_distribution_30d": {"1":0.02,"2":0.18,"3":0.41,"4":0.15,"5":0.06,"6":0.10,"7":0.08},
  "rule_budget_consumption_this_week": {"1":0.0,"2":0.95,"3":1.0,"4":0.7,"5":0.4,"6":0.5,"7":0.8},
  "fallback_mode_pct_30d": 0.22,
  "low_yield_throttle_active": false,
  "skip_rate_7d": 0.18,
  "promotion_review_latency_days_p50": 1.8,
  "promotion_review_latency_days_p95": 4.5,
  "memory_size_count": 142,
  "disabled_generators": [],
  "flags": []
}
```

### Operator-visible artifacts

The kernel does NOT add a separate file the operator must remember to
check. Instead it integrates with the existing `operator_digest.py`
interface (CLAUDE.md: "operator digest is the primary interface"). A
`digest_hook.py` writes a kernel section that the digest renders if any
of: `flags` non-empty, mode != normal, promotion_candidates non-empty,
yield report has notable change. Otherwise kernel stays silent in digest
output (per existing exception-only philosophy).

### Data freshness / read-snapshot

Forward-day script writes to `data/processed/*.csv` and `*.json` daily
17:00–17:30 ET. Kernel cycles must not read these files mid-write.
Mechanism:

- Kernel pauses 17:00–17:30 ET (covered by §2 pause windows)
- Each cycle pins a `data_snapshot_id` at start (timestamp + file hashes of
  all CSVs read); records it in cycle log. This makes results reproducible
  and detects mid-cycle data changes (cycle marked `STALE_DATA` if hashes
  shift before completion)

### Log rotation

`forge_cycle_log.jsonl` rotates weekly Sunday 00:00 ET to
`archive/forge_cycle_log_<YYYY-WW>.jsonl`. Active log starts fresh.
Archives kept 12 weeks then compressed to `.jsonl.gz`. Integrity metrics
are recomputed from active log only, not archive.

### Git / .gitignore

Kernel state files (`research/data/forge_kernel/*`) are added to
`.gitignore` per IP-protection feedback memory (`feedback_security.md`).
Strategy outputs (registry entries, generated candidate files) follow
existing IP classification — operator decides what gets committed during
review of `forge_promotion_candidates.json`.

---

## 6. How the kernel stays hot without junk or fake motion

This section is the design's load-bearing claim. "Always on" is easy.
"Always on and producing real edge" is the hard part.

### 6.1 Every cycle must justify itself

Selector emits the cycle target with rule + gap key + budget remaining.
If no rule has remaining budget AND a qualifying target, the work cycle
**skips** — it does not invent a target. Cycle log records
`outcome: SKIPPED, reason: <specific>`. Skips are not failures; they
prove the selector is honest. `skip_rate_7d` in integrity JSON.

### 6.2 Yield-to-noise tracked continuously

`harvest_to_closure_ratio_7d` and the daily yield report make
junk-output visible immediately. If 4 consecutive cycles produce zero
advance, conservative mode (§4) engages and surfaces to operator.

### 6.3 Selector rule distribution + budget consumption logged

Two metrics together answer "what is the engine spending time on?":

- `selector_rule_distribution_30d` shows actual fire rate
- `rule_budget_consumption_this_week` shows whether budgets are being honored

Mismatch (e.g., distribution skewed despite balanced budgets) is a flag.

### 6.4 Promotion gate is human-only

Kernel writes `forge_promotion_candidates.json` when a strategy passes
the validation battery. Operator reviews + decides + clears entries.
Nothing in Lane A changes without an operator commit. This is the seam
between Lane B (machine speed) and Lane A (human discipline) — explicit,
not implicit.

`promotion_review_latency_days_p50/p95` tracks operator-side health. If
p95 climbs above 7 days, integrity flag fires — the seam is broken even
if the kernel is healthy. Engine producing, operator not consuming.

### 6.5 Memory closure is mandatory before queue exit

Any rejected/archived candidate must have a memory payload written
(existing `docs/fql_forge/memory_index.md` schema) before it leaves the
queue. Failed ideas become future search inputs (selector rule 6) — they
don't just disappear. The `closed_with_memory_pct` integrity metric
enforces this.

`memory_size_count` is tracked so unbounded growth is visible (rule-6
input quality degrades if memory becomes noise — see v2 question §10).

### 6.6 Fake-motion detection

Five signals catch a busy-but-useless kernel:

- **High cycle count, zero candidates_advanced** for >48h → flag
- **Selector rule 7 dominance >50% over 7d** → flag (recombining itself)
- **Same gap_key targeted >3 cycles in 24h with zero advance** → graduated cooldown (§4)
- **High skip_rate_7d (>40%)** → flag (selector starving — likely budget misconfigured or gap pool exhausted)
- **Same generator FAILS 3+ times in 24h** → auto-disable + flag (§4)

Flags route through operator digest. Kernel does not "decide" to fix
itself beyond conservative-mode and graduated cooldowns — it surfaces
the problem.

---

## 7. Implementation gating (post-checkpoint)

Build is **not** authorized during the hold. Sequence after May 1
checkpoint clears (and after Treasury-Rolldown verification carveout
ends 2026-05-02):

**Phase A (week 1 post-hold) — read-only:**
1. Build `forge_kernel/integrity.py` — codify the 4 anti-drift metrics
   over existing data; runs hourly; no other behavior change.
2. Build `forge_kernel/cycle_log.py` — append-only journal. Backfilled
   from existing `mass_screen_results.json` and `evolution_results.json`
   so schema gets exercised on real data immediately.
3. Build `forge_kernel/digest_hook.py` (read-only at this stage).
4. Add startup self-check (data dirs exist, registry parseable, dependencies importable).

**Phase B (week 2–3) — selector + queue, no execution:**
5. Build `selector.py` + `queue.py`. Run in dry-run mode for 14 days
   (extended from 5d in original draft — 14d covers 2 weekly review
   cycles, enough to evaluate selector quality across a full cadence
   loop). Selector picks targets and logs them; no generator actually
   fires.

**Phase C (week 4) — execution wired, throttled to 25%:**
6. Wire selector → existing generators (mutation/crossbreed). Cadence
   throttled to: 1 work cycle per 8h (vs designed 2h), 1 drain per 16h
   (vs designed 4h), no daily crossbreed pass yet. Watch integrity
   metrics for 7 full days. No promotions still allowed.

**Phase D (week 5+) — scale to designed cadence:**
7. Move to designed Layer 0 cadence. Add launchd plist. Promotion gate
   stays human until 30+ days of stable integrity metrics.

### Phase stop conditions

Each phase halts (does not advance) if any of:

- New integrity flag appears that wasn't in design's expected-flag list
- Skip rate >60% for 48h (selector misconfigured)
- Daily compute budget ceiling hit
- Operator-set halt file present at phase boundary

Halt → revise design → resume from same phase, not earlier.

### Crash / restart recovery

On startup:
- Read `forge_kernel_state.json.active_cycle`
- If non-null: mark that cycle `outcome: INTERRUPTED` in cycle log; do NOT retry automatically
- Re-validate state files (schema check); if any fail, write halt and exit
- Resume normal scheduling on next tick boundary

Cycle IDs are timestamp-based (`fk-<ISO8601>-c<n>`) so re-running an
interrupted cycle would generate a different ID — no idempotency
collision.

---

## 8. v1.1 evidence-driven refinements (deferred, will revisit after data)

These are good ideas without enough evidence to commit to specific
parameters in v1. Implement v1 with placeholder values; refine after 30+
days of cycle data:

1. **Conservative-mode hysteresis** — clear threshold may want to be
   "yield ≥ 0.10 over 10 cycles" rather than current 3. Three is too
   easy to hit on flukey cycles. Watch how often mode thrashes; tighten
   from observed data.

2. **Daily registry-add cap of 20** — may want to tighten to 10 to
   enforce stricter selectivity. Watch what 20 produces; if >50% are
   memory-payload-only (not advancing), tighten.

3. **Pause during forward-trading window (17:00–17:30 ET)** — defaults
   to pause. If observed compute contention is zero (kernel is mostly
   I/O-bound and forward-day is mostly network-bound), can run through.
   Decide from observed CPU/disk metrics.

4. **Memory pruning policy** — once `memory_size_count` shows growth
   trajectory, design pruning rule (age + revival_attempts + last_relevant_signal).

---

## 9. v2 open questions (deferred — needs v1 data)

- **Learned selector** (RL on cycle outcomes → routing) — needs cycle data first
- **Auto-source-lane ranking** (which sources earned the most validated strategies) — needs longitudinal yield data first
- **Auto-stale-detection** beyond the 9 codified rules
- **Multi-machine compute distribution** — only if v1 single-machine becomes a binding constraint
- **Auto-promotion through gate** — likely never in scope; gate is the seam by design
- **Memory pruning rule** — see v1.1 #4
- **Refinement-playbook auto-generation** from memory payloads (in original v1 deferral list)

---

## 10. Standing questions for v1 design (operator-answered)

1. **Daily registry-add cap: 20 or tighter at 10?** — DEFAULT 20 in v1, refine in v1.1 from data (see §8 #2)
2. **Pause during forward-trading window?** — DEFAULT pause in v1, refine in v1.1 from data (see §8 #3)
3. **`forge_priority.txt` operator override in v1?** — **YES, included in v1.** Cheap to implement, trivially auditable (cycle log records `selector_rule: 1`), and gives an emergency steer if the selector goes sideways.

---

## Appendix A — Compatibility with existing principles

- **Continuous discovery, selective deployment** (standing) — kernel embodies the discovery half; deployment seam (§6.4) embodies selective half
- **Elite standard** (standing) — selectivity priority + dedup + memory-closure are the elite filter applied at machine speed
- **Lane A/B operating doctrine** — kernel is Lane B implementation; hard prohibitions (§4) enforce the seam
- **Doc discipline** (`feedback_doc_discipline.md`) — kernel writing memory payloads IS doc updating; mandatory closure (§6.5) honors the principle
- **IP protection** (`feedback_security.md`) — kernel state files .gitignored (§5)

The kernel design extends these standing principles. It does not replace
or weaken any of them.
