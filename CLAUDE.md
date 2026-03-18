# Algo Lab — Claude Instructions

## Current Mode: OPERATE AND OBSERVE

FQL is in operate-and-observe mode. Do NOT start new build lanes, prototype
strategies, or infrastructure projects unless the weekly scorecard flags a
real issue or a probation review threshold is hit.

**Daily priority:** Help run `./scripts/start_forward_day.sh` on market days.
**Friday priority:** Help review `python3 research/weekly_scorecard.py` output.

## Probation Portfolio (5 strategies accumulating forward evidence)

| Strategy | Asset | Horizon | Tier | Target Trades | Promotion PF |
|----------|-------|---------|------|---------------|-------------|
| DailyTrend-MGC-Long | MGC | Daily | REDUCED | 15 | > 1.2 |
| MomPB-6J-Long-US | 6J | Intraday (US) | REDUCED | 30 | > 1.2 |
| FXBreak-6J-Short-London | 6J | Intraday (London) | MICRO | 50 | > 1.1 |
| PreFOMC-Drift-Equity | MES | Event (FOMC) | MICRO | 8 | > 1.2 |
| TV-NFP-High-Low-Levels | MES | Event (NFP) | MICRO | 8 | > 1.1 |

Review criteria: `docs/PROBATION_REVIEW_CRITERIA.md`
Week 8 formal review is the next major decision point.

## Automation (3 active launchd agents)

- **Daily:** weekdays 17:30 ET — 6 research jobs (health, half-life, contribution, controller, report, drift)
- **Twice-weekly:** Tue/Thu 18:00 ET — batch_first_pass factory testing
- **Weekly:** Fri 18:30 ET — integrity monitor, kill criteria, auto-report
- **Forward runner:** DESIGNED but DISABLED (`scripts/com.fql.forward-trading.plist`)

## System State

- **Registry:** 103 strategies, schema v3.0, rejection taxonomy
- **Genome map:** 9-dimension classification, overcrowding + gap analysis
- **Factory:** batch_first_pass operational, 20+ reports processed
- **Forward runner:** 10 strategies across 4 assets, 2 horizons, probation included
- **Tests:** 127 passing
- **Harvest engine:** Phase 1 active — 5 of 6 lanes running (legacy_revival disabled)
- **Factor coverage:** MOMENTUM 54%, STRUCTURAL 1, EVENT 2 (probation), CARRY 0 (GAP), VOLATILITY 0 (GAP)
- **Conversion queue:** Natural pause — no strong candidates pending

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

- `docs/FQL_ARCHITECTURE.md` — 7-layer system reference
- `docs/OPERATING_RHYTHM.md` — weekly cadence
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
