# FQL Changelog

*Major architectural changes, module additions, and system milestones.*

---

## 2026-03-15

### Architecture Documentation
- Created `FQL_ARCHITECTURE.md` -- definitive 7-layer system reference
- Created `FISHER_QUANT_OPERATING_PRINCIPLES.md` -- platform constitution
- Created `SYSTEM_INTEGRITY_MONITOR.md` -- system health monitoring specification
- Created `STRATEGY_DISCOVERY_PIPELINE.md` -- discovery architecture documentation
- Created `CHANGELOG.md` -- this file

### Infrastructure
- Migrated repo from `~/Desktop/Algo Trading` to `~/projects/Algo Trading`
- Hardened launchd automation: wrapper script with lockfile, explicit PATH, failure logging
- Fixed Python output buffering under launchd (PYTHONUNBUFFERED=1)
- Switched plist from direct Python invocation to bash wrapper script
- Added duplicate-run protection (PID-based lockfile)
- Verified end-to-end launchd automation (6/6 daily jobs SUCCESS)

### Session Drift Integration
- Integrated session drift as 10th controller scoring dimension
- Activation scoring model now uses 10 weighted dimensions

### Counterfactual Engine
- Built counterfactual engine with 6 opportunity-cost metrics
- Added to scheduled execution pipeline

### Live Drift Monitor
- Added session/time-of-day drift detection
- 6 drift dimensions, 3 alert tiers (NORMAL/DRIFT/ALARM)
- Session concentration penalty

### Execution Quality Monitor
- Built signal retention, slippage, and blocking analysis
- Tracks execution quality vs theoretical performance

---

## Pre-2026-03-15

### Major Milestones (from git history)
- Portfolio Regime Controller with 10-dimension activation scoring
- Strategy State Machine (8 states, explicit transitions)
- Strategy half-life monitor (edge decay tracking)
- Strategy kill criteria (4-dimension automated triggers)
- 60-point automated health check system
- Walk-forward matrix (3-dimension robustness)
- Strategy genome mapping and exposure clustering
- Crossbreeding engine and evolution scheduler
- Forward testing infrastructure (Phase 17, 100+ days)
- Daily research scheduler (19 automated jobs)
- Prop firm optimizer and portfolio simulator
- Strategy registry (57 strategies, institutional memory)

See `docs/research_log.md` for detailed chronological history.
