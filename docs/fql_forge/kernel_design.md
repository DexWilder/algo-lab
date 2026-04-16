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

Most components exist as code already; the kernel adds a thin orchestrator
+ state files + selectivity wiring. Components in **bold** need no new
implementation logic; only scheduling and state plumbing.

| # | Component | Existing code | New work |
|---|-----------|---------------|----------|
| 1 | **Intake / harvest loop** | `research/harvest_engine.py --scan/--run` | Kernel-driven invocation; rate-limit |
| 2 | **Gap detector** | `research/data/strategy_genome_map.json` | Read-only consumer; staleness check |
| 3 | Candidate generator | — (logic in evolution + crossbreeding) | New thin layer: pick gap → route → enqueue |
| 4 | **Crossbreeder** | `research/crossbreeding/crossbreeding_engine.py` | Gap-targeted invocation |
| 5 | **Mutation engine** | `research/evolution/mutations.py` + `evolution_scheduler.py` | Gap-targeted invocation |
| 6 | **Batch backtest runner** | `research/batch_first_pass.py` + `research/mass_screen.py` | Continuous-throttled invocation; deterministic seeds |
| 7 | **Validation battery scheduler** | `research/validation/run_validation_battery.py` | New: queue drainer for FIRST_PASS_PASSED items |
| 8 | Result logger / registry writer | `research/data/strategy_registry.json`, `research/data/first_pass/` | Reuse existing writers; add cycle log |
| 9 | Stale queue sweeper | `docs/fql_forge/stale_checks.md` (currently manual) | Promote rules 2/4/5/8/9 to code; emit findings only |
| 10 | Integrity monitor | `docs/fql_forge/anti_drift_checks.md` (currently manual) | Promote 4 metrics to code; emit health JSON |
| 11 | Genome map regenerator | existing genome analysis script | New schedule: daily 03:30 ET refresh |

**Net new code surface (design only — to be validated at impl):**

- `research/forge_kernel/orchestrator.py` — top-level scheduler/dispatcher; single-writer for kernel state
- `research/forge_kernel/selector.py` — gap → generator routing (rule-budget aware)
- `research/forge_kernel/cycle_log.py` — append-only cycle journal
- `research/forge_kernel/queue.py` — typed queue with WIP caps + dedup
- `research/forge_kernel/integrity.py` — yield/noise + anti-drift metrics
- `research/forge_kernel/stale.py` — codified stale rules
- `research/forge_kernel/digest_hook.py` — emits kernel section into operator digest
- `research/forge_kernel/alerts.py` — wraps existing `scripts/fql_alerts.py` for critical-path bypass
- 1 new launchd plist for the kernel tick
- Kernel state files (see §5)

Existing engines are imported and called as libraries. Nothing in
`engine/`, `strategies/`, or the existing `research/data/strategy_*.json`
schema changes.

### Nomenclature

- **Cycle** — one fired iteration of a Layer 0c work cycle. Has a unique `cycle_id`.
- **Candidate** — a strategy variant produced by a generator inside a cycle. Lives in pre-validation queue until first-pass result.
- **Strategy** — a candidate that passed first-pass and got a registry entry.
- **Promotion candidate** — a strategy that passed validation battery; awaits operator review for probation.

---

## 2. Cadence — Layer 0 under existing layers

Existing cadence (human-paced, in `docs/fql_forge/cadence.md`): Layers
1–4. Layer 0 is the new machine layer; Layers 1–4 are unchanged. Layer 0
produces inputs and metrics that Layer 1 reads each morning.

### Layer 0 cadence

| Sub-layer | Period | Job | Bounded by |
|-----------|--------|-----|------------|
| 0a — tick | 15 min | Claw inbox scan + dedup intake | <30s wallclock |
| 0b — short cycle | hourly | Stale sweeper + integrity heartbeat | <60s wallclock |
| 0c — work cycle | every 2h | Selector picks 1 gap → generator → backtest queue | hard cap: ≤5 candidates enqueued per cycle |
| 0d — drain | every 4h | Backtest runner drains queue; validation runner drains FIRST_PASS_PASSED | compute budget ≤30 min wallclock |
| 0e — daily | 02:00 ET | Crossbreeding pass on validated parents (one family per day, rotating) | hard cap: ≤10 hybrids per pass |
| 0f — daily | 03:00 ET | Yield report → writes `forge_yield_daily.json` | <2 min |
| 0g — daily | 03:30 ET | Regenerate `strategy_genome_map.json` | <5 min |

