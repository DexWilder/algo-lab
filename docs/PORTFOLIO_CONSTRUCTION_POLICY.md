# FQL Portfolio Construction Policy

*How validated strategies fit together at the portfolio level.*
*Effective: 2026-03-18*

---

## Mission Alignment

FQL is a prop-first portfolio. The goal is compounding real capital on
futures with uncorrelated, mechanically-defined edges. Portfolio
construction serves this by maximizing the number of independent bets
while controlling concentration risk. Every rule below exists to prevent
the portfolio from silently collapsing into a single bet disguised as
many strategies.

---

## 1. Factor Concentration Limits

| Rule | Threshold | Action |
|------|-----------|--------|
| Single factor > 40% of weighted active exposure | **HARD CAP** | No new strategies in that factor until another factor grows |
| Single factor > 50% (current MOMENTUM state) | **REDUCE** | Actively seek alternatives; apply high-bar rule to new entrants |
| Factor with 0 active or probation strategies | **GAP** | Prioritize in harvest targeting |
| Factor with 5+ active strategies | **OVERCROWDED** | No new entrants unless clearly superior to weakest existing |

### Current Factor State (2026-03-18)

| Factor | Core | Probation | Total Active | % of Active | Status |
|--------|------|-----------|-------------|-------------|--------|
| MOMENTUM | 5 | 6 | 11 | ~61% | **OVER HARD CAP — high-bar only** |
| MEAN_REVERSION | 1 | 2 | 3 | ~17% | Adequate |
| VOLATILITY | 0 | 3 | 3 | ~17% | Adequate but no core |
| EVENT | 0 | 2 | 2 | ~11% | Growing, needs core promotion |
| CARRY | 0 | 0 | 0 | 0% | **GAP — highest harvest priority** |
| STRUCTURAL | 0 | 1 | 1 | ~6% | **THIN — harvest priority** |

### Factor Weighting Method

- Primary factor = 1.0 weight
- Secondary factor = 0.5 weight
- A strategy with primary=MOMENTUM, secondary=CARRY contributes 1.0 to
  MOMENTUM and 0.5 to CARRY

### Momentum High-Bar Rule

New momentum strategies are accepted ONLY if they meet at least one of:
- Operate on a horizon not covered by existing momentum
- Target an asset class with no momentum coverage
- Show superior evidence over existing momentum sleeves
- Use a fundamentally different entry mechanism
- Fill a specific session/time gap (afternoon, close, overnight)

---

## 2. Asset Concentration Limits

| Rule | Threshold | Action |
|------|-----------|--------|
| Single asset ≥ 5 active strategies | **HARD CAP** | No new strategies on that asset |
| Single asset = 4 active strategies | **HIGH** | New entrants must be in a different session or factor |
| Single asset class ≥ 50% of active strategies | **REBALANCE** | Prioritize other asset classes |
| Asset with 0 active strategies | **GAP** | Flag in harvest targeting |

### Current Asset State

| Asset | Active Strategies | Cap Status |
|-------|-------------------|------------|
| MNQ | 4 (+ 1 event) | **HIGH** — next entrant needs different session/factor |
| MGC | 4 | **HIGH** — same constraint |
| M2K | 4 | **HIGH** — same constraint |
| MES | 1 | Room for 3 more |
| 6J | 2 | Room for 2 more |
| MCL | 2 | Room for 2 more |
| 6E | 1 (testing) | Room |
| Rates (ZN/ZF/ZB) | 0 | **GAP** |
| 6B | 0 | **GAP** |

### Asset Class Distribution Target

| Asset Class | Target Range | Current | Status |
|-------------|-------------|---------|--------|
| Equity Index (MES/MNQ/M2K) | 30-50% | ~55% | Slightly over |
| Metal (MGC) | 15-25% | ~22% | On target |
| Energy (MCL) | 10-20% | ~11% | On target |
| FX (6J/6E/6B) | 10-25% | ~11% | Room to grow |
| Rates (ZN/ZF/ZB) | 5-15% | 0% | **GAP** |

