# Candidate Promotion Standard — Algo Lab

## Overview

Every strategy in the lab moves through a defined lifecycle. No strategy advances without meeting explicit criteria. This prevents premature deployment and ensures only robust, tested strategies enter the portfolio.

## Status Definitions

### 1. `converted`
**What it means:** Strategy has been faithfully converted from Pine Script to Python and produces non-zero signals on at least one asset.

**Requirements to achieve:**
- Faithful conversion from source (no optimization)
- `generate_signals(df)` implements the interface contract (signal, exit_signal, stop_price, target_price)
- Non-zero signal count on at least 1 target asset
- Session flatten works (no positions held past 15:15 ET)
- `meta.json` created with source attribution and parameters
- Baseline backtest run on MES/MNQ/MGC (both/long/short)
- Results saved to `backtests/<name>_baseline/`

**What happens next:** Review baseline metrics. If PF > 1.0 on any asset/mode combo, proceed to validation. If PF < 1.0 everywhere, create postmortem and reject or salvage components.

---

### 2. `candidate_validated`
**What it means:** Strategy has demonstrated robust, non-spurious edge through systematic testing.

**Requirements to achieve (ALL must pass):**

| Test | Criterion |
|------|-----------|
| **Profit Factor** | PF > 1.3 on primary asset/mode |
| **Sharpe Ratio** | Sharpe > 1.2 (annualized) |
| **Top-Trade Removal** | PF > 1.0 after removing top 3 trades |
| **Walk-Forward** | At least 1 out-of-sample segment profitable (PF > 1.0) |
| **Parameter Stability** | > 60% of parameter variations remain profitable (PF > 1.0) |
| **Monthly Consistency** | > 50% of months are profitable |
| **Trade Count** | Minimum 30 trades in baseline period |
| **Automation Ready** | Pure signal logic, no manual intervention required |

**Validation artifacts required:**
- `research/experiments/<name>_validation/`
  - `validation_report.md`
  - `robustness_metrics.json`
  - `top_trade_removal.csv`
  - `walk_forward_splits.csv`
  - `session_windows.csv`
  - `param_stability.csv`
  - `monthly_breakdown.csv`
  - `equity_curve.csv`

**What happens next:** Update `meta.json` status to `candidate_validated`. Add to `research/validated/`. Compute correlation against existing validated strategies.

---

### 3. `candidate_deployable`
**What it means:** Strategy is ready for live paper trading or funded account deployment.

**Requirements to achieve (ALL must pass):**

| Test | Criterion |
|------|-----------|
| **candidate_validated** | All validation criteria met |
| **Session Focus** | Identified optimal trading window with stable or improving edge |
| **Drawdown Profile** | MaxDD < 2% of starting capital OR < 3x average win |
| **Correlation** | |r| < 0.25 against all existing deployed strategies (daily PnL) |
| **No Structural Issues** | No cliff edges in parameter surface, no regime-specific collapse |
| **Walk-Forward Trend** | Performance not degrading across time periods (2024 → 2025 → 2026) |
| **Prop Compatibility** | Strategy works within prop account constraints (EOD flatten, max DD limits) |

**Additional requirements:**
- Recommended session window documented
- Risk parameters (position size, max contracts) calculated for target account
- Prop controller config created in `controllers/prop_configs/`
- Added to portfolio roster with assigned role (core/enhancer/stack component)

---

## Rejection Criteria

A strategy should be **rejected** (status: `rejected`) if:
- PF < 1.0 on all asset/mode combinations
- Edge collapses after removing top 1 trade
- No walk-forward segment is profitable
- < 20% of parameter variations are profitable
- Strategy relies on a single regime that no longer exists

Rejected strategies get a postmortem in `research/postmortems/` documenting:
- Why it failed
- Whether any logic is salvageable as components
- Lessons learned for future work

## Status Transitions

```
harvested → converted → candidate_validated → candidate_deployable
                ↓                  ↓
            rejected           rejected
                ↓                  ↓
          postmortem          postmortem
```

## Current Lab Status

| Strategy | Asset | Mode | Status | PF | Sharpe |
|----------|-------|------|--------|-----|--------|
| pb_trend | MGC | short | candidate_validated | 2.02 | 4.18 |
| pb_trend | MNQ | long | candidate_validated | 1.72 | 1.85 |
| orb_009 | MGC | long | candidate_validated | 1.99 | 3.63 |
| vwap_006 | MES | long | converted (side-specific) | 1.21 | 1.32 |
| ict_010 | — | — | rejected | <1.0 | negative |

---
*Created 2026-03-07. Update this table as strategies advance through the pipeline.*
