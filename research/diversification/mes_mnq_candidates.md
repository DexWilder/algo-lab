# Diversification Search — MES/MNQ Candidates

*Phase 7 parallel activity: identify non-gold strategies to reduce MGC concentration risk.*

---

## Problem Statement

The deployment portfolio (PB-MGC-Short + ORB-009 MGC-Long) trades only MGC. Despite near-zero daily PnL correlation (r=0.004), the strategies share 62% drawdown overlap because they're both gold-dependent. A non-gold strategy (MES or MNQ) would reduce this structural risk.

## Diversification Requirements

| Requirement | Rationale |
|-------------|-----------|
| Different asset (MES or MNQ) | Break gold-only concentration |
| Low correlation with existing portfolio | Daily PnL r < 0.15 vs MGC strategies |
| Net PF > 1.3 after costs | Must survive transaction cost friction |
| Different entry model preferred | Breakout (ORB-009) + pullback (PB) already covered |
| Survives regime gate | Should work in medium/high vol regimes |

---

## Existing Cross-Asset Data

From conversion round 1, we already have MES/MNQ results for two strategies:

### ORB-009 on MNQ
| Metric | Value |
|--------|-------|
| Mode | Long |
| Trades | 171 |
| PF | 1.237 |
| Sharpe | 1.13 |
| Total PnL | $2,739 |
| MaxDD | $2,339 |
| Win Rate | 53.2% |

**Assessment:** Marginal. PF decent but MaxDD is large relative to PnL. Would need cost analysis — likely survives friction ($1.04/RT for MNQ) but not exciting.

### ORB-009 on MES
| Metric | Value |
|--------|-------|
| Mode | Both |
| Trades | 432 |
| PF | 1.122 |
| Sharpe | 0.68 |
| Total PnL | $2,096 |
| MaxDD | $2,780 |

**Assessment:** Weak. High trade count but low PF. Likely marginal after costs.

### VWAP-006 on MES
Already known to be dead after costs (74% friction impact at 572 trades).

---

## Top Candidates from Triage Queue

### Tier 1: Convert Next (AF=5, strong diversification case)

| # | Strategy | Family | Entry Model | Regime | Complexity | Diversification Value |
|---|----------|--------|-------------|--------|------------|----------------------|
| 1 | RVWAP Mean Reversion | vwap | mean_reversion | range_bound | medium | HIGH — different entry model, different regime |
| 2 | HYE Mean Reversion VWAP | vwap | mean_reversion | range_bound | easy | HIGH — same as above, easy conversion |
| 3 | Open Drive (ORB-002) | orb | breakout | trending | medium | MEDIUM — different session behavior, fills gap |

**RVWAP Mean Reversion** is the top pick:
- Mean reversion entry model (vs breakout/pullback in portfolio)
- Range-bound regime specialist (portfolio strategies do best in medium/high vol)
- Singleton cluster — unique logic, not another ORB variant
- AF=5 (highest automation fitness)
- Run on MES and MNQ to find best asset fit

**HYE Mean Reversion VWAP** is the backup:
- Same thesis (VWAP mean reversion) but different implementation
- Easy conversion (simplest logic in queue)
- Validates whether the VWAP mean reversion cluster has edge

**Open Drive** fills a structural gap:
- No opening drive strategies in the lab
- Measures first-bar conviction — different from range breakout
- Tests whether session structure (open drive vs choppy open) predicts trend days

### Tier 2: Worth Testing (AF=4-5, less clear diversification)

| # | Strategy | Family | Notes |
|---|----------|--------|-------|
| 4 | Liquidity Sweeper (ICT-002) | ict | Volatile regime specialist, but ICT-010 already failed |
| 5 | Gap Momentum (ORB-018) | orb | Gap-based, different from range breakout |
| 6 | Gold ORB (ORB-003) | orb | Gold-specific ORB — doesn't help with diversification |

### Not Recommended

| Strategy | Reason |
|----------|--------|
| GCK VWAP BOT | Gold-specific — doesn't help diversification |
| SMC Strategy (ICT-004) | ICT family already tested and failed (ICT-010) |
| Dynamic Swing VWAP | Low trade frequency, mixed regime — hard to validate |

---

## Research Gaps Relevant to MES/MNQ

The triage pipeline has **zero harvested strategies** in these families:
- **Pure trend following** (MA crossover, momentum)
- **Session-specific** (London/Asia/pre-market)
- **Pure mean reversion** (non-VWAP: Bollinger, RSI extremes, Keltner)

This means:
1. Converting existing queue candidates is the fastest path
2. A targeted harvest for MES/MNQ trend or session strategies would expand the search space
3. The ORB-009 MNQ-Long result (PF=1.237) could be a quick win if it survives friction

---

## Recommended Conversion Order

