# Strategy Registry

*Canonical status tracker for every strategy in the lab. Updated after each phase.*

---

## Parent Strategies (Validated + Deployed)

| Strategy | Asset | Mode | PF | Sharpe | Trades | Engine Type | Promoted |
|----------|-------|------|----|--------|--------|-------------|----------|
| PB-Trend | MGC | Short | 2.36 | 5.27 | 28 | pullback_scalper | Phase 6 |
| ORB-009 | MGC | Long | 2.07 | 3.93 | 106 | trend_continuation | Phase 6 |
| VWAP Trend | MNQ | Long | 1.67 | 2.62 | 195 | breakout/continuation | Phase 11 |
| XB-PB-EMA-TimeStop | MES | Short | 1.82 | 3.56 | 123 | pullback_scalper | Phase 12 |

**Key traits:**
- PB: 3-bar median hold, HIGH_RV specialist, morning session, MGC
- ORB: 28-bar median hold, TRENDING specialist, opening range breakout, MGC
- VWAP Trend: 14-bar median hold, TRENDING specialist, pullback to VWAP, MNQ
- XB-PB-EMA-TimeStop: 10-bar median hold, HIGH_VOL_TRENDING specialist, MES
- All pairwise correlations near-zero (r < 0.2)
- **4 parents across 3 assets (MES, MNQ, MGC) — full asset coverage achieved**

---

## Probation (Edge likely real, needs more data or refinement)

| Strategy | Asset | Mode | PF | Sharpe | Trades | Blocker | Path to Promotion |
|----------|-------|------|----|--------|--------|---------|-------------------|
| Donchian GRINDING+PL | MNQ | Long | 1.99 | 3.97 | 48 | Sample size | Wait for more data (Q3 2026) |
| BB Equilibrium (Trend-Aware) | MGC | Long | 3.22 | 3.13 | 60 | Gold-only, WF marginal | Re-validate with more data |
| XB-ORB-EMA-Ladder | MNQ | Short | 1.92 | 3.80 | 117 | MC ruin at $2K (MNQ sizing) | Position sizing work, re-validate |
| Session VWAP Fade | MGC | Long | 2.13 | 2.59 | 104 | Gold-only, needs refinement | Phase 14 Gold MR refinement |

**Donchian notes:**
- True trend-follower DNA (61-bar median hold)
- GRINDING persistence filter concentrates edge
- Profit Ladder exit eliminates drawdown
- 99% parameter stability, 0% ruin — edge is real, just thin data
- Stability score: 7.0/10 (3 failures all sample-driven)

**Session VWAP Fade notes:**
- Gold-specific mean reversion (MES/MNQ fail uniformly)
- Fades morning overextension from VWAP (10:00-12:30 window, 2.0 ATR deviation)
- Session-extreme stops + VWAP target — clean risk model
- 11-bar median hold — confirmed MR DNA
- Near-zero correlation vs all 5 parents (max |r| = 0.042)
- Portfolio impact: Sharpe +0.03, Calmar +3.36, MaxDD -$100
- RANGING_EDGE_SCORE = 0.18 (moderate range specialist)
- Phase 13 discovery, Phase 14 refinement target

**BB Equilibrium notes:**
- Gold-specific mean reversion (PF < 0.65 on equity indexes)
- Trend-Aware EMA(20) filter solves walk-forward: 2024 PF 0.88→1.00
- 100% parameter stability, bootstrap/DSR/MC all pass
- Stability score: 7.0/10 (3 failures: gold-only asset, thin sample)
- Portfolio correlation: r=0.084 vs PB, r=0.175 vs ORB (excellent diversifier)

**XB-ORB-EMA-Ladder notes:**
- Phase 12 crossbred child (ORB entry + EMA slope filter + Profit Ladder exit)
- **Multi-asset: PF>1.5 on all 3 assets, PF>1.8 on all 3 timeframes**
- 59-bar median hold — trend-follower DNA, different from ORB-009 (28-bar)
- 100% parameter stability (27/27), perfect walk-forward (3/3)
- Only failure: MC ruin P($2K)=59.6% — MNQ position sizing, not edge quality
- Stability score: 9.0/10

---

## Rejected (No edge or structurally redundant)

