# Research Gap Map

*Regime-aware research roadmap. Future harvesting prioritizes filling regime gaps, not just adding strategies.*

---

## Regime Coverage Matrix

The lab's primary research tool. Shows which market regimes have strategy coverage and which are exposed.

| Regime | Strategy | PF in Regime | Coverage |
|--------|----------|-------------|----------|
| LOW_VOL | VIX Channel MES | 1.79 | COVERED |
| NORMAL (vol) | PB-Short, ORB-009 | 2.36, 2.05 | COVERED |
| HIGH_VOL | ORB-009 | 2.18 | COVERED |
| TRENDING | ORB-009, PB-Short | 2.06, 2.05 | COVERED |
| RANGING | VIX Channel MES | 1.64 | COVERED (thin) |
| LOW_RV | ORB-009 | 2.79 | COVERED |
| NORMAL_RV | VIX Channel MES | 1.39 | COVERED (thin) |
| HIGH_RV | PB-Short | 4.99 | COVERED |
| EXTREME_VOL (spikes) | ??? | — | **MISSING** |
| RANGE_BOUND (multi-day) | ??? | — | **MISSING** |
| OVERNIGHT / GLOBEX | ??? | — | **MISSING** |
| SESSION_TRANSITION | ??? | — | **MISSING** |

### Coverage Notes
- **LOW_VOL + RANGING** = 15 days (2.4% of data). Very thin coverage — VIX Channel is the only active strategy.
- **RANGING overall** covered only by VIX Channel (PF=1.64). No dedicated mean reversion strategy survives here.
- **HIGH_RV** covered only by PB-Short (11 trades, PF=4.99). Strong but low sample.
- **Extreme volatility** (macro days, CPI/FOMC) has no dedicated strategy. Existing strategies may be active but not optimized for spikes.

## Current Family Coverage

| Family | Strategies Converted | Best Result | Status |
|--------|---------------------|-------------|--------|
| PB (Pullback) | 1 (PB-Trend) | MGC-Short PF=2.36 | deployment_ready |
| ORB (Opening Range Breakout) | 2 (ORB-009, Gap-Mom) | MGC-Long PF=2.07 | deployment_ready |
| Session (Trend Following) | 1 (VIX Channel) | MES-Both PF=1.30 | pending_validation |
| VWAP (VWAP-based) | 2 (VWAP-006, RVWAP-MR) | No edge | rejected |
| ICT (Smart Money) | 1 (ICT-010) | No edge | rejected |
| Vol Compression | 2 (ORION, BB/KC Squeeze) | Marginal after costs | rejected |

## Regime-Prioritized Harvest Targets

**Priority is now determined by regime gap severity, not family novelty.**

### Tier 1 — Fill regime gaps with zero coverage

1. **EXTREME_VOL specialist** (macro event days)
   - *Target regime:* Extreme volatility spikes (CPI, FOMC, NFP)
   - *Why:* No strategy optimized for 3+ sigma moves. Existing strategies are active but may underperform vs a dedicated approach.
   - *Harvest targets:* Range expansion breakout, news straddle, volatility crush plays
   - *Expected PF:* Even 1.2-1.3 would add value as a regime filler

2. **RANGE_BOUND mean reversion** (multi-day consolidation)
   - *Target regime:* RANGING + LOW_VOL (currently only 2.4% of days)
   - *Why:* VIX Channel covers RANGING but is trend-following, not mean-reverting. A true reversion strategy would be complementary.
   - *Harvest targets:* Bollinger band fade, market profile value area reversion, RSI extreme fade
   - *Conversion note:* Previous VWAP/band reversions failed on 5m. Try 15m or 30m timeframes, or session-anchored mean reversion.

3. **OVERNIGHT / SESSION_TRANSITION**
   - *Target regime:* Pre-market, Asia→Europe, Europe→US transitions
   - *Why:* Entirely untapped. All current strategies are RTH 09:30-15:45 only.
   - *Harvest targets:* London breakout, Asia range breakout, overnight gap strategies
   - *Regime benefit:* These operate in a completely different microstructure — near-zero correlation expected.

### Tier 2 — Strengthen thin coverage

4. **RANGING strengthener** (dedicated to ranging markets)
   - *Target regime:* RANGING (21.1% of days, covered only by VIX Channel at PF=1.64)
   - *Why:* VIX Channel's RANGING edge is its secondary strength, not primary. A dedicated ranging strategy would provide redundancy.
   - *Harvest targets:* Keltner channel fade, stochastic mean reversion, choppy market scalpers

5. **Trend following** (non-pullback, non-ORB)
   - *Target regime:* TRENDING (78.9% of days)
   - *Why:* TRENDING is well-covered by ORB-009 and PB-Short, but both are gold-focused. A TRENDING strategy on MES/MNQ would diversify asset exposure.
   - *Harvest targets:* EMA crossover, SuperTrend, Donchian channel
   - *Intake candidates:* 4 trend scripts in pipeline, none converted

### Tier 3 — Asset diversification within covered regimes

6. **MES/MNQ versions of PB or ORB**
   - *Why:* Both core strategies trade MGC. Adding index versions reduces gold concentration risk.
   - *Note:* Previous attempts (PB-MNQ-Long, ORB-MNQ-Long) had marginal edge. May need different parameter sets.

7. **Alternative micros** (M2K, MYM, M6E)
   - *Why:* Different correlation structure than gold/index futures.
   - *Risk:* Lower liquidity, wider spreads on micros.

## Relationship to Intake Pipeline

| Regime Gap | Intake Scripts Available | Status |
|-----------|------------------------|--------|
| EXTREME_VOL | 5 (breakout cluster) | 2 converted, both rejected — retry with regime focus |
| RANGE_BOUND | 20 (VWAP cluster) | 2 converted, both rejected — retry on higher timeframe |
| OVERNIGHT | 0 | **Harvest needed** |
| RANGING | 4 (session cluster) | 1 converted (VIX Channel — partial coverage) |
| TRENDING (MES/MNQ) | 4 (trend cluster) | None converted |

**Recommendation:** Harvest overnight/session-transition strategies first (zero intake candidates, zero coverage). Then retry mean reversion on 15m/30m timeframes.

---

## Research Philosophy (Post Phase 8)

> A mediocre standalone strategy (PF ~1.3) can be a portfolio powerhouse if it trades in regimes where the core strategies are idle.

Future strategy evaluation should include:
1. **Standalone PF** (minimum 1.0 after costs)
2. **Regime coverage** — does it fill a gap in the coverage matrix?
3. **Portfolio correlation** — is it uncorrelated with existing strategies?
4. **Regime efficiency** — does it concentrate edge in underserved regimes?

A strategy with PF 1.3 that fills an empty regime cell may be more valuable than a strategy with PF 1.8 that duplicates existing TRENDING coverage.

---
*Updated 2026-03-09 with regime coverage analysis (Phase 8).*
