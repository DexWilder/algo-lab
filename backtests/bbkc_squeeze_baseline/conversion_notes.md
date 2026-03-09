# BB/KC Squeeze Momentum — Conversion Baseline

**Strategy:** bbkc_squeeze
**Family:** breakout
**Source:** https://www.tradingview.com/script/x9r2dOhI-Trading-Strategy-based-on-BB-KC-squeeze/
**Run date:** 2026-03-09 05:43:40
**Conversion type:** Faithful (no optimization)

## Results Summary

- **MES both**: 1295 trades, PF=1.485, WR=41.9%, Sharpe=2.868, PnL=$9,606.25, MaxDD=$1,002.50
- **MES long**: 687 trades, PF=1.492, WR=43.4%, Sharpe=2.0923, PnL=$4,642.50, MaxDD=$880.00
- **MES short**: 608 trades, PF=1.479, WR=40.1%, Sharpe=2.3543, PnL=$4,963.75, MaxDD=$890.00
- **MGC both**: 692 trades, PF=0.991, WR=39.2%, Sharpe=-0.034, PnL=$-119.00, MaxDD=$2,819.00
- **MGC long**: 377 trades, PF=0.815, WR=43.5%, Sharpe=-1.1047, PnL=$-1,294.00, MaxDD=$1,800.00
- **MGC short**: 315 trades, PF=1.182, WR=34.0%, Sharpe=0.4442, PnL=$1,175.00, MaxDD=$1,571.00
- **MNQ both**: 1291 trades, PF=1.214, WR=41.0%, Sharpe=1.6824, PnL=$8,892.50, MaxDD=$2,082.00
- **MNQ long**: 684 trades, PF=1.231, WR=43.7%, Sharpe=1.4611, PnL=$4,567.50, MaxDD=$1,134.50
- **MNQ short**: 607 trades, PF=1.192, WR=38.1%, Sharpe=1.121, PnL=$4,232.50, MaxDD=$1,887.00

## Notes

- Faithful conversion from Pine Script v5
- No parameter optimization applied
- Engine: fill-at-next-open (same as PB baseline)
- Data: Databento CME 5m