| Strategy | Asset | Reason | Phase |
|----------|-------|--------|-------|
| ICT-010 | All | No edge (PF < 1.0 everywhere) | Phase 3 |
| VWAP-006 | MES | 74% PnL eaten by friction | Phase 3 |
| RVWAP-MR | All | No edge on 5m bars | Phase 3 |
| Gap-Mom | MES/MNQ | No edge on index futures | Phase 5 |
| ORION Vol | All | Marginal after costs | Phase 5 |
| BB/KC Squeeze | MES | 50% friction impact (1,295 trades) | Phase 5 |
| EMA Trend Rider | MNQ | r=0.449 vs PB — structural overlap | Phase 11 |
| BB Compression Gold | MGC | r=0.624 vs PB — structural overlap, PF=1.09 | Phase 11.7 |
| VWAP MR Gold | MGC | Weak edge (PF=1.27), outclassed by BB Eq | Phase 11.7 |
| Session Reversion Gold | MGC | Fragile (97 trades, PnL from 4 trades) | Phase 11.7 |
| XB-PB-Squeeze-Chand | MGC | r=0.462 vs ORB — structural overlap | Phase 12 |
| ORB Fade | All | Too few trades (max 60), negative edge on MES/MNQ | Phase 13 |

---

## Crossbreeding Descendants (BB Eq Refinement Lane)

| Recipe | Combo | PF | Sharpe | Trades | Exit | Status |
|--------|-------|----|--------|--------|------|--------|
| #11 BB + morning + midline | MGC-long | 3.49 | 4.67 | 61 | midline | Refinement candidate |
| #7 BB + EMA slope + midline | MGC-long | 3.15 | 4.11 | 63 | midline | Refinement candidate |
| #9 BB + squeeze + ATR trail | MGC-long | 2.97 | 3.18 | 85 | ATR trail | Refinement candidate |
| #18 BB + no filter + profit ladder | MGC-long | 2.67 | 3.07 | 92 | profit ladder | Refinement candidate |
| #19 BB + morning + profit ladder | MGC-long | 2.14 | 2.56 | 61 | profit ladder | Refinement candidate |

These are BB Equilibrium variants with different exit/filter combinations — high correlation vs BB Eq parent expected. Treat as exit evolution candidates, not new parent strategies.

---

## Pending Validation

| Strategy | Asset | Mode | Raw PF | Notes |
|----------|-------|------|--------|-------|
| VIX Channel | MES | Both | 1.30 | Passes 5/8 criteria, fails net PF, DSR, MC ruin |
| Gap-Mom | MGC | Long | — | Insufficient data |

---

## Watch List (Interesting but insufficient data)

| Strategy | Evidence | Next Step |
|----------|----------|-----------|
| orb_range_fade | PF=4.83 on 9 trades | Re-evaluate with more data |
| vix_ema_trend | PF=1.48, DNA duplicate | Reassess if VIX DNA threshold relaxed |
| VWAP Dev MR | MGC-long PF=1.31, RES=0.53 (purest range specialist) | Phase 14 refinement |
| BB Range MR | MGC-long PF=3.05, only 40 trades | Phase 14 refinement |

---

## Portfolio Genome Summary

| Strategy | Engine Type | Median Hold | Trend Sens. | Vol Sens. | Asset |
|----------|-------------|-------------|-------------|-----------|-------|
| PB-Trend | pullback_scalper | 3b | +0.457 | +1.000 | MGC |
| ORB-009 | trend_continuation | 28b | +1.000 | +0.709 | MGC |
| VWAP Trend | breakout | 14b | +1.000 | -0.038 | MNQ |
| XB-PB-EMA-TimeStop | pullback_scalper | 10b | — | — | MES |
| Donchian | trend_follower | 61b | +0.944 | -0.664 | MNQ |
| BB Equilibrium | mean_reversion | 11b | +1.000 | +0.947 | MGC |
| XB-ORB-EMA-Ladder | trend_follower | 59b | — | — | MNQ |
| Session VWAP Fade | mean_reversion | 11b | — | — | MGC |

**Portfolio diversification score: ~7.5/10** (up from 6.2 — MES gap filled)

**Two-Engine Architecture:**
- **Trend Engine Family** (indexes): PB, ORB, VWAP Trend, XB-PB-EMA, Donchian
- **Mean Reversion Engine Family** (gold): Session VWAP Fade, BB Equilibrium, VWAP Dev MR, BB Range MR

**Missing engine types:** counter_trend, session_structure, volatility_compression, overnight_gap

---

*Last updated: 2026-03-10 (Phase 12 — Crossbreeding engine, XB-PB-EMA-TimeStop promoted)*
