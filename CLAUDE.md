# Algo Lab — Claude Instructions

## Current Mode: CONTINUOUS DISCOVERY, SELECTIVE DEPLOYMENT

**Continuous catalog growth is a standing FQL principle.** The discovery
engine never idles. Harvesting, cataloging, tagging, clustering, blocker
mapping, and assessment run at all times — even when deployment is
bottlenecked, all probation slots are full, or no conversion is planned.

**Elite standard is a standing FQL principle.** FQL does not optimize for
quantity, activity, or mediocre passable results. Every strategy, family,
unlock, and rule must earn its place. Weak ideas are pruned quickly. Strong
ideas are refined ruthlessly. Forward evidence outranks backtest fantasy.
Discovery is relentless, but standards are uncompromising.

Conversion, testing, probation, and live portfolio changes remain selective
and gated. These two clocks run at different speeds, on purpose.

**Do NOT** start new build lanes, prototype strategies, or infrastructure
projects unless the weekly scorecard flags a real issue or a probation
review threshold is hit. Discovery work (scan, stage, tag, assess) is
always appropriate.

### Proactive Session Behaviors

Claude should do these automatically at the start of relevant sessions:

- **Market-day session (when requested):** Run `./scripts/start_forward_day.sh`
  (not scheduled — manual start, automated downstream reporting)
- **Monday session:** Scan Claw outputs from `~/openclaw-intake/inbox/harvest/`
  and `inbox/refinement/`. Dedupe, tag, cluster, present for accept/reject.
  Also run `python3 research/harvest_engine.py --scan`.
- **Friday session:** Read Claw cluster report from `inbox/clustering/`,
  verify assignments. Then run full review sequence:
  ```bash
  python3 research/weekly_scorecard.py --save
  python3 research/weekly_intake_digest.py --save
  python3 research/operating_dashboard.py
  ```
  Present consolidated summary with recommended actions.
- **Sunday/Monday:** Read Claw gap refresh from `inbox/assessment/`, update
  `inbox/_priorities.md` and `inbox/_family_queue.md` for next week's Claw runs.
- **Monthly (or after 20+ new registry entries):** Refresh genome map and
  factor decomposition.

See `docs/CONTINUOUS_DISCOVERY_OPERATING_PLAN.md` for the full operating plan.
See `docs/CLAW_CATALOG_ENGINE.md` for Claw's scheduled task definitions.

## Probation Portfolio

**Primary workhorse candidates (promoted 2026-04-06 and 2026-04-08):**

| Strategy | Asset | Archetype | Baseline PF | Trades | Status |
|----------|-------|-----------|------------|--------|--------|
| **XB-ORB-EMA-Ladder-MNQ** | MNQ | Workhorse | 1.62 | 1183 | Live forward |
| **XB-ORB-EMA-Ladder-MCL** | MCL | Workhorse | 1.33 | 898 | Live forward |

Both use the same strategy code: ORB breakout + EMA slope filter + profit_ladder
exit with `stop_mult=2.0`. Cross-asset validated on MNQ/MES/MGC/M2K (equity+gold)
and MCL (energy). Does NOT extend to rates (ZN/ZF/ZB) or FX (6J/6E/6B — small
sample). See `docs/` and `research/data/xb_orb_*_sweep_results.json` for full
sweep and validation results.

**Other probation / watch strategies:**
- DailyTrend-MGC-Long, MomPB-6J-Long-US, FXBreak-6J-Short-London (legacy watch)
- NoiseBoundary-MNQ-Long, ZN-Afternoon-Reversion, VolManaged-EquityIndex-Futures
- PreFOMC-Drift-Equity, TV-NFP-High-Low-Levels (event sleeves)

Review criteria: `docs/PROBATION_REVIEW_CRITERIA.md`

## Automation (8 active launchd agents)

- **Forward day:** weekdays 17:00 ET — data refresh + forward paper trading
- **Daily research:** weekdays 17:30 ET — 6 research jobs + report stack
- **Operator digest:** weekdays 18:00 ET — exception-only daily intelligence (`scripts/operator_digest.py`)
- **Twice-weekly:** Tue/Thu 18:00 ET — batch_first_pass factory testing **+ auto mass-screen of untested strategies**
- **Weekly:** Fri 18:30 ET — integrity monitor, kill criteria, auto-report, throughput audit
- **Claw control loop:** every 30 min — Claw coordination, EOD audit at 22:00
- **Source helpers:** every 3 days — GitHub/Reddit/YouTube/blog/digest lead fetching
- **Watchdog:** every 5 min — gateway/claw/job health, self-healing recovery, CLEARED transition logging

