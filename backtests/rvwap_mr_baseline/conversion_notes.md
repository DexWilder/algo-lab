# RVWAP Mean Reversion — Conversion Baseline

**Strategy:** rvwap_mr
**Family:** vwap
**Source:** https://www.tradingview.com/script/oZcWZsvU-RVWAP-Mean-Reversion-Strategy/
**Run date:** 2026-03-08 20:14:28
**Conversion type:** Faithful (no optimization)

## Results Summary

- **MES both**: 1004 trades, PF=0.83, WR=51.6%, Sharpe=-1.8252, PnL=$-5,372.50, MaxDD=$5,942.50
- **MES long**: 527 trades, PF=0.766, WR=50.3%, Sharpe=-2.3319, PnL=$-4,463.75, MaxDD=$4,928.75
- **MES short**: 474 trades, PF=0.961, WR=52.7%, Sharpe=-0.3192, PnL=$-492.50, MaxDD=$1,433.75
- **MGC both**: 405 trades, PF=1.007, WR=53.1%, Sharpe=0.0366, PnL=$117.00, MaxDD=$3,252.00
- **MGC long**: 179 trades, PF=0.998, WR=58.7%, Sharpe=-0.0083, PnL=$-17.00, MaxDD=$4,961.00
- **MGC short**: 222 trades, PF=0.81, WR=47.8%, Sharpe=-1.2433, PnL=$-1,537.00, MaxDD=$1,787.00
- **MNQ both**: 904 trades, PF=0.868, WR=53.8%, Sharpe=-1.2143, PnL=$-7,263.00, MaxDD=$9,197.50
- **MNQ long**: 468 trades, PF=0.856, WR=53.4%, Sharpe=-1.2073, PnL=$-4,520.50, MaxDD=$6,615.50
- **MNQ short**: 433 trades, PF=0.909, WR=53.6%, Sharpe=-0.7802, PnL=$-2,119.50, MaxDD=$2,815.00

## Notes

- Faithful conversion from Pine Script v5
- No parameter optimization applied
- Engine: fill-at-next-open (same as PB baseline)
- Data: Databento CME 5m
