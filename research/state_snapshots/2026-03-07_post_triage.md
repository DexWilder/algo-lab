# Algo Lab State Snapshot — 2026-03-07 (Post-Triage)

## Harvest Totals
- **Total harvested scripts:** 54
- **Families:** VWAP (23), ORB (18), ICT (13)
- **With Pine source code:** 23

## Strategy Families in Lab
| Family | Status | Strategies | Notes |
|--------|--------|-----------|-------|
| PB (Pullback) | VALIDATED | pb_trend, lucid-100k | MGC-Short primary, MNQ-Long/MES-Short secondary |
| VWAP | IN PROGRESS | vwap_rev, vwap_006 | vwap_006 converted round 1 |
| ORB | IN PROGRESS | orb_009 | Converted round 1, MGC-Long standout |
| ICT | TESTED | ict_010 | Converted round 1, no edge found |
| Mean Reversion | GAP | — | Not yet harvested (non-VWAP) |
| Trend | GAP | — | Only sma-crossover exists |
| Session | GAP | — | No London/Asia strategies |
| Opening Drive | GAP | — | ORB-002 partially covers |

## Validated Strategies
- **pb_trend** (MGC-Short): PF=2.71, Sharpe=3.88 — candidate validated with robustness tests
- **pb_trend** (MNQ-Long): PF=1.72, Sharpe=1.85
- **pb_trend** (MES-Short): PF=1.34, Sharpe=0.62

## Experimental Strategies (Conversion Round 1)
- **orb_009** (MGC-Long): PF=1.99, Sharpe=3.63, r<0.02 vs PB — **strong diversification candidate**
- **orb_009** (MNQ-Long): PF=1.24, Sharpe=1.13
- **vwap_006** (MES-Long): PF=1.21, Sharpe=1.32 — long-only edge
- **vwap_006** (MNQ-Long): PF=1.19, Sharpe=1.21
- **ict_010**: No edge (PF<1 all combos) — session sweep model doesn't work on this data

## Current Conversion Candidates (from Triage)
1. **RVWAP Mean Reversion** (vwap) — AF=5, easy conversion, range-bound specialist
2. **HYE Mean Reversion VWAP** (vwap) — AF=5, representative of 20-member cluster
3. **Liquidity Sweeper** (ict) — AF=5, volatile regime specialist
4. **Gold ORB Strategy** (orb) — AF=5, gold-specific 15-min ORB
5. **Dynamic Swing AVWAP** (vwap) — AF=4, unique pivot-anchored VWAP approach
6. **GCK VWAP BOT** (vwap) — AF=4, confidence scoring system
7. **SMC Strategy** (ict) — AF=4, discount/premium zones
8. **Gap Momentum System** (orb) — AF=4, academic TASC source

## Triage Summary
- **Convert now:** 8 (cluster representatives, AF >= 4)
- **Hold for later:** 39 (non-representative, might promote later)
- **Component only:** 3 (useful parts to extract)
- **Already converted:** 3 (ORB-009, VWAP-006, ICT-010)
- **Reject:** 1 (ICT-006, AF=2, no SL/TP)
- **Clusters:** 8 total

## Component Catalog
- **Entries:** 17 cataloged
- **Exits:** 10 cataloged
- **Filters:** 11 cataloged
- **Risk models:** 6 cataloged
- **Session models:** 4 cataloged

## Next Research Goals
1. **Convert top 3 from triage** — RVWAP, Liquidity Sweeper, Gold ORB (diverse families)
2. **Correlation analysis round 2** — test independence of new converts vs PB + ORB-009
3. **Harvest new families** — pure mean reversion, trend following, London/Asia session
4. **Portfolio construction** — combine independent edges into master stack
5. **Robustness testing** — walk-forward on orb_009 MGC-Long (promising candidate)

## Infrastructure
- **Backtest engine:** engine/backtest.py (fill-at-next-open)
- **Baseline runner:** backtests/run_conversion_baseline.py (generic, any strategy)
- **Data:** Databento CME 5m — MES (141K bars, 630 days), MNQ (141K), MGC (77K)
- **Triage:** research/triage/run_triage.py (re-runnable as manifest grows)

---
*Snapshot generated 2026-03-07 post-triage*