**Why these intervals:** 15-min tick keeps Claw flow current; 2h work
cycle gives backtest cohorts time to finish before next batch; 4h drain
matches typical backtest runtime; daily crossbreed rotated by family;
daily genome regen prevents selector input drift as registry grows.
Nothing runs every minute — "always on" ≠ "always firing."

### Pause windows (general rule + scheduled windows)

**General rule:** Kernel auto-pauses any time `research/data/watchdog_state.json`
shows SAFE_MODE active. Generated candidates against broken data feeds
or unhealthy infrastructure are worse than no candidates. Watchdog already
detects gateway/data/job-health issues every 5 min — kernel piggybacks.

**Scheduled windows (mandatory pause regardless of SAFE_MODE state):**

- **17:00–17:30 ET weekdays** — forward-trading agent runs (Lane A)
- **17:30–18:00 ET weekdays** — daily research agent runs
- **18:00–19:00 ET Tue/Thu** — twice-weekly research + mass_screen
- **18:30–19:30 ET Fri** — weekly research rollup
- **2026-04-30 00:00 ET → 2026-05-02 00:00 ET** — Treasury-Rolldown May 1 verification carveout (special case of the general SAFE-MODE-respect rule, codified explicitly because the trigger is calendar-based not health-based)

Pause is mode change, not shutdown. Kernel writes
`forge_kernel_state.json.mode = "paused"`, `pause_reason = "<window>"`,
resumes on next tick after window ends.

### Interaction with existing scheduled agents

| Existing agent | Schedule | Status under kernel |
|----------------|----------|---------------------|
| `com.fql.claw-control-loop` | 30 min | Unchanged. Kernel intake additive. |
| `com.fql.daily-research` | weekday 17:30 | Unchanged. Kernel daily yield report at 03:00 supplementary. |
| `com.fql.twice-weekly-research` (mass_screen) | Tue/Thu 18:00 | **Demoted to safety net.** Kernel work cycles handle the same job continuously. |
| `com.fql.weekly-research` | Fri 18:30 | Unchanged. Reads kernel cycle log + integrity JSON for rollup. |
| `com.fql.forward-trading` | weekday 17:00 | Unchanged. Lane A. |
| `com.fql.watchdog` | 5 min | Add kernel heartbeat to its checks; kernel reads watchdog SAFE_MODE. |

### Reconciliation with the 5-state queue (`docs/fql_forge/queues.md`)

The 5-state model (Inbox / In Progress / Validation / Validated / Rejected)
is the **operator-facing** view. Kernel queues (pre-validation backtest,
validation battery) are **sub-states inside "In Progress"**. Kernel
updates the operator-facing position when state changes.

---

## 3. Selectivity policy

Always-on without selectivity = junk factory. The selector is the gate.

### Selector input (read every work cycle, 0c)

- `research/data/strategy_genome_map.json` — current gap list (selector also checks `as_of` timestamp; if >36h old, emits `STALE_GENOME_MAP` integrity flag, continues with caveat)
- `research/data/strategy_registry.json` — current strategy inventory + status
- `docs/PORTFOLIO_TRUTH_TABLE.md` (parsed sections) — open portfolio gaps
- `research/data/forge_kernel/strategy_memory.json` — failed-but-salvageable list
- `research/data/forge_kernel/recent_yield.json` — last N cycle outcomes
- `research/data/forge_kernel/rule_budget.json` — running consumption per rule
- `research/data/forge_kernel/forge_priority.txt` — operator override (optional)

### Selectivity priority — weekly budget per rule (NOT first-match)

Earlier draft used first-match-wins. That had a structural flaw: rules 2–3
(portfolio + regime gaps) almost always have qualifying targets, so rules
5/6/7 would never fire. Rule 7 in particular (validated-parent recombination)
is the empirical workhorse path that built the XB-ORB family — putting it
last under first-match would prevent the engine from doing what has
historically worked best.

Replace with weekly budget per rule:

