# System Integrity Monitor

*Specification for periodic diagnostics that ensure all FQL automation and modules remain aligned.*
*Last updated: 2026-03-15*

---

## Purpose

Prevent system drift by running periodic health diagnostics across all FQL subsystems. The System Integrity Monitor consolidates existing health checks into a single, actionable report.

---

## Current Health Infrastructure (Built)

FQL already has several health monitoring components:

| Module | What It Checks | Cadence |
|--------|---------------|---------|
| `research/fql_health_check.py` | 60-point failure detection across 5 categories | Daily (scheduled) |
| `research/live_drift_monitor.py` | Forward-test edge drift (6 dimensions, 3 alert tiers) | Daily (scheduled) |
| `execution/execution_quality_monitor.py` | Slippage, latency, fill quality | On-demand |
| `research/strategy_half_life_monitor.py` | Edge decay tracking (4 statuses) | Daily (scheduled) |
| `research/strategy_kill_criteria.py` | Automated kill triggers (4 dimensions) | Weekly (scheduled) |
| `research/counterfactual_engine.py` | Opportunity-cost analysis (6 metrics) | On-demand |

---

## System Integrity Report Specification

The System Integrity Monitor should produce a consolidated report covering all subsystems.

### Report Sections

**1. Automation Health**
- Scheduler: last run timestamp, success/error count today
- launchd agent: loaded status, last exit code
- Lockfile: present (running) or absent (idle)
- Log files: exist, writable, not stale

Source: `research/data/scheduler_log.json`, `research/logs/`

**2. Scheduler Job Health**
- Per-job status: last run, last status, duration
- Jobs that have NEVER_RUN on their expected cadence
- Jobs with ERROR status in last 7 days
- Jobs with increasing duration trend (potential performance issue)

Source: `research/fql_research_scheduler.py --status`

**3. Strategy Registry Consistency**
- Total strategies by status (core, probation, testing, idea, rejected)
- Strategies missing required fields
- Strategies with stale review dates (>30 days for core, >90 days for others)
- Registry schema version check

Source: `research/data/strategy_registry.json`

**4. Controller Health**
- Last activation matrix timestamp
- Strategies currently ON, REDUCED, OFF, DISABLED
- Any strategy stuck in a state for >14 days without review
- Reason code distribution (are decisions well-explained?)

Source: `research/data/portfolio_activation_matrix.json`, `research/reports/`

**5. Drift Monitor Status**
- Strategies with active DRIFT alerts
- Strategies with active ALARM alerts
- Session concentration warnings
- Drift alert age (how long has each been active?)

Source: `research/data/live_drift_log.json`

**6. Edge Lifecycle Health**
- Strategies with DECAYING or ARCHIVE_CANDIDATE half-life status
- Strategies with active kill criteria flags
- Strategies with dilutive contribution (negative marginal Sharpe)
- Time since last strategy promotion or retirement

Source: Half-life reports, kill criteria reports, contribution analysis

**7. Data Integrity**
- Last data update timestamp
- Data gaps or missing bars
- Data file sizes (anomaly detection)

Source: `state/data_update_state.json`, `research/data_integrity_check.py`

**8. Log Anomalies**
- Errors in launchd stderr log
- Uncaught exceptions in per-run logs
- Scheduler log ERROR entries in last 7 days

Source: `research/logs/`

---

## Output Format

### Console Summary

```
FQL System Integrity Report -- 2026-03-15
=========================================

Automation:       OK     (last run: 2026-03-15 17:30, 6/6 success)
Scheduler:        OK     (19 jobs configured, 0 errors this week)
Registry:         OK     (57 strategies, 6 core, 0 missing fields)
Controller:       OK     (6 active, 0 stuck, last run: today)
Drift Monitor:    WARN   (2 ALARM alerts active)
Edge Lifecycle:   OK     (0 ARCHIVE_CANDIDATE, 1 DECAYING)
Data Integrity:   OK     (last update: today, no gaps)
Logs:             OK     (no errors in last 7 days)

Overall: HEALTHY (1 warning)
```

### Status Levels

- **OK** -- No issues detected
- **WARN** -- Non-critical issue that should be reviewed
- **FAIL** -- Critical issue requiring immediate attention

Overall status: HEALTHY (all OK or WARN), DEGRADED (any FAIL), CRITICAL (multiple FAIL)

### JSON Report

Full details saved to `research/reports/integrity_report_YYYYMMDD.json` for trend tracking.

---

## Recommended Cadence

- **Weekly** -- Full system integrity report (automated via scheduler)
- **Daily** -- Subset checks already run by existing daily pipeline
- **On-demand** -- After any major code change, deployment, or incident

---

## Implementation Plan

### Phase 1: Consolidation (build `research/system_integrity_monitor.py`)
- Aggregate existing health check outputs into unified report
- Add scheduler and automation health checks
- Add registry consistency checks
- Output console summary + JSON report

### Phase 2: Scheduling
- Add as weekly job to `fql_research_scheduler.py`
- Add to daily decision report as summary section

### Phase 3: Alerting
- Flag FAIL conditions in daily report
- Eventually: webhook or email alerts for CRITICAL status

---

## Maintenance

This specification should be updated when:
- New monitoring modules are added
- New subsystems are built that need integrity checks
- Alert thresholds need adjustment based on operational experience
