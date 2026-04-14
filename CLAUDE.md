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

**Primary workhorse candidates (XB-ORB-EMA-Ladder family, promoted 2026-04-06 / 04-08 / 04-13):**

| Strategy | Asset | Archetype | Baseline PF | Trades | Promoted | Status |
|----------|-------|-----------|------------|--------|----------|--------|
| **XB-ORB-EMA-Ladder-MNQ** | MNQ | Workhorse | 1.62 | 1183 | 2026-04-06 | Live forward |
| **XB-ORB-EMA-Ladder-MCL** | MCL | Workhorse | 1.33 | 898  | 2026-04-08 | Live forward |
| **XB-ORB-EMA-Ladder-MYM** | MYM | Workhorse | 1.67 | 340  | 2026-04-13 | Live forward |

All three use the same strategy code: ORB breakout + EMA slope filter +
profit_ladder exit with `stop_mult=2.0`. MYM was added after the intraday
autocorrelation screen flagged it as the top expansion target. Cross-asset
validated on MNQ/MES/MGC/M2K (equity+gold), MCL (energy), MYM (equity
index). Does NOT extend to rates (ZN/ZF/ZB) or FX (6J/6E/6B — small
sample). See `research/data/xb_orb_*_sweep_results.json` for full sweep
and validation results.

**XB-ORB probation governance lives in [`docs/XB_ORB_PROBATION_FRAMEWORK.md`](docs/XB_ORB_PROBATION_FRAMEWORK.md)**
(review gates at 20/30/50/100 forward trades, promotion/downgrade/archive
logic, behavioral flag criteria, core-promotion engineering checklist).
`docs/PROBATION_REVIEW_CRITERIA.md` holds only a pointer for the XB-ORB
family and governs the non-XB-ORB legacy watch set.

**Other probation strategies (non-XB-ORB, current as of 2026-04-14):**

*Intraday single-asset:*
- DailyTrend-MGC-Long (MGC, trend, daily bars, sparse)
- ZN-Afternoon-Reversion (ZN, afternoon rates reversion, full drift tier)
- TV-NFP-High-Low-Levels (MNQ, sparse event)
- VolManaged-EquityIndex-Futures (MES, vol-scaled sizing — excluded from per-trade drift by design)

*Out-of-band monthly:*
- Treasury-Rolldown-Carry-Spread (ZN/ZF/ZB 3-tenor carry spread, re-probated 2026-04-14, monthly rebalance via `research/run_treasury_rolldown_spread.py`; first live fire expected 2026-05-01)

*Removed from probation:* MomPB-6J-Long-US (archived), FXBreak-6J-Short-London (rejected — verified concentration catastrophe, see `docs/PROBATION_REVIEW_CRITERIA.md` §3), NoiseBoundary-MNQ-Long (archived), PreFOMC-Drift-Equity (rejected).

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

## System State (2026-04-14)

- **Registry:** 115+ strategies, schema v3.2, rejection taxonomy
- **Genome map:** 9-dimension classification, overcrowding + gap analysis
- **Factory:** batch_first_pass with dual-archetype classification, silent
  failure detector, auto per-event decomposition
- **Forward runner:** probation includes XB-ORB-EMA-Ladder on MNQ + MCL + MYM
  (three workhorse candidates — MYM wired 2026-04-13 via autocorrelation
  expansion screen), plus legacy watch/event sleeves
- **Harvest engine:** Phase 1 active — Claw lanes running, ~127 notes queued
- **Energy gap:** FILLED via cross-asset extension of xb_orb_ema_ladder to
  MCL (not via dedicated crude prototypes, which all failed)
- **Dormant safety net:** 4-layer defense (silent failure detector, auto
  mass-screen, daily dormant digest line, weekly throughput audit)
- **Validation doctrine:** positive median trade, cross-asset generalization,
  sample size, low concentration — all four required for workhorse ADVANCE

## Current Hold & May 1 Checkpoint

