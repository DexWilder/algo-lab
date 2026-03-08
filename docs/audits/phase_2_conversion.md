# Phase 2 Audit — Strategy Conversion

**Date Completed:** 2026-02-28
**Auditor:** Claude (engine builder)

---

## Objective

Faithfully convert top 3 harvested Pine Script strategies to Python. No optimization — preserve original parameters. Run baseline backtests on Databento CME 5m data (MES, MNQ, MGC).

## Conversion Rules

1. **No optimization** — preserve original parameters exactly
2. **Faithful conversion** — match source logic, don't improve
3. **Same interface** — `generate_signals(df) -> df` with signal/exit_signal/stop_price/target_price
4. **Same dataset** — Databento CME 5m bars (MES 141K, MNQ 141K, MGC 77K bars)

## Deliverables

| Strategy | Files | Baseline Dir | Status |
|----------|-------|-------------|--------|
| ORB-009 | `strategies/orb_009/strategy.py`, `meta.json` | `backtests/orb_009_baseline/` | Complete |
| VWAP-006 | `strategies/vwap_006/strategy.py`, `meta.json` | `backtests/vwap_006_baseline/` | Complete |
| ICT-010 | `strategies/ict_010/strategy.py`, `meta.json` | `backtests/ict_010_baseline/` | Complete |
| Generic runner | `backtests/run_conversion_baseline.py` | — | Complete |

## Baseline Results (Gross, No Costs)

### ORB-009 — Opening Range Breakout + VWAP + Volume
| Asset | Mode | PF | Sharpe | Trades | PnL | MaxDD |
|-------|------|-----|--------|--------|-----|-------|
| MGC | Long | 1.99 | 3.63 | 106 | $3,022 | $826 |
| MGC | Both | 1.52 | 1.97 | 199 | $4,201 | $1,254 |
| MES | Both | 1.12 | 0.68 | 432 | $2,096 | $2,780 |
| MNQ | Both | 1.14 | 0.75 | 362 | $4,003 | $4,033 |

**Verdict:** Strong edge on MGC-Long. Weak on MES/MNQ.

### VWAP-006 — VWAP-RSI Scalper
| Asset | Mode | PF | Sharpe | Trades | PnL | MaxDD |
|-------|------|-----|--------|--------|-----|-------|
| MES | Long | 1.21 | 1.32 | 572 | $2,879 | $1,245 |
| MGC | Long | 1.32 | 1.89 | 259 | $2,190 | $1,723 |
| MNQ | Both | 1.09 | 0.67 | 976 | $4,602 | $3,479 |

**Verdict:** Marginal edge, extremely high trade count. Cost sensitivity unknown at this stage.

### ICT-010 — Captain Backtest Session Sweep
| Asset | Mode | PF | Sharpe | Trades | PnL |
|-------|------|-----|--------|--------|-----|
| MES | Both | 0.65 | -2.95 | 232 | -$1,603 |
| MGC | Both | 0.79 | -1.56 | 155 | -$931 |
| MNQ | Both | 0.84 | -1.22 | 264 | -$1,547 |

**Verdict:** No edge. Negative PnL on every asset/mode. Rejected.

## Quality Checks

- [x] All 3 strategies produce non-zero signal counts
- [x] Trades.csv has correct columns (entry_time, exit_time, pnl, etc.)
- [x] Session flatten works (no positions past 15:15 ET)
- [x] Metrics in expected ranges
- [x] Correlation analysis completed against PB family
- [x] ORB-009 uncorrelated with PB family (r < 0.01)

## Conversion Rate

| Metric | Value |
|--------|-------|
| Attempted | 3 |
| Produced edge (gross PF > 1.5 on best asset) | 1 (ORB-009) |
| Marginal (gross PF 1.0-1.5) | 1 (VWAP-006) |
| No edge (PF < 1.0) | 1 (ICT-010) |
| Success rate | 33% (1/3 strong) |

## Decision

Advance ORB-009 MGC-Long to validation. Hold VWAP-006 for cost analysis. Archive ICT-010.

---
*Audit generated 2026-03-07*