---

## 3. Session and Time-of-Day Concentration Limits

| Rule | Threshold | Action |
|------|-----------|--------|
| Single session ≥ 6 active strategies | **HARD CAP** | No new strategies in that session |
| Morning session (09:30-11:30 ET) ≥ 50% of active | **REBALANCE** | Prioritize afternoon/close/overnight |
| Session with 0 active strategies | **GAP** | Flag in harvest targeting |
| 3+ strategies generating signals in the same 30-min window | **CROWDED** | Review for correlation; consider staggering |

### Current Session State

| Session | Active Strategies | Status |
|---------|-------------------|--------|
| Morning (09:30-11:30 ET) | ~8 | **AT CAP — no new morning strategies** |
| Midday (11:30-14:00 ET) | 1 | Room |
| Afternoon (14:00-15:30 ET) | 0 | **GAP** |
| Close (15:30-16:00 ET) | 1 | Room |
| All-day | 5 | Acceptable (distributed across hours) |
| London (03:00-08:00 ET) | 1 | Room |
| Tokyo | 0 | **GAP** |
| Overnight | 1 (event only) | Room |
| Daily close (rebalance) | 1 | Room |
| Event windows | 2 | Room |

### Time Overlap Rule

When 3+ strategies trade the same asset in the same 30-minute window,
run a correlation check on their daily PnL. If correlation > 0.35,
they are effectively one bet. Either:
- Remove the weakest (lowest standalone Sharpe)
- Stagger entry times if the mechanisms are genuinely independent
- Accept the overlap if factor diversity justifies it (e.g., one is
  momentum, another is mean-reversion)

---

## 4. Portfolio Role Labels

Every active strategy should be tagged with its portfolio role. This
determines how it contributes to the whole and what happens when the
portfolio needs rebalancing.

| Role | Description | Expected Behavior | Sizing |
|------|-------------|-------------------|--------|
| **Workhorse** | High trade count, moderate PF, consistent returns. Backbone of the portfolio. | 100+ trades/year, PF 1.15-1.4, low variance | BASE or BOOST |
| **Tail Engine** | Low frequency, high payoff per trade. Captures rare large moves. | 10-30 trades/year, PF > 1.5, high per-trade variance | MICRO or REDUCED |
| **Stabilizer** | Low correlation to portfolio, smooths equity curve. May have modest PF. | Correlation < 0.15 to portfolio, PF > 1.1 | REDUCED or BASE |
| **Event Sleeve** | Calendar-driven, trades only around specific events. | 5-15 trades/year, PF > 1.2, zero overlap with non-event strategies | MICRO |
| **Diversifier** | Operates in an underrepresented factor, asset, or session. Valued for what it ISN'T as much as what it earns. | Fills a stated gap (factor, asset, session) | MICRO to REDUCED |
| **Gap Filler** | Temporary or experimental. Fills a known portfolio gap while a better candidate is developed. | May have lower bar for PF (> 1.1) if gap is critical | MICRO only |

### Current Role Assignments

| Strategy | Role | Justification |
|----------|------|---------------|
| VWAP-MNQ-Long | Workhorse | Highest trade count (163/6yr), backbone |
| XB-PB-EMA-MES-Short | Workhorse | FULL_ON action, consistent contributor |
| BB-EQ-MGC-Long | Tail Engine | 3x efficiency (5.6% trades → 16.6% PnL), low frequency |
| NoiseBoundary-MNQ-Long | Workhorse | 609 trades, perfect WF, steady |
| DailyTrend-MGC-Long | Diversifier | Only daily-horizon strategy, PF 3.65 |
| MomPB-6J-Long-US | Diversifier | FX asset, US session, carry secondary |
| FXBreak-6J-Short-London | Diversifier | FX asset, London session, short bias |
| PreFOMC-Drift-Equity | Event Sleeve | 8 FOMC events/year, zero daily overlap |
| TV-NFP-High-Low-Levels | Event Sleeve | 12 NFP events/year, zero daily overlap |
| CloseVWAP-M2K-Short | Stabilizer | Close session, mean-reversion, low overlap |