**Hold in effect** 2026-04-14 → 2026-05-01. Runtime code, strategy
lifecycle, portfolio composition, and launchd agents are frozen.
Documentation, data ops, registry hygiene, and preparation are
allowed. Full rules in `docs/HOLD_STATE_CHECKLIST.md`.

**Next event:** Treasury-Rolldown-Carry-Spread first live monthly
rebalance fires on 2026-05-01 (first business day). Verification
and decision procedure below.

### Operator sequence for May 1

1. **Confirm rebalance fired** — `launchctl list | grep treasury-rolldown` + tail `research/logs/treasury_rolldown_monthly_stdout.log`
2. **Inspect spread log** — run `docs/SPREAD_LOG_AUDIT_PROCEDURE.md` → one-line OK/WARN/FAIL verdict
3. **Run verification checks** — execute the 7 checks in `docs/MAY_1_TREASURY_ROLLDOWN_VERIFICATION.md`, fill in outcome table
4. **Render checkpoint decision** — feed verification output into `docs/MAY_1_CHECKPOINT_TEMPLATE.md` to produce exactly one of: Remain / Open FX-STRUCTURAL lane / Resume hardening queue / Investigate anomaly
5. **Commit the filled checkpoint** — commit message `Checkpoint 2026-05-01: [decision]`
6. **Log outcome** — update `docs/PORTFOLIO_TRUTH_TABLE.md` next-checkpoint section + `docs/HOLD_STATE_CHECKLIST.md` exit record

### Hold & checkpoint documentation

- `docs/HOLD_STATE_CHECKLIST.md` — frozen surfaces, allowed actions, breach conditions, exit criteria
- `docs/GOLDEN_SNAPSHOT_2026-04-14.md` — frozen reference state at hold entry (HEAD commit, runner universe, data freshness, health stack)
- `docs/DATA_BLOCKED_STRATEGY_RULE.md` — data-blocked vs quiet distinction; review-clock rule (applies to MYM and any future pipeline-gap incident)
- `docs/MAY_1_TREASURY_ROLLDOWN_VERIFICATION.md` — 7-check mechanics (pass/warn/fail per check, commands, action per outcome)
- `docs/MAY_1_CHECKPOINT_TEMPLATE.md` — decision wrapper (reads verification output, produces exactly one of four decisions)
- `docs/SPREAD_LOG_AUDIT_PROCEDURE.md` — documented audit with OK/WARN/FAIL verdict

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
- `docs/PROBATION_REVIEW_CRITERIA.md` — promotion/downgrade thresholds (non-XB-ORB)
- `docs/XB_ORB_PROBATION_FRAMEWORK.md` — authoritative governance for all XB-ORB-EMA-Ladder variants
- `docs/ELITE_PROMOTION_STANDARDS.md` — evaluation framework by strategy shape (prevents wrong-framework failure mode)
- `docs/PORTFOLIO_TRUTH_TABLE.md` — operator summary of current state (derived, not authoritative)

**Hold-window docs (2026-04-14 → 2026-05-01)** — see "Current Hold & May 1 Checkpoint" section above for purpose and usage:

- `docs/HOLD_STATE_CHECKLIST.md`
- `docs/GOLDEN_SNAPSHOT_2026-04-14.md`
- `docs/DATA_BLOCKED_STRATEGY_RULE.md`
- `docs/MAY_1_TREASURY_ROLLDOWN_VERIFICATION.md`
- `docs/MAY_1_CHECKPOINT_TEMPLATE.md`
- `docs/SPREAD_LOG_AUDIT_PROCEDURE.md`
- `docs/ASSET_EXPANSION.md` — onboarding checklist for new assets
- `docs/CHANGELOG.md` — architectural change log

## General

- Always read files before editing them
- Prefer editing existing files over creating new ones
- Follow existing code patterns and conventions in the repo
- Use `engine/asset_config.py` for asset definitions (not hardcoded dicts)
- Use `engine/strategy_universe.py` for strategy configs (not PORTFOLIO_CONFIG)
- Use `research/utils/atomic_io.py` for all critical JSON writes
