# ORB Breakout + VWAP + Volume Filters — Conversion Baseline

**Strategy:** orb_009
**Family:** orb
**Source:** https://www.tradingview.com/script/wLSGHPUe-ORB-Breakout-Strategy-with-VWAP-and-Volume-Filters/
**Run date:** 2026-03-07 22:16:42
**Conversion type:** Faithful (no optimization)

## Results Summary

- **MES both**: 432 trades, PF=1.122, WR=51.4%, Sharpe=0.6782, PnL=$2,096.25, MaxDD=$2,780.00
- **MES long**: 215 trades, PF=1.111, WR=51.2%, Sharpe=0.5855, PnL=$792.50, MaxDD=$1,262.50
- **MES short**: 217 trades, PF=1.13, WR=51.6%, Sharpe=0.7152, PnL=$1,303.75, MaxDD=$2,357.50
- **MGC both**: 199 trades, PF=1.516, WR=49.2%, Sharpe=1.97, PnL=$4,201.00, MaxDD=$1,254.00
- **MGC long**: 106 trades, PF=1.987, WR=51.9%, Sharpe=3.6284, PnL=$3,022.00, MaxDD=$826.00
- **MGC short**: 93 trades, PF=1.232, WR=46.2%, Sharpe=0.9405, PnL=$1,179.00, MaxDD=$1,102.00
- **MNQ both**: 362 trades, PF=1.139, WR=52.2%, Sharpe=0.7539, PnL=$4,002.50, MaxDD=$4,032.50
- **MNQ long**: 171 trades, PF=1.237, WR=53.2%, Sharpe=1.1341, PnL=$2,738.50, MaxDD=$2,339.00
- **MNQ short**: 191 trades, PF=1.073, WR=51.3%, Sharpe=0.4124, PnL=$1,264.00, MaxDD=$2,985.50

## Notes

- Faithful conversion from Pine Script v5
- No parameter optimization applied
- Engine: fill-at-next-open (same as PB baseline)
- Data: Databento CME 5m