### Role-Based Replacement Rules

- **Workhorses** are never replaced — only added alongside. The portfolio
  needs multiple independent workhorses.
- **Tail Engines** can coexist if they target different events or regimes.
  Replace only if a new one is strictly superior on the same asset/session.
- **Diversifiers** are valued for their gap-fill. Replace only if a better
  gap-filler appears in the same dimension AND the old one is underperforming.
- **Event Sleeves** should not overlap on the same event. One strategy per
  event type (FOMC, NFP, OPEC, CPI, etc.).
- **Gap Fillers** are explicitly temporary. Replace when a proper Diversifier
  or Workhorse is validated for that gap.

---

## 5. Probation Slot Limits

| Rule | Limit | Rationale |
|------|-------|-----------|
| **Max probation strategies** | **8** | Attention budget — each needs weekly monitoring. More than 8 dilutes review quality. |
| **Max probation per asset** | **3** | Prevents over-testing on one asset while others are ignored |
| **Max probation in one factor** | **3** | Prevents loading up on the same factor bet |
| **Min forward runner capacity** | Must fit in forward runner without degrading performance | Currently running 17 strategies; practical limit ~25 |
| **Max time in probation** | **16 weeks** | Promote, extend once (to 16w max), or remove. No indefinite probation. |

### Current Probation State (2026-03-18)

- Probation strategies: 5 official + 4 additional = **9 total**
- This exceeds the 8-slot cap. The additional 4 (MomIgn-M2K, CloseVWAP-M2K,
  TTMSqueeze-M2K, ORBEnh-M2K) were activated by the controller before the
  cap was formalized. Going forward, enforce the cap.

### Opening a New Probation Slot

A new strategy enters probation ONLY when:
1. A slot is available (current count < 8) OR an existing probation
   strategy is promoted/removed to make room
2. The candidate fills a factor, asset, or session gap not already
   covered by other probation strategies
3. The candidate passed the full validation battery
4. You explicitly approve the entry

### Priority for Probation Slots

When multiple candidates compete for a slot:
1. Fills a factor GAP (CARRY, STRUCTURAL) → highest priority
2. Fills an asset GAP (rates, 6B) → high priority
3. Fills a session GAP (afternoon, Tokyo) → high priority
4. Diversifier role → medium priority
5. Additional workhorse in a covered area → lowest priority

---

## 6. Add vs Replace Decision Framework

### When to ADD alongside existing strategies

- New strategy operates in a **different factor** than existing
- New strategy operates in a **different session** than existing
- New strategy operates on a **different asset** than existing
- New strategy has **correlation < 0.20** with all existing strategies
- Portfolio has room (under concentration limits)

### When to REPLACE an existing strategy

- New strategy operates in the **same factor + same asset + same session**
  as an existing strategy AND has demonstrably superior metrics:
  - Higher forward PF (not just backtest PF)
  - Higher Sharpe ratio
  - Lower max drawdown
  - Better walk-forward stability
- The existing strategy has a kill flag or is flagged for decay
- The existing strategy is a Gap Filler being replaced by a validated
  Diversifier or Workhorse

### When to do NEITHER (reject the new entrant)

- Portfolio is at concentration limits for the new strategy's factor/asset/session
- New strategy is correlated > 0.35 with an existing strategy that performs
  better
- New strategy doesn't fill any gap and the portfolio has no room
- Adding it would push any concentration metric over the hard cap

### Decision Checklist

Before adding or replacing, verify:
- [ ] Factor concentration stays under 40% for the target factor
- [ ] Asset concentration stays under 5 strategies for the target asset
- [ ] Session concentration stays under 6 for the target session
- [ ] Correlation with every existing active strategy is documented
- [ ] Portfolio role is assigned
- [ ] Net portfolio Sharpe improves (or is neutral with diversification benefit)

---

## 7. Portfolio-Level Warning Triggers

These trigger a review even if every individual strategy looks acceptable.

