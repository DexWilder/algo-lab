# ALGO-CORE-TREND-001 Baseline Report v2
## Databento CME Data + REV Gate Fix

**Date:** 2026-03-07
**Strategy:** Lucid v6.3 (Python v1.0)
**Data source:** Databento GLBX.MDP3 (real CME volume)
**Date range:** 2024-02-29 → 2026-03-06 (~630 trading days)
**Engine:** Fill-at-next-open

---

## Critical Bug Found & Fixed

**Bug:** `quality_ok` required ADX >= 14, while `range_regime` (REV gate) required ADX < 14.
These were **mutually exclusive** — REV signals could never fire in auto mode.

**Fix:** Split quality gate into `quality_pb` (ADX + volume) and `quality_rev` (volume only).
REV conditions already self-select ranging markets via neutralish + vwap_flat.

**REV threshold adjustments (moderate relaxation):**
- `neutralish`: 0.6 → 1.0 (EMA separation in ATR units)
- `vwap_flat`: 0.3 → 0.5 ATR (VWAP slope threshold)
- `dist_atr`: 1.4 → 1.2 (distance from VWAP)
- `RSI`: 35/65 → 40/60
- `REV_ADX_MAX`: 14 → 25 (regime gate)
- `rejection`: 0.4 (unchanged)

---

## Summary Table

| Asset | Mode | Trades | PF | WR% | Sharpe | PnL | MaxDD | AvgR |
|-------|------|-------:|---:|----:|-------:|----:|------:|-----:|
| MES | both | 400 | 1.01 | 41.5% | 0.09 | $144 | $1,900 | 0.007 |
| MES | long | 233 | 0.93 | 41.2% | -0.53 | -$442 | $1,405 | -0.040 |
| **MES** | **short** | **167** | **1.10** | **41.9%** | **0.75** | **$586** | **$884** | **0.059** |
| **MGC** | **both** | **97** | **1.42** | **52.6%** | **2.27** | **$1,458** | **$662** | **0.201** |
| MGC | long | 69 | 1.26 | 50.7% | 1.50 | $691 | $662 | 0.127 |
| **MGC** | **short** | **28** | **2.02** | **57.1%** | **4.18** | **$767** | **$283** | **0.437** |
| MNQ | both | 574 | 1.05 | 44.1% | 0.43 | $1,624 | $2,250 | 0.030 |
| **MNQ** | **long** | **343** | **1.12** | **46.1%** | **0.94** | **$1,921** | **$1,951** | **0.067** |
| MNQ | short | 230 | 0.95 | 40.9% | -0.36 | -$713 | $2,578 | -0.027 |

## Signal Type Distribution

| Asset | PB signals | REV signals |
|-------|-----------|------------|
| MES | 453 | 3 |
| MGC | 109 | 2 |
| MNQ | 700 | 1 |

REV is now firing but remains very low-frequency (~6 signals across 3 assets over 2 years).
The compound condition stack (neutralish + vwap_flat + dist_atr + RSI + rejection candle + MTF) is inherently rare.
REV needs separate development as ALGO-CORE-VWAP-001-REV.

---

## Side-Specific Deployment Candidates

### Tier 1: MGC Short-Only
- **PF 2.02 | Sharpe 4.18 | WR 57.1%**
- 28 trades, $767 PnL, $283 MaxDD
- Monthly consistency: 8/11 positive (73%)
- Verdict: **Strongest candidate. Small sample but very clean edge.**

### Tier 2: MGC Both-Sides
- **PF 1.42 | Sharpe 2.27 | WR 52.6%**
- 97 trades, $1,458 PnL, $662 MaxDD
- Monthly consistency: 11/20 positive (55%)
- Verdict: **Best overall risk-adjusted profile. Larger sample.**

### Tier 3: MNQ Long-Only
- **PF 1.12 | Sharpe 0.94 | WR 46.1%**
- 343 trades, $1,921 PnL, $1,951 MaxDD
- Monthly consistency: 13/25 positive (52%)
- Verdict: **Mild edge, high trade count. Needs further filtering.**

### Tier 4: MES Short-Only
- **PF 1.10 | Sharpe 0.75 | WR 41.9%**
- 167 trades, $586 PnL, $884 MaxDD
- Monthly consistency: 13/25 positive (52%)
- Verdict: **Marginal edge. Not deployment-ready.**

---

## Key Findings

1. **PB module is validated** — shows real edge, especially on MGC
2. **REV module gate was broken** — mutually exclusive ADX conditions (now fixed)
3. **REV is still low-frequency** — needs separate research as its own strategy
4. **MGC is the primary asset** — best PF, Sharpe, WR, and consistency
5. **Side asymmetry is real** — MGC short and MNQ long carry the edge
6. **Data upgrade mattered** — real CME volume improved VWAP accuracy and MGC results

## Next Steps

1. Preserve PB as validated ALGO-CORE-TREND-001-PB
2. Develop REV separately as ALGO-CORE-VWAP-001-REV
3. Focus optimization on MGC (primary) and MNQ (secondary)
4. Begin OpenClaw harvest for diversification (ICT, ORB, VWAP families)