| Rule | Weekly budget | Targets |
|------|---------------|---------|
| 1 | as needed | Operator override (`forge_priority.txt`) |
| 2 | 25% | Critical portfolio gap (PORTFOLIO_TRUTH_TABLE) |
| 3 | 25% | Regime gap (genome map cell underperforms) |
| 4 | 15% | Asset gap with owned local data |
| 5 | 10% | Time-of-day / session gap |
| 6 | 10% | Salvageable failed idea (strategy memory) |
| 7 | 15% | Validated parent recombination |

Selector picks the rule whose budget is most under-consumed (relative to
weekly target), then picks the best target within that rule. Budget
resets weekly Sunday 00:00 ET. Unused budget → integrity flag
`UNUSED_BUDGET:rule_<n>` → operator review.

### Selector output (one per work cycle)

```json
{
  "cycle_id": "fk-2026-04-17T14:00:00-04:00-c03",
  "fired_at": "2026-04-17T14:00:00-04:00",
  "selector_rule": 3,
  "rule_budget_remaining": 0.41,
  "target_gap": {
    "type": "regime_gap",
    "key": "commodity+afternoon+mean_reversion",
    "rationale": "Genome cell empty; truth table flags energy gap",
    "cooldown_state": "active"
  },
  "generator": "mutation",
  "parent_or_seed": "xb_orb_ema_ladder|MCL|baseline",
  "budget": {"max_candidates": 5, "max_compute_minutes": 25},
  "skip_if": ["queue_pre_validation > 30", "recent_yield_streak < 0.05", "gap_key_in_cooldown"],
  "data_snapshot_id": "ds-2026-04-17T13:00:00",
  "random_seed": 174302540300003
}
```

### Why weekly budget, not first-match or RL

- **vs first-match:** weekly budget guarantees every rule path gets exercised; surfaces source exhaustion as a flag rather than silent starvation
- **vs RL:** v1 keeps the selector explicit and inspectable. Every cycle log entry names rule + budget remaining. Drift is trivially diagnosable. Learned routing is v2+

---

## 4. Guardrails / anti-sprawl controls

Selector chooses *what*; guardrails bound *how much* and *how aggressively*.

### Queue caps

| Queue / counter | Cap | Behavior on cap |
|-----------------|-----|-----------------|
| Pre-validation backtest queue | 30 items | Reject new enqueue; selector skips work cycle until drained < 20 |
| Validation battery queue | 15 items | Reject new enqueue; selector skips until drained < 10 |
| Crossbreed candidates per family per week | 25 | Family rotation skips that family for the week |
| Mutation candidates per parent per day | 8 | Selector picks different parent next cycle |
| Total registry adds per day | 20 | Hard ceiling; surfaces ALERT if hit 3 days in a row |
| **Daily compute budget (all cycles combined)** | **180 min wallclock** | **Kernel enters paused mode until 00:00 ET reset; CRITICAL ALERT** |
| Per-cycle compute budget | 30 min wallclock | Runner kills jobs that exceed; logs `BUDGET_EXCEEDED` |

### Concurrent-cycle protection (single-writer state)

- Orchestrator is sole writer of `forge_kernel_state.json`. All other
  components read it; none write.
- Before firing a 0c work cycle: orchestrator checks `active_cycle` field.
  If non-null (previous cycle still running), skip the new fire and log
  `outcome: SKIPPED, reason: CYCLE_IN_FLIGHT`.
- File lock (`.forge_kernel.lock`) on orchestrator startup prevents two
  orchestrator instances from running simultaneously. Second instance
  exits cleanly with log line.
- Cycle IDs are timestamp-based (`fk-<ISO8601>-c<n>`), so even an
  interrupted-then-rerun cycle gets a fresh ID — no accidental reuse.

### Dedup before enqueue (with backtest determinism)

Every candidate hashes:

- **Genome 9-tuple** → if a registered strategy already occupies the cell, require novelty score > 0.30 (parameter-space distance to nearest existing entry)
- **Parameter signature** → reject exact param matches against registry
- **Strategy logic hash** → AST-normalized (whitespace + var renames stripped) hash; reject byte-equivalent regenerations

**Backtest determinism:** Every backtest invocation receives an explicit
random seed derived from `cycle_id` + candidate index. Identical
candidates produce identical results, dedup hashes work, repeated runs
are reproducible. Cheap to enforce upfront; painful to retrofit. Seed is
recorded in cycle log for any future re-run.

