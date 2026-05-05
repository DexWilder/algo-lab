# FQL Forge Automation Design

**Filed:** 2026-05-05
**Status:** Design + initial dry-run orchestrator. Scheduling DISABLED by default; operator must explicitly load launchd to activate cadence.

**Core principle (locked):** **Autonomous evidence generation. Human-gated system mutation.**

The Forge runs continuously to produce candidate evidence; no Forge component is authorized to mutate protected state. Promotion, registry append, portfolio composition, runtime, scheduler, checkpoint, hold-state — all stay operator-gated regardless of what the Forge surfaces.

---

## Safety boundaries (the contract)

### Allowed autonomously (no operator intervention required)

| Action | Surface |
|---|---|
| Run `research/fql_forge_batch_runner.py` in `--dry-run` / report-only mode | Lane B / Forge |
| Select candidate batches from registered pool | Lane B |
| Run cheap screens via existing harnesses (crossbreeding engine swaps, A/B comparisons on existing strategy code) | Lane B |
| Classify PASS / WATCH / KILL / RETEST per existing verdict standard | Lane B |
| Write markdown / CSV / JSON reports to `research/data/fql_forge/reports/` | Lane B (new sub-tree, no overlap with Lane A surfaces) |
| Update Forge-only queue / report files | Lane B |
| Surface next recommended batch in queue file | Lane B |
| Flag harness bugs or missing data (e.g., engine `donchian_breakout` 0-trades) | Lane B (diagnostic) |

### NOT allowed autonomously (operator must explicitly approve before any of these)

| Action | Why |
|---|---|
| Registry append (`research/data/strategy_registry.json` mutation) | T2 surface — registry status changes need operator gate |
| Live strategy promotion (any status transition past `idea`) | T3 |
| Portfolio composition changes | T3 |
| Runtime / scheduler / checkpoint / hold-state changes | T3 / Lane A |
| Deployment changes (launchd loads/unloads beyond the disabled-by-default plist) | T3 |
| Broad parameter optimization loops | violates §3.3 bounded recombination + risks overfitting |
| Live trading logic changes | T3 |
| Modifying `engine/` / `strategies/` source code without operator review | risks silent runtime drift |

### Tripwires — automation pauses itself

The daily loop self-halts and surfaces an alert (does NOT continue) under any of:

1. Three consecutive runs produce zero PASS candidates (suggests harness or candidate-pool degradation)
2. A candidate produces a system-blowup-level loss (PnL < -10% of starting capital in cheap screen)
3. The reports directory grows past 30 days of files without operator review (prevents accumulation noise)
4. Any candidate's `_xb_swap()` function raises an exception (engine/data error needs human attention)
5. Total batch runtime exceeds 5 minutes (likely a hung subprocess or expanding scope)

When a tripwire fires, the loop writes a `_TRIPWIRE_<reason>.md` file to the reports directory and exits non-zero. launchd sees the failure; future runs do not auto-resume until operator clears the tripwire.

---

## Cadence (proposed; NOT enabled yet)

| Phase | Frequency | What runs | Operator review cycle |
|---|---|---|---|
| **Phase A — manual CLI only (NOW)** | On operator command | Operator runs `python3 research/fql_forge_daily_loop.py --dry-run --top N` | Per-invocation |
| **Phase B — scheduled report-only (next)** | Once per weekday at 19:00 ET (after operator digest) | Daily loop fires; writes report; surfaces next-batch recommendation | Friday weekly review |
| **Phase C — auto-drafted registry patches (later)** | Same cadence | Daily loop produces `_DRAFT_register_*.md` for any candidates that pass with strict criteria | Operator approves draft → manual append |
| **Phase D — controlled promotion proposals (much later)** | Same cadence | Loop proposes status transitions for review | Operator approves; still manual T3 |

**Activation gate for Phase B:** operator must explicitly `launchctl load` the disabled plist (provided in `scripts/com.fql.forge-daily-loop.plist.disabled`). Default state: NOT loaded.

---

## Outputs

