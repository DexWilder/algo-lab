# ORION Hybrid Volatility Breakout — Conversion Baseline

**Strategy:** orion_vol
**Family:** breakout
**Source:** https://www.tradingview.com/script/6xLkMWMC-ORION-Hybrid-Volatility-Breakout-Strategy/
**Run date:** 2026-03-09 05:43:53
**Conversion type:** Faithful (no optimization)

## Results Summary

- **MES both**: 400 trades, PF=0.94, WR=42.8%, Sharpe=-0.3543, PnL=$-1,336.25, MaxDD=$3,271.25
- **MES long**: 240 trades, PF=0.83, WR=43.3%, Sharpe=-1.0766, PnL=$-2,170.00, MaxDD=$2,637.50
- **MES short**: 160 trades, PF=1.088, WR=41.9%, Sharpe=0.4827, PnL=$833.75, MaxDD=$2,250.00
- **MGC both**: 187 trades, PF=1.209, WR=48.1%, Sharpe=1.0344, PnL=$2,071.00, MaxDD=$1,244.00
- **MGC long**: 114 trades, PF=1.458, WR=50.9%, Sharpe=2.0309, PnL=$2,471.00, MaxDD=$944.00
- **MGC short**: 73 trades, PF=0.911, WR=43.8%, Sharpe=-0.5098, PnL=$-400.00, MaxDD=$1,545.00
- **MNQ both**: 394 trades, PF=1.006, WR=44.4%, Sharpe=0.0338, PnL=$239.50, MaxDD=$4,201.50
- **MNQ long**: 226 trades, PF=0.935, WR=46.0%, Sharpe=-0.4063, PnL=$-1,435.00, MaxDD=$3,313.50
- **MNQ short**: 168 trades, PF=1.083, WR=42.3%, Sharpe=0.481, PnL=$1,674.50, MaxDD=$3,693.00

## Notes

- Faithful conversion from Pine Script v5
- No parameter optimization applied
- Engine: fill-at-next-open (same as PB baseline)
- Data: Databento CME 5m
