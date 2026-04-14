# Candidate Promotion Standard — Algo Lab

*Canonical promotion criteria. Updated 2026-03-10 (post-Phase 13).*

## Overview

Every strategy moves through a defined lifecycle. No strategy advances without meeting explicit criteria.

## Status Lifecycle

```
harvested (91 scripts)
    ↓ intake/manage.py + triage
converted (15 strategies)
    ↓ backtests/run_conversion_baseline.py
baselined
    ↓ research/validation/run_validation_battery.py
    │
    ├──→ rejected (12)          PF<1, no edge, structural overlap, or fragile
    ├──→ probation (4)          Edge real, needs more data or refinement
    └──→ parent (4)             Full validation, stability ≥7.0/10, 0 hard failures
              ↓
          portfolio              Vol Target weights, correlation verified, stress tested
              ↓
          deployment             Prop controller + execution adapter
```

## Validation Battery (Source of Truth)

**Script:** `research/validation/run_validation_battery.py`

The generic 10-criterion battery is the canonical promotion gate. It runs 6 tests:

| Test | What It Checks |
|------|----------------|
| Walk-forward (year splits) | Edge persists across time periods |
| Walk-forward (rolling) | No performance degradation |
| Regime stability | Edge works across vol/trend regimes |
| Asset robustness | Strategy works on multiple assets |
| Timeframe robustness | Edge not timeframe-specific |
| Statistical (Bootstrap, DSR, MC) | Edge is statistically real, survives resampling |
| Parameter stability | >60% of parameter combos remain profitable |

### Scoring

- **10 criteria**, each pass/fail
- **Stability score** = passes / 10
- **≥7.0/10 with 0 hard failures** → PROMOTE to parent
- **5.0-6.9 or failures driven by sample size** → PROBATION
- **<5.0** → REJECT

### Key Thresholds

| Metric | Minimum |
|--------|---------|
| Profit Factor | > 1.3 (primary combo) |
| Sharpe Ratio | > 1.2 (annualized) |
| Trade Count | ≥ 30 |
| Walk-Forward | ≥1 OOS segment profitable |
| Parameter Stability | > 60% of variations profitable |
| Bootstrap CI lower bound | > 1.0 |
| DSR | > 0.95 |
| MC P(ruin at $2K) | < 5% |
| Correlation vs parents | |r| < 0.25 |

## Two-Tier Discovery Gate (Phase 13+)

For new strategy families (not yet through full validation):

**Tier 1 — Discovery Gate** (advance to deeper analysis):
- PF > 1.15, Trades ≥ 30
- Median hold 5-20 bars (for MR strategies)
- No catastrophic TRENDING bleed
- Correlation vs any parent < 0.35

**Tier 2 — Promotion Candidate** (flag for validation battery):
- PF > 1.4, Sharpe > 1.8, Trades ≥ 80
- Positive portfolio impact (Sharpe delta > 0)
- RANGING_EDGE_SCORE > 0.3 (for MR strategies)

**Portfolio Usefulness Override:** If correlation < 0.1 and improves portfolio consistency, keep alive even if only passing Tier 1.

## Rejection Criteria

A strategy is rejected if:
- PF < 1.0 on all asset/mode combinations
- Edge collapses after removing top 1 trade
- No walk-forward segment is profitable
- Correlation > 0.35 vs any existing parent (structural overlap)
- Strategy relies on a single regime that no longer exists

Rejected strategies get a postmortem in `research/postmortems/`.

## Current Lab Status

See `CLAUDE.md` for authoritative current lab state, probation portfolio,
and automation status.
See `docs/strategy_registry.md` for the authoritative strategy status table.
(`docs/LAB_STATE.md` is retained only as a historical snapshot and is no
longer maintained as a status source.)

---
*Updated 2026-03-10. Previous version reflected Phase 3 state (2 strategies). This version reflects current 4-parent + 4-probation portfolio.*