### Per-run artifacts (written by the daily loop)

```
research/data/fql_forge/reports/
├── forge_daily_2026-05-05.md      ← markdown report (operator-readable)
├── forge_daily_2026-05-05.json    ← machine-readable result table
└── forge_queue.md                  ← rolling next-action queue (single file, updated each run)
```

### Markdown report structure (consistent across runs)

```
# FQL Forge Daily — YYYY-MM-DD
- Run: dry-run / report-only
- Candidates tested: N
- Verdict summary: P PASS / W WATCH / K KILL / R RETEST
- Per-candidate result table
- Architecture trend notes (if patterns emerge)
- Next-batch recommendation
- Tripwires fired: 0 (or alert details)
```

### JSON report (for machine consumption)

```json
{
  "date": "2026-05-05",
  "run_mode": "dry-run",
  "candidates_tested": 5,
  "verdict_counts": {"PASS": 2, "WATCH": 1, "KILL": 2, "RETEST": 0},
  "results": [
    {"candidate": "...", "asset": "...", "metrics": {...}, "verdict": "PASS"}
  ],
  "next_batch_recommendation": ["...", "...", "..."],
  "tripwires_fired": []
}
```

### Rolling queue file

`forge_queue.md` is updated (not overwritten) each run with the latest "next safe Forge action" recommendation. Operator can scan this single file to see the current state without reading every daily report.

---

## How operator reviews

1. **Daily glance (eventually automated):** check the latest `forge_daily_<date>.md` for verdict counts and any tripwires. If counts look normal and no tripwires, no action.
2. **Weekly review (Friday):** scan the week's daily reports for patterns; look at `forge_queue.md` for recommended next actions; decide whether to authorize any promotion or registry append.
3. **Tripwire response:** if any `_TRIPWIRE_*.md` exists in the reports dir, operator must read it before allowing the loop to resume.
4. **Twice-monthly assessment:** the daily reports feed the twice-monthly truth-audit per `ELITE_OPERATING_PRINCIPLES.md` Principle 6.

---

## Activation steps (when operator decides to enable Phase B scheduling)

1. Operator reviews `scripts/com.fql.forge-daily-loop.plist.disabled`
2. Operator copies it: `cp scripts/com.fql.forge-daily-loop.plist.disabled ~/Library/LaunchAgents/com.fql.forge-daily-loop.plist`
3. Operator loads it: `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.fql.forge-daily-loop.plist`
4. Loop fires daily at 19:00 ET (or operator-edited schedule)
5. To deactivate: `launchctl bootout gui/$(id -u)/com.fql.forge-daily-loop` and remove the plist

The plist provided is in this repo as `.disabled` extension precisely so it cannot be loaded accidentally.

---

## Design reference: what this is NOT

- **Not Phase 0 hot lane activation.** Phase 0 (hot lane Track A start) remains gated on TRS-2026-06 second clean cycle. The daily loop is pre-Phase-0 reporting, not the Phase 0 generator.
- **Not autonomous promotion.** Daily loop reports candidates; never appends to registry, never promotes, never changes portfolio.
- **Not unbounded.** Tripwires + cost ceilings + boundedness all apply (per `post_may1_build_sequence.md` §3.3 §6).
- **Not a Lane A surface.** All file writes target `research/data/fql_forge/reports/` — a fresh sub-tree under Lane B research data; no overlap with `data/processed/`, `logs/`, `state/`, or registry.

---

## Files in this design

- `docs/fql_forge/forge_automation_design.md` — this doc
- `research/fql_forge_batch_runner.py` — existing batch runner (CLI-only, on-demand)
- `research/fql_forge_daily_loop.py` — daily orchestrator (NEW; CLI-only initially)
- `scripts/com.fql.forge-daily-loop.plist.disabled` — disabled launchd plist (provided but not loaded)
- `research/data/fql_forge/reports/` — output directory (created on first run)

---

*Filed 2026-05-05. Lane B / Forge. Phase A (manual CLI only) operative now; Phase B (scheduled launchd) requires explicit operator activation.*