The operator digest is the primary interface. It auto-runs daily and:
- Suppresses noise (only surfaces state changes)
- Generates decision memos when thresholds are hit
- Sends macOS notification only for ACTION/ALERT items
- Emits "nothing actionable" when system is nominal
- **Shows dormant inventory counts every day** (coded untested, ideas untested, harvest notes)
- On-demand: `fql digest`

## Factory Classification (dual archetype, 2026-04-07)

The factory classifies every strategy through one of two paths:

**Workhorse path** (trades ≥ 500):
- PF > 1.2, walk-forward H1/H2 both > 1.0
- Top-3 < 30%, Top-5 < 45%, Top-10 < 55% concentration
- Median trade ≥ 0
- Max single year < 40%
- Catches continuous intraday grinders like xb_orb_ema_ladder

**Tail-engine path** (trades < 500):
- PF ≥ 1.15 for VIABLE, ≥ 1.30 for STRONG
- Max single instance < 35%, positive instance fraction ≥ 60%
- Instance CV < 3.0 (cross-instance stability)
- Max DD duration < 900d, max year < 50%
- Catches sparse event/session/carry strategies

**Routing rule**: trades < 500 → both paths run, stricter verdict wins.
Prevents sparse strategies from cheesing the workhorse "directional split"
SALVAGE path.

**Automatic features**:
- Silent failure detector: flags strategies producing 0 signals on 10k+ bars
- Per-event decomposition: when a strategy exposes `EVENT_CLASSIFIER`, the
  factory auto-breaks down results by event type and emits verdicts
  (ISOLATE X / ALL EVENTS WEAK / COMPOSITE VIABLE)
- Dormant safety net: 4 defensive layers (runtime, twice-weekly clear,
  daily digest line, weekly throughput audit)

## System State (2026-04-08)

- **Registry:** 115+ strategies, schema v3.2, rejection taxonomy
- **Genome map:** 9-dimension classification, overcrowding + gap analysis
- **Factory:** batch_first_pass with dual-archetype classification, silent
  failure detector, auto per-event decomposition
- **Forward runner:** probation includes XB-ORB-EMA-Ladder on MNQ + MCL
  (two workhorse candidates), plus legacy watch/event sleeves
- **Harvest engine:** Phase 1 active — Claw lanes running, ~127 notes queued
- **Energy gap:** FILLED via cross-asset extension of xb_orb_ema_ladder to
  MCL (not via dedicated crude prototypes, which all failed)
- **Dormant safety net:** 4-layer defense (silent failure detector, auto
  mass-screen, daily dormant digest line, weekly throughput audit)
- **Validation doctrine:** positive median trade, cross-asset generalization,
  sample size, low concentration — all four required for workhorse ADVANCE

## Auto-Commit & Push

After completing any phase, task, or meaningful unit of work:
1. `git add` all new and modified files (be specific, no `git add .`)
2. `git commit` with a clear message summarizing what was done
3. `git push origin main`
4. Verify clean working tree with `git status`

Do this automatically — never wait for the user to ask.

## Milestone Snapshots

Create milestone tags at major checkpoints:
- Strategy promoted to parent
- Portfolio structure materially changes
- Research phase completes
- Deployment infrastructure changes materially

```bash
./scripts/create_milestone.sh "v<major>.<minor>-phase<N>-<short-name>" "Description"
```

See `docs/release_workflow.md` for full details.

## Key Documentation

- `docs/CONTINUOUS_DISCOVERY_OPERATING_PLAN.md` — discovery vs deployment split
- `docs/CLAW_CATALOG_ENGINE.md` — Claw weekly schedule, output structure, governance
- `docs/FQL_ARCHITECTURE.md` — 7-layer system reference
- `docs/OPERATING_RHYTHM.md` — weekly cadence (superseded by discovery plan)
- `docs/PROBATION_REVIEW_CRITERIA.md` — promotion/downgrade thresholds
- `docs/ASSET_EXPANSION.md` — onboarding checklist for new assets
- `docs/CHANGELOG.md` — architectural change log

## General

- Always read files before editing them
- Prefer editing existing files over creating new ones
- Follow existing code patterns and conventions in the repo
- Use `engine/asset_config.py` for asset definitions (not hardcoded dicts)
- Use `engine/strategy_universe.py` for strategy configs (not PORTFOLIO_CONFIG)
- Use `research/utils/atomic_io.py` for all critical JSON writes