### Hard prohibitions (kernel cannot do these — period)

- Touch any file under `state/` (account state, data update state)
- Modify any `*_state.json` outside `research/data/forge_kernel/`
- Modify `engine/strategy_universe.py` probation list
- Modify `research/data/portfolio_activation_matrix.json`
- Modify the `status` field of any existing entry in `research/data/strategy_registry.json` (only append new entries)
- Edit any file in `strategies/` (only generates new files in `research/evolution/generated_candidates/`)
- Promote a strategy to probation (operator-only — see §6.4)
- Run `git commit` or `git push` (operator commits kernel state if desired)
- Run during any pause window (§2)
- Run while watchdog SAFE_MODE is active (§2 general rule)

### Soft throttles (yield-driven)

If `recent_yield_streak < 0.05` (last 20 cycles produced <5% advance
rate), selector enters **conservative mode**: skip rule 7 entirely,
raise novelty score 0.30 → 0.50, halve enqueue caps, emit
`LOW_YIELD_THROTTLE`. Auto-clears after yield ≥ 0.10 over 3 consecutive
cycles (v1 default — flagged as v1.1 refinement candidate, see §8).

Conservative mode is suppressed during bootstrap (§6.7).

### Graduated gap-key cooldown

Same `gap_key` targeted with zero advance:

- 3 cycles in 24h → 1-day cooldown
- 5 cycles in 72h → 3-day cooldown
- 8 cycles in 7d → 7-day cooldown

Cooldown means selector skips that key when picking targets within its
rule. Operator can manually clear via `forge_priority.txt`.

### Stop-the-world halt

Operator creates empty `research/data/forge_kernel/forge_kernel_halt`
file. Kernel checks every tick; if present, completes in-flight cycle if
safe, writes `mode = "halted"`, sleeps until file removed. Emergency
switch — cleaner than disabling launchd. HALT also fires CRITICAL ALERT
via `fql_alerts.py`.

### Generator exception isolation

Each generator invocation runs inside a try/except boundary:

1. Exception caught by orchestrator; never propagates
2. Cycle marked `outcome: GENERATOR_FAILED` (not `OK`); exception type + first traceback line logged
3. Kernel continues to next sub-layer
4. Same generator FAILS 3+ times in 24h → auto-disabled, added to
   `forge_kernel_state.json.disabled_generators[]`, CRITICAL ALERT fires.
   Selector skips disabled generators until operator manually re-enables.

---

## 5. Artifact / state outputs

All kernel state lives under `research/data/forge_kernel/`. Existing
state files are unchanged.

### State files

| File | Type | Updated by | Read by |
|------|------|-----------|---------|
| `forge_kernel_state.json` | snapshot | orchestrator only | watchdog, operator digest |
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
| `.forge_kernel.lock` | file lock | orchestrator | concurrent-instance check |

### Operator-controlled files

- `forge_priority.txt` — one rule override target per line, plain text
- `forge_kernel_halt` — empty file presence = halt
- `forge_promotion_candidates.json` — operator clears entries after promotion decision

### `forge_promotion_candidates.json` schema (operator-actionable in one file)

Each entry contains everything operator needs for a promotion decision —
no hunting through 5 files:

```json
{
  "promotion_id": "pc-2026-04-17-01",
  "candidate_strategy_id": "xb_orb_ema_ladder_zb_v3",
  "submitted_at": "2026-04-17T14:30:00-04:00",
  "parent_provenance": ["xb_orb_ema_ladder_mnq", "xb_orb_ema_ladder_mcl"],
  "family_tag": "XB-ORB-EMA-Ladder",
  "originating_cycle": "fk-2026-04-17T12:00:00-04:00-c01",
  "selector_rule_fired": 7,
  "validation_battery_report": {
    "walk_forward": {...},
    "regime_stability": {...},
    "asset_robustness": {...},
    "timeframe_robustness": {...},
    "monte_carlo": {...},
    "parameter_stability": {...}
  },
  "first_pass_classification": "ADVANCE",
  "trade_count": 743,
  "pf": 1.41,
  "suggested_probation_tier": "workhorse",
  "applicable_governance_doc": "docs/XB_ORB_PROBATION_FRAMEWORK.md",
  "promotion_checklist_path": "docs/XB_ORB_PROBATION_FRAMEWORK.md#core-promotion-engineering-checklist",
  "data_snapshot_id": "ds-2026-04-17T11:00:00",
  "random_seed": 174302540300003
}
```

