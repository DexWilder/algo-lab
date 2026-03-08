# ALGO-FAMILY-PB-001: PB Trend -- Pullback Trend-Following

## Family Overview

- **Family ID**: ALGO-FAMILY-PB-001
- **Family Name**: PB Trend -- Pullback Trend-Following
- **Strategy Class**: Trend continuation via pullback entries
- **Entry Model**: Pullback retrace into established trend
- **Risk Model**: ATR-based stops and targets
- **Exit Model**: Bracket (stop + target), fixed R multiples
- **Source**: Extracted from Lucid v6.3 trend pullback module
- **Location**: `strategies/pb_trend/`

---

## Members

### PB-MGC-Short v1.1

| Metric         | Value         |
|----------------|---------------|
| Profit Factor  | 2.22          |
| Sharpe Ratio   | 5.07          |
| Trade Count    | 19            |
| Total PnL      | $741          |
| Max Drawdown   | $283          |
| Session        | 09:30-10:30 ET|
| Asset          | MGC           |
| Direction      | Short only    |

### PB-MNQ-Long

| Metric         | Value         |
|----------------|---------------|
| Profit Factor  | 1.12          |
| Sharpe Ratio   | 0.94          |
| Trade Count    | 343           |
| Total PnL      | $1,921        |
| Max Drawdown   | $1,951        |
| Asset          | MNQ           |
| Direction      | Long only     |

### PB-MES-Short

| Metric         | Value         |
|----------------|---------------|
| Profit Factor  | 1.10          |
| Sharpe Ratio   | 0.75          |
| Trade Count    | 167           |
| Total PnL      | $586          |
| Max Drawdown   | $884          |
| Asset          | MES           |
| Direction      | Short only    |

---

## Portfolio Metrics (All 3 Combined)

| Metric              | Value                                  |
|----------------------|----------------------------------------|
| Combined PnL         | $3,341                                |
| Combined Sharpe      | 1.20                                  |
| Combined MaxDD       | $1,950                                |
| Return Correlations  | All < 0.02 (effectively uncorrelated) |
| Trade Overlap        | < 12% across all pairs                |

The near-zero correlations confirm that these three members operate on independent edges across different assets, directions, and sessions. Combining them produces a portfolio with better risk-adjusted returns than any single member.

---

## Automation Readiness Checklist

Applies to all three members.

| Criterion                                  | Status |
|--------------------------------------------|--------|
| No discretionary inputs                    | YES    |
| Deterministic signals                      | YES    |
| Fixed session handling                     | YES    |
| Stable stop/target logic (ATR-based)       | YES    |
| No repaint risk (closed bars only)         | YES    |
| Executable with market/limit/stop orders   | YES    |
| Controller layer separation               | YES    |
| 1+ year tested (2 years)                  | YES    |
| Parameter stability verified (16 variations tested, all profitable) | YES |

All members pass every automation readiness criterion. Signals are fully deterministic, use only closed-bar data, and require no manual judgment. The controller layer is separated per the platform-agnostic architecture (strategy engine / risk controller / execution adapter).

---

## Notes

- PB-MGC-Short is the strongest individual performer (highest PF and Sharpe) but has the smallest sample size (19 trades). Extended data collection is recommended.
- PB-MNQ-Long provides the bulk of trade volume (343 trades) and PnL ($1,921) but has a tighter PF (1.12) and higher drawdown ($1,951).
- PB-MES-Short is the weakest individual member but contributes meaningfully to portfolio diversification due to near-zero correlation with the other two.
- All 16 parameter variations tested were profitable, indicating robust parameter stability across the family.