### Concentration Warnings

| Warning | Trigger | Review Action |
|---------|---------|---------------|
| **Factor tilt** | Any factor > 40% weighted exposure | Pause new entrants in that factor; prioritize harvest in gap factors |
| **Asset crowding** | Any asset ≥ 5 strategies | Reject new entrants on that asset unless they replace a weaker one |
| **Session pile-up** | Morning session ≥ 50% of active | Pause morning strategy development; target afternoon/close/overnight |
| **Direction imbalance** | Long:Short ratio > 3:1 or < 1:3 | Flag; consider adding directional counterweight |

### Correlation Warnings

| Warning | Trigger | Review Action |
|---------|---------|---------------|
| **Pairwise redundancy** | Two strategies corr > 0.35, same asset/direction/family | Flag weaker one for potential removal |
| **Portfolio correlation spike** | Average pairwise correlation across all active > 0.20 | Review for hidden factor exposure; check regime sensitivity |
| **Simultaneous drawdown** | 3+ strategies losing on the same day, 3+ times in a month | Run correlation analysis; may be disguised single bet |

### Performance Warnings

| Warning | Trigger | Review Action |
|---------|---------|---------------|
| **Portfolio Sharpe decay** | Rolling 60-day Sharpe < 0.5 (annualized) | Review regime fit; check if multiple strategies are decaying |
| **Drawdown breach** | Portfolio DD > 2x historical max DD | Emergency review — check kill criteria across all strategies |
| **Win rate collapse** | Portfolio win rate drops below 35% over 30+ trades | Review whether edge is structural or was regime-dependent |
| **Dead capital** | 3+ strategies at MICRO tier with 0 trades in 4+ weeks | Review signal generation; consider removing to free slots |

### Structural Warnings

| Warning | Trigger | Review Action |
|---------|---------|---------------|
| **Regime concentration** | 60%+ of PnL comes from one regime (TRENDING or RANGING) | Portfolio is regime-dependent; prioritize regime-neutral strategies |
| **Vintage concentration** | All core strategies developed in the same 3-month period | Overfitting risk to the regime that was dominant during development |
| **Horizon collapse** | 80%+ of strategies on the same bar frequency (e.g., 5-minute) | Single-horizon risk; prioritize daily, swing, or monthly strategies |
| **Event calendar gap** | Next 30 days have 0 scheduled event trades | Event sleeves are dormant — acceptable but monitor for evidence accumulation pace |

---

## 8. Portfolio Review Cadence

| Review | Frequency | What It Checks |
|--------|-----------|----------------|
| Factor concentration | Weekly (scorecard) | Any factor over 40%? Any GAP factors? |
| Asset concentration | Weekly (scorecard) | Any asset over cap? |
| Pairwise correlation | Monthly (contribution report) | Any pair > 0.35? |
| Portfolio Sharpe | Weekly (scorecard) | Rolling 60-day above 0.5? |
| Session distribution | Monthly (genome map) | Morning still dominant? Gaps? |
| Probation slot count | Before any new entry | Under 8? Room for the candidate? |
| Role balance | Quarterly | Enough workhorses? Enough diversifiers? |

---

## Appendix: Concentration Limits Summary

| Dimension | Soft Limit | Hard Cap | Current State |
|-----------|-----------|----------|---------------|
| Factor (single) | 40% | 50% | MOMENTUM 61% — **OVER** |
| Asset (single) | 4 strategies | 5 strategies | MNQ/MGC/M2K at 4 — **AT LIMIT** |
| Session (single) | 5 strategies | 6 strategies | Morning at ~8 — **OVER** |
| Probation slots | 6 | 8 | 9 — **OVER** (legacy, enforce going forward) |
| Direction ratio | 2:1 | 3:1 | ~2:1 long:short — OK |
| Horizon (single bar freq) | 70% | 80% | ~80% intraday 5m — **AT LIMIT** |
| Pairwise correlation | 0.25 (flag) | 0.35 (act) | 1 pair flagged (Donchian/NoiseBoundary) |