Promotion tier suggestion follows existing factory dual-archetype rule
(workhorse if trades ≥ 500; tail-engine otherwise). Suggestion only —
operator decides.

### `forge_kernel_state.json` schema

```json
{
  "kernel_version": "1.0",
  "last_tick": "2026-04-17T14:15:03-04:00",
  "last_work_cycle": "2026-04-17T14:00:00-04:00",
  "last_drain": "2026-04-17T12:00:00-04:00",
  "last_crossbreed_pass": "2026-04-17T02:00:00-04:00",
  "last_genome_regen": "2026-04-17T03:30:00-04:00",
  "mode": "normal | conservative | bootstrap | paused | halted",
  "pause_reason": null,
  "active_cycle": null,
  "data_snapshot_id": "ds-2026-04-17T13:00:00",
  "disabled_generators": [],
  "bootstrap_until": "2026-04-24T00:00:00-04:00"
}
```

All timestamps ISO 8601 with `-04:00` offset. UTC stored elsewhere is
converted on read.

### `forge_cycle_log.jsonl` entry

```json
{"cycle_id":"fk-2026-04-17T14:00:00-04:00-c03","fired_at":"2026-04-17T14:00:00-04:00","selector_rule":3,"target_gap":{"type":"regime_gap","key":"commodity+afternoon+mr"},"generator":"mutation","parent":"xb_orb_ema_ladder|MCL","candidates_generated":4,"candidates_passed_first_pass":1,"candidates_advanced_to_validation":0,"compute_minutes":17,"per_component_runtime":{"selector":0.4,"mutation":2.1,"backtest":14.2,"log":0.3},"data_snapshot_id":"ds-2026-04-17T13:00:00","random_seed":174302540300003,"outcome":"OK","notes":"1 SALVAGE, 3 REJECT"}
```

