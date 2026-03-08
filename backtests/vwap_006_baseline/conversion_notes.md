# VWAP-RSI Scalper FINAL v1 — Conversion Baseline

**Strategy:** vwap_006
**Family:** vwap
**Source:** https://www.tradingview.com/script/S9hY3huK-VWAP-RSI-Scalper-FINAL-v1/
**Run date:** 2026-03-07 22:18:05
**Conversion type:** Faithful (no optimization)

## Results Summary

- **MES both**: 1023 trades, PF=1.123, WR=38.8%, Sharpe=0.8332, PnL=$3,430.00, MaxDD=$1,647.50
- **MES long**: 572 trades, PF=1.212, WR=40.7%, Sharpe=1.3231, PnL=$2,878.75, MaxDD=$1,245.00
- **MES short**: 441 trades, PF=1.041, WR=37.6%, Sharpe=0.2334, PnL=$592.50, MaxDD=$2,342.50
- **MGC both**: 466 trades, PF=0.966, WR=40.1%, Sharpe=-0.2386, PnL=$-573.00, MaxDD=$2,540.00
- **MGC long**: 259 trades, PF=1.315, WR=44.4%, Sharpe=1.8874, PnL=$2,190.00, MaxDD=$1,723.00
- **MGC short**: 204 trades, PF=0.587, WR=34.8%, Sharpe=-2.1879, PnL=$-4,873.00, MaxDD=$5,380.00
- **MNQ both**: 976 trades, PF=1.088, WR=39.1%, Sharpe=0.6716, PnL=$4,602.00, MaxDD=$3,478.50
- **MNQ long**: 528 trades, PF=1.191, WR=41.7%, Sharpe=1.205, PnL=$4,902.50, MaxDD=$2,259.00
- **MNQ short**: 439 trades, PF=0.984, WR=37.1%, Sharpe=-0.1143, PnL=$-459.00, MaxDD=$2,351.50

## Notes

- Faithful conversion from Pine Script v5
- No parameter optimization applied
- Engine: fill-at-next-open (same as PB baseline)
- Data: Databento CME 5m