1. **RVWAP Mean Reversion** → Run on MES, MNQ, MGC
   - If PF > 1.3 on MES or MNQ: proceed to validation
   - If mean reversion thesis works: validates entire VWAP cluster
2. **HYE Mean Reversion VWAP** → Run on MES, MNQ
   - Backup if RVWAP doesn't work
   - Easy conversion — fast to test
3. **Open Drive** → Run on MES, MNQ
   - Fills research gap
   - Different signal type (session structure vs price pattern)
4. **ORB-009 MNQ-Long cost analysis** → Quick check
   - Already have baseline data
   - Just need to apply $1.04/RT friction and regime gate

---

## Success Criteria

A candidate advances to the portfolio if:
- Net PF > 1.3 after transaction costs
- Survives robustness battery (top-trade removal, walk-forward, parameter stability)
- DSR > 0.95 (survives multiple testing correction)
- Daily PnL correlation < 0.15 with existing MGC portfolio
- Reduces portfolio drawdown overlap below 50%

---

## Conversion Results

### Round 1: RVWAP Mean Reversion → REJECTED

Converted and backtested on all three assets. No edge found.

| Asset | Mode | Trades | PF | Sharpe | PnL | MaxDD |
|-------|------|--------|-----|--------|-----|-------|
| MES | Both | 1,004 | 0.83 | -1.83 | -$5,373 | $5,943 |
| MGC | Both | 405 | 1.01 | 0.04 | $117 | $3,252 |
| MNQ | Both | 904 | 0.87 | -1.21 | -$7,263 | $9,198 |

**Verdict:** REJECTED. PF < 1.0 on MES/MNQ, breakeven on MGC. Mean reversion via VWAP stdev bands does not produce an edge on 5m futures data with our engine.

### ORB-009 MNQ-Long Cost Analysis

| Metric | Gross | Net |
|--------|-------|-----|
| PF | 1.237 | 1.201 |
| PnL | $2,739 | $2,356 |
| Friction | — | $383 (14.0%) |

**Verdict:** MARGINAL. Net PF 1.201 < 1.3 threshold. Not recommended for portfolio inclusion without further optimization.

### Open Drive (ORB-002) — Deferred

Strategy requires 30-minute bars (market profile concept). Would need bar aggregation adapter or separate engine config. Deferred to future research.

### Round 2: Gap Momentum (ORB-018) — MIXED

| Asset | Mode | Trades | PF | Sharpe | PnL | MaxDD |
|-------|------|--------|-----|--------|-----|-------|
| MES | Long | 27 | 0.24 | -9.87 | -$984 | $1,160 |
| MGC | Long | 24 | 3.41 | 3.67 | $2,718 | $518 |
| MNQ | Long | 28 | 0.48 | -4.71 | -$1,412 | $1,905 |

**MGC-Long cost analysis:** Net PF=3.26, friction only 2.9%. Perfectly uncorrelated with existing portfolio (r=-0.01, zero trade date overlap with PB-Short).

**CRITICAL WARNING:** Best trade = $2,332 (86% of total PnL). Top-trade removal would likely collapse PF. Only 24 trades — bootstrap CI will be wide.

**Verdict for diversification:** FAILS. No edge on MES or MNQ. MGC result is strong but adds another gold strategy, not diversification. Could be a portfolio enhancement candidate (3rd gold strategy with independent alpha) after robustness validation.

### Remaining Queue

| # | Candidate | Status |
|---|-----------|--------|
| ~~1~~ | ~~RVWAP Mean Reversion~~ | REJECTED (no edge) |
| ~~2~~ | ~~Gap Momentum~~ | FAILS diversification (no MES/MNQ edge) |
| ~~3~~ | ~~Open Drive~~ | DEFERRED (needs 30m bars) |
| 4 | HYE Mean Reversion VWAP | Low priority (VWAP MR thesis likely dead) |
| 5 | **New harvest needed** | MES/MNQ trend, session, volatility compression |

### Key Insights

1. **The lab's edge is concentrated in gold.** All strategies that show PF > 1.5 trade MGC. Index futures (MES/MNQ) consistently show marginal or no edge.
2. **VWAP mean reversion doesn't work** on 5m futures after realistic fills.
3. **Gap momentum works on gold** but not on indices — gold has unique overnight gap dynamics.
4. **Diversification requires new harvest.** The existing triage queue is dominated by VWAP and ORB variants. Need to harvest: pure trend following, volatility compression breakout, and session-specific strategies designed for MES/MNQ.
5. **Gold portfolio enhancement is possible:** Gap Momentum could become a 3rd gold strategy if it passes robustness. But this doesn't reduce gold concentration risk.

---
*Report generated 2026-03-08 | Updated 2026-03-08 with conversion results*