### `forge_integrity.json` schema

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
  "genome_map_age_hours": 8.3,
  "disabled_generators": [],
  "bootstrap_active": false,
  "flags": []
}
```

### Operator surfaces — primary + critical-alert bypass

**Primary surface (digest):** Kernel does NOT add a separate file the
operator must remember to check. `digest_hook.py` writes a kernel
section into existing `operator_digest.py` output. Section renders only
when: `flags` non-empty, mode != normal, promotion_candidates non-empty,
or notable yield change. Otherwise silent (per existing exception-only
philosophy).

**Critical-alert bypass:** Some events can't wait for tomorrow's digest.
These route immediately through existing `scripts/fql_alerts.py`
(macOS notification + log):

- HALT file detected → CRITICAL
- Daily compute budget ceiling hit → CRITICAL
- Watchdog SAFE_MODE detected (kernel auto-pause) → CRITICAL
- Generator stack-trace (3+ failures in 24h, auto-disabled) → CRITICAL
- Single generator stack-trace (first occurrence) → INFO

Bypass is additive — same events also surface in next digest.

### Data freshness / read-snapshot

Forward-day script writes to `data/processed/*.csv` and `*.json` daily
17:00–17:30 ET. Kernel cycles must not read these mid-write. Mechanism:

- Pause window 17:00–17:30 ET (§2)
- Each cycle pins a `data_snapshot_id` at start (timestamp + file hashes
  of all CSVs read); records it in cycle log + promotion candidate. Makes
  results reproducible and detects mid-cycle data changes (cycle marked
  `STALE_DATA` if hashes shift before completion)

### Log rotation

`forge_cycle_log.jsonl` rotates weekly Sunday 00:00 ET to
`archive/forge_cycle_log_<YYYY-WW>.jsonl`. Active log starts fresh.
Archives kept 12 weeks then compressed. Integrity metrics computed from
active log only.

### Git / .gitignore

Per IP-protection feedback memory (`feedback_security.md`):

- `.gitignore` adds `research/data/forge_kernel/*`
- **Exceptions tracked in git for audit trail:** `forge_promotion_candidates.json` (each promotion decision needs reproducible record), `forge_kernel_halt` if present (operator action history)
- This design doc and v1.1/v2 evolutions tracked normally
- Strategy outputs (registry entries, generated candidate files) follow
  existing IP classification — operator decides commits during promotion review

---

## 6. How the kernel stays hot without junk or fake motion

Load-bearing claim of the design. "Always on" is easy. "Always on and
producing real edge" is hard.

### 6.1 Every cycle must justify itself

Selector emits cycle target with rule + gap key + budget remaining. If
no rule has remaining budget AND a qualifying target, the work cycle
**skips** — does not invent a target. Cycle log records
`outcome: SKIPPED, reason: <specific>`. `skip_rate_7d` in integrity JSON.

### 6.2 Yield-to-noise tracked continuously

`harvest_to_closure_ratio_7d` and the daily yield report make
junk-output visible. 4 consecutive cycles producing zero advance →
conservative mode (§4) → operator surfacing.

### 6.3 Selector rule distribution + budget consumption logged

Two metrics together answer "what is the engine spending time on?":

- `selector_rule_distribution_30d` — actual fire rate
- `rule_budget_consumption_this_week` — whether budgets are being honored

Mismatch is a flag.

### 6.4 Promotion gate is human-only

Kernel writes `forge_promotion_candidates.json` when a strategy passes
the validation battery. Operator reviews + decides + clears entries.
Nothing in Lane A changes without an operator commit. The seam between
Lane B (machine speed) and Lane A (human discipline) — explicit, not
implicit.

`promotion_review_latency_days_p50/p95` tracks operator-side health. If
p95 climbs above 7 days, integrity flag fires — engine producing,
operator not consuming.

### 6.5 Memory closure is mandatory before queue exit

Any rejected/archived candidate must have a memory payload written
(`docs/fql_forge/memory_index.md` schema) before it leaves the queue.
Failed ideas become future search inputs (rule 6) — they don't disappear.
`closed_with_memory_pct` enforces this.

`memory_size_count` is tracked so unbounded growth is visible
(rule-6 input degrades if memory becomes noise — see §9).

### 6.6 Fake-motion detection

Five signals catch a busy-but-useless kernel:

- High cycle count, zero candidates_advanced for >48h → flag
- Selector rule 7 dominance >50% over 7d → flag (recombining itself)
- Same gap_key targeted >3 cycles in 24h with zero advance → graduated cooldown (§4)
- High `skip_rate_7d` (>40%) → flag (selector starving)
- Same generator FAILS 3+ times in 24h → auto-disable + CRITICAL alert (§4)

Flags route through operator digest. Kernel does not "decide" to fix
itself beyond conservative-mode + cooldowns + auto-disable — it surfaces
the problem.

### 6.7 Bootstrap mode (first 7 days)

Integrity metrics like `harvest_to_closure_ratio_7d` and
`selector_rule_distribution_30d` have no meaningful data on day 1.
Without bootstrap protection, kernel would flag itself broken on launch.

For the first 7 days after kernel start (or restart with cleared state):

- `mode = "bootstrap"` in state JSON
- `bootstrap_active = true` in integrity JSON
- All integrity flags are advisory (logged, not surfaced via digest or alerts)
- Conservative mode is suppressed (yield streak data is too noisy)
- Hard prohibitions, queue caps, daily compute ceiling, halt file, and
  generator exception isolation REMAIN ACTIVE (these don't depend on
  trend data)

Bootstrap clears automatically at `bootstrap_until` timestamp. Operator
can clear early via `forge_priority.txt` directive `BOOTSTRAP_CLEAR`.

---

## 7. Implementation gating (post-checkpoint)

Build is **not** authorized during the hold. Sequence after May 1
checkpoint clears + Treasury-Rolldown verification carveout ends 2026-05-02.

**Phase A (week 1 post-hold) — read-only:**
1. Build `forge_kernel/integrity.py` over existing data; runs hourly
2. Build `forge_kernel/cycle_log.py` — backfilled from existing
   `mass_screen_results.json` and `evolution_results.json` so schema
   gets exercised on real data immediately
3. Build `forge_kernel/digest_hook.py` (read-only at this stage)
4. Build genome map regen schedule (component #11) — independently useful
   even if rest of kernel never ships
5. Add startup self-check (data dirs exist, registry parseable, dependencies importable, watchdog reachable)

**Phase B (week 2–3) — selector + queue, no execution:**
6. Build `selector.py` + `queue.py`. Run dry-run for 14 days. Selector
   picks targets and logs them; no generator actually fires. Operator
   reviews target stream for selectivity quality.

**Phase C (week 4) — execution wired, throttled to 25%:**
7. Wire selector → existing generators. Cadence throttled: 1 work cycle
   per 8h (vs designed 2h), 1 drain per 16h (vs designed 4h), no daily
   crossbreed pass yet. Bootstrap mode active throughout. Watch
   integrity metrics for 7 full days. No promotions allowed.

**Phase D (week 5+) — scale to designed cadence:**
8. Move to designed Layer 0 cadence. Add launchd plist. Bootstrap mode
   continues for 7 days from D start. Promotion gate stays human until
   30+ days of stable integrity metrics (post-bootstrap).

### Phase stop conditions

Each phase halts (does not advance) if any of:

- New integrity flag appears that wasn't in design's expected-flag list
- Skip rate >60% for 48h (selector misconfigured)
- Daily compute budget ceiling hit
- Operator-set halt file present at phase boundary
- Generator auto-disabled in current phase

Halt → revise design → resume from same phase, not earlier.

### Crash / restart recovery

On startup:
- Check `.forge_kernel.lock` — if held by live process, exit cleanly
- Read `forge_kernel_state.json.active_cycle` — if non-null: mark that
  cycle `outcome: INTERRUPTED` in cycle log; do NOT retry automatically
- Re-validate state files (schema check); if any fail, write halt and exit
- If bootstrap was active and `bootstrap_until` not reached, resume bootstrap
- Resume normal scheduling on next tick boundary

Cycle IDs are timestamp-based so re-running an interrupted cycle would
generate a different ID — no idempotency collision.

---

## 8. v1.1 evidence-driven refinements (deferred, will revisit after data)

Implement v1 with placeholder values; refine after 30+ days of data:

1. **Conservative-mode hysteresis** — clear threshold may want to be
   "yield ≥ 0.10 over 10 cycles" rather than 3. Watch how often mode
   thrashes.
2. **Daily registry-add cap of 20** — may want 10 to enforce stricter
   selectivity. Watch what 20 produces.
3. **Pause during forward-trading window (17:00–17:30 ET)** — defaults
   to pause; revisit if observed compute contention is zero.
4. **Memory pruning policy** — once `memory_size_count` shows growth
   trajectory, design pruning rule (age + revival_attempts + last_relevant_signal).
5. **Bootstrap duration of 7 days** — may need 14 if cycle volume is low.

---

## 9. v2 open questions (deferred — needs v1 data)

- **Learned selector** (RL on cycle outcomes → routing)
- **Auto-source-lane ranking** (which sources earned the most validated strategies)
- **Auto-stale-detection** beyond the 9 codified rules
- **Multi-machine compute distribution** — only if v1 single-machine becomes binding
- **Auto-promotion through gate** — likely never in scope; gate is the seam by design
- **Memory pruning rule** (see §8 #4)
- **Refinement-playbook auto-generation** from memory payloads (original v1 deferral)

---

## 10. Standing questions for v1 design (operator-answered)

1. **Daily registry-add cap: 20 or 10?** — DEFAULT 20 in v1, refine in v1.1 (§8 #2)
2. **Pause during forward-trading window?** — DEFAULT pause, refine in v1.1 (§8 #3)
3. **`forge_priority.txt` operator override in v1?** — **YES, included.** Cheap, auditable, gives emergency steer.

---

## Appendix A — Compatibility with existing principles

- **Continuous discovery, selective deployment** — kernel embodies the discovery half; deployment seam (§6.4) embodies selective half
- **Elite standard** — selectivity priority + dedup + memory-closure are the elite filter at machine speed
- **Lane A/B operating doctrine** — kernel is Lane B implementation; hard prohibitions (§4) enforce the seam
- **Doc discipline** — kernel writing memory payloads IS doc updating
- **IP protection** — kernel state .gitignored except audit-trail files (§5)

The kernel design extends these standing principles. It does not replace
or weaken any of them.
