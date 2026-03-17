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
- Output: research/data/allocation_matrix.json

### Controller Unification
- Created engine/strategy_universe.py: canonical strategy adapter
- Registry (strategy_registry.json) is now single source of truth
- Execution path reads from registry via build_portfolio_config()
- Removed circular import (PORTFOLIO_CONFIG in regime controller)
- Freshness checks and safe fallback to hardcoded config

### State Integrity Hardening
- 127 tests (activation scoring, state machine, regime engine, allocation, atomic writes, strategy universe)
- Atomic writes for 8 critical JSON state files
- Registry backup rotation (keep 5 versions)

### Asset Expansion
- Canonical asset config: engine/asset_config.py (16 assets, 6 classes)
- Minimum viable watchdog: research/system_watchdog.py (5 checks, SAFE_MODE)
- FX data onboarded: 6E, 6J, 6B ($4.30 total, 300K+ bars)
- ZF (5-Year Treasury) data onboarded
- Databento loader expanded to support all 11 symbols

### Cross-Asset Research
- 50 cross-asset transfer tests across ZN/ZB/6E/6J/6B (0 direct transfers)
- 6J calibration fix (point_value 100x correction)
- Finding: current strategy DNA is equity-index-specific

### Native Strategy Prototypes
- FX Session Breakout (6J: PF 1.20, ADVANCE; 6E/6B: REJECT)
- Rate Intraday Mean Reversion (ZN/ZB/ZF: all NO_EDGE)
- FX Daily-Bar Trend (6J: PF 1.46, unstable WF; opened multi-horizon lane)
- 6J Tokyo-London Transition (short PF 1.09, PROMISING_REFINEMENT)
- Rate Daily-Bar Momentum (ZF: PF 2.52, insufficient trades)

### Validated Non-Equity Strategies (3 probation candidates)
- DailyTrend-MGC-Long: PASS 7/8, PF 3.65, daily bars, REDUCED tier
- MomPB-6J-Long-US: CONDITIONAL_PASS 5/7, PF 1.58, US session, REDUCED tier
- FXBreak-6J-Short-London: CONDITIONAL_PASS 5/8, PF 1.20, London session, MICRO tier
- DualThrust Daily: convergent confirmation for MGC daily long (PF 2.79)
- MomPB-6E-Long-US: FAIL 4/8 (walk-forward unstable, regime vulnerable)

### Factory Pipeline
- batch_first_pass.py: rapid multi-asset strategy evaluation with auto-classification
- 12 strategies spec'd, coded, and batch-tested
- 5 strategy specs drafted (MCL-Breakout, RSI2-Bounce, EIA-Reaction, GapFill, NR7-Breakout)
- Factory throughput: spec → code → batch test → classified in ~15 minutes
- Scheduler integration: biweekly_batch_first_pass job (Tue/Thu automatic)
- Implementation bugs caught and fixed (NR7 entry timing, EIA day filter)

### Registry Hardening (v3.0)
- 65 strategies with enriched metadata
- Rejection taxonomy: 7 reason codes, all 21 rejections classified
- Source lineage categories: internal/tradingview/academic/expansion/factory/practitioner
- Lifecycle stages: discovery/first_pass/forward_validation/deployed/archived
- Batch first-pass reports linked (7), validation reports linked (19)

### Platform Intelligence
- Strategy Genome Classifier: 9-dimension classification, overcrowding + gap analysis
- System Integrity Monitor: 7-check weekly self-diagnostic (scheduler, registry, data, forward runner, probation, allocation)
- Portfolio Contribution Report: backtest + forward contribution, overlap/complementarity analysis
- Dormant Harvest Infrastructure: 5 source lanes (all disabled), gap-aware targeting from genome map

### Forward Runner Integration
- 10-strategy portfolio across 4 assets (MES, MNQ, MGC, 6J), 2 horizons
- Probation strategies included with status/tier/horizon logging
- ASSET_CONFIG from canonical engine/asset_config.py
- Daily-bar strategy handling (resample detection)

### Automation
- 3 launchd agents active: daily (17:30), twice-weekly (Tue/Thu 18:00), weekly (Fri 18:30)
- Guarded forward runner designed but disabled (double safety: plist + enable flag)
- All agents with lockfile protection, explicit PATH, failure logging

### Operating Governance
- Weekly operating rhythm (OPERATING_RHYTHM.md): ~75-120 min/week
- Probation review criteria (PROBATION_REVIEW_CRITERIA.md): Week 2/4/8/12 checkpoints
- Promotion playbook (PROMOTION_PLAYBOOK.md): evidence hierarchy, decision rules
- Promotion checklist (PROMOTION_CHECKLIST.md): operational steps, rollback plan
- Salvage policy (SALVAGE_POLICY.md): max 1 attempt, 30-day expiry, family closure rules
- Security policy (SECURITY_POLICY.md): GREEN/YELLOW/RED IP classification
- Weekly scorecard (weekly_scorecard.py): 7-section Friday review
- Probation decision journal (probation_journal.py): structured evidence + decision logging
- Data depth roadmap (DATA_DEPTH_ROADMAP.md): $18.89 to backfill all expansion assets
- Controlled harvest activation plan (HARVEST_ACTIVATION.md)
- Legacy folder inventory: 12 items scanned, 0 extractable strategies

### System State at Session End
- 65 strategies in registry (5 core, 12 probation, 26 idea, 21 rejected, 1 testing)
- 127 automated tests, all passing
- Operate-and-observe mode active
- Week 8 formal probation review is next major decision point

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
