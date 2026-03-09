# NY VIX Channel Trend — Conversion Baseline

**Strategy:** vix_channel
**Family:** session
**Source:** https://www.tradingview.com/script/TlOcVraF-NY-VIX-Channel-Trend-US-Futures-Day-Trade-Strategy/
**Run date:** 2026-03-09 05:44:03
**Conversion type:** Faithful (no optimization)

## Results Summary

- **MES both**: 503 trades, PF=1.394, WR=52.7%, Sharpe=2.0366, PnL=$8,870.00, MaxDD=$1,418.75
- **MES long**: 263 trades, PF=1.331, WR=52.5%, Sharpe=1.7447, PnL=$4,040.00, MaxDD=$1,313.75
- **MES short**: 240 trades, PF=1.469, WR=52.9%, Sharpe=2.364, PnL=$4,830.00, MaxDD=$1,385.00
- **MGC both**: 362 trades, PF=0.961, WR=45.6%, Sharpe=-0.23, PnL=$-1,026.00, MaxDD=$3,749.00
- **MGC long**: 182 trades, PF=1.181, WR=49.5%, Sharpe=0.9551, PnL=$1,963.00, MaxDD=$1,569.00
- **MGC short**: 180 trades, PF=0.805, WR=41.7%, Sharpe=-1.2033, PnL=$-2,989.00, MaxDD=$4,843.00
- **MNQ both**: 506 trades, PF=1.321, WR=54.7%, Sharpe=1.7724, PnL=$13,655.50, MaxDD=$3,824.50
- **MNQ long**: 263 trades, PF=1.315, WR=57.8%, Sharpe=1.7526, PnL=$6,989.50, MaxDD=$2,286.50
- **MNQ short**: 243 trades, PF=1.327, WR=51.4%, Sharpe=1.7919, PnL=$6,666.00, MaxDD=$3,532.50

## Notes

- Faithful conversion from Pine Script v5
- No parameter optimization applied
- Engine: fill-at-next-open (same as PB baseline)
- Data: Databento CME 5m
