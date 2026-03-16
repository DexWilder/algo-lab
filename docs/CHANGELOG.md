# FQL Changelog

*Major architectural changes, module additions, and system milestones.*

---

## 2026-03-16

### Strategic Pivot: Expand Opportunity Set
- Full-stack assessment concluded infrastructure is ahead of opportunity set
- 6 strategies on 3 correlated assets = ~2-3 independent bets (bottleneck)
- Revised roadmap: Safety → Asset Expansion → Multi-Horizon → Evolution → Factor Decomposition
- FQL mission shifts from "build smart system" to "diversified strategy factory"

### Portfolio Regime Allocation
- Built allocation engine: 6-tier sizing (OFF/MICRO/REDUCED/BASE/BOOST/MAX_ALLOWED)
- 5-stage pipeline: base tier, contribution/CF adjustments, crowding dampening, session-specific, validation
- Session-specific allocation tiers (morning/midday/afternoon)
- 13 allocation reason codes for full decision explainability
- Integrated into controller as Phase 4 (post-scoring)
- Added Section 10 to daily report (markdown + terminal)
- Output: research/data/allocation_matrix.json

### Controller Unification
- Created engine/strategy_universe.py: canonical strategy adapter
- Registry (strategy_registry.json) is now single source of truth
- Execution path reads from registry via build_portfolio_config()
- Removed circular import (PORTFOLIO_CONFIG in regime controller)
- Added execution_config to registry schema for 6 core strategies
- Freshness checks and safe fallback to hardcoded config

### State Integrity Hardening
- Created test suite: 127 tests (activation scoring, state machine, regime engine, allocation, atomic writes, strategy universe)
- Atomic writes for 8 critical JSON state files
- Registry backup rotation (keep 5 versions)
- research/utils/atomic_io.py utility module

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
