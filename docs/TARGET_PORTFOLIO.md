# FQL Target Portfolio — End-State Design

*What the ideal 8-12 strategy portfolio should look like.*
*Effective: 2026-03-26*

---

## Design Principle

The portfolio maximizes the number of genuinely independent, elite-quality
bets while controlling concentration risk. Every slot costs attention,
margin, and complexity. A strategy that merely doesn't lose money is not
earning its place — it must actively contribute edge, diversification,
or structural resilience.

---

## Target Composition: 10 Core Strategies

### By Role (4 categories)

| Role | Target Count | Purpose | Current |
|------|-------------|---------|---------|
| **Workhorse** | 3-4 | High trade count, steady PF 1.15-1.4, backbone of equity curve | 3 (VWAP-MNQ, XB-PB-MES, NoiseBoundary-MNQ) |
| **Tail Engine** | 1-2 | Low frequency, high payoff per trade, captures rare large moves | 1 (BB-EQ-MGC) |
| **Stabilizer** | 2-3 | Low correlation, smooths equity curve, may include sizing overlays | 0 core (VolManaged in probation) |
| **Event Sleeve** | 2-3 | Calendar-driven, trades around specific events, counts at 0.5 slots | 0 core (PreFOMC + TV-NFP in probation) |

### By Factor (6 factors, no >40% concentration)

| Factor | Target % | Target Count | Current Core | Gap |
|--------|----------|-------------|-------------|-----|
| MOMENTUM | 25-35% | 3 | 3 | At limit — no more |
| MEAN_REVERSION | 10-15% | 1 | 1 | OK |
| VOLATILITY | 10-20% | 1-2 | 0 | **GAP** — VolManaged in pipeline |
| CARRY | 10-15% | 1 | 0 | **GAP** — Treasury-Rolldown in pipeline |
| EVENT | 10-15% | 1-2 (at 0.5 slots) | 0 | **GAP** — PreFOMC + NFP in pipeline |
| STRUCTURAL | 10-15% | 1 | 0 | **GAP** — ZN-Afternoon-Rev in pipeline |
| VALUE | 5-10% | 0-1 | 0 | **BLIND SPOT** — no pipeline candidates |

### By Asset Class

| Asset Class | Target % | Target Count | Current Core | Gap |
|-------------|----------|-------------|-------------|-----|
| Equity Index (MES/MNQ/M2K) | 30-40% | 3-4 | 2 | Heavy if probation promotes |
| Metal (MGC) | 15-20% | 1-2 | 2 | At limit |
| Energy (MCL) | 10-15% | 1 | 0 | **GAP** |
| FX (6J/6E/6B) | 10-15% | 1 | 0 | Thin (MomPB-6J in probation) |
| Rates (ZN/ZF/ZB) | 10-15% | 1-2 | 0 | Growing (2 in probation) |

### By Session

| Session | Target | Current Core | Gap |
|---------|--------|-------------|-----|
| Morning (09:30-12:00) | 3-4 max | 4 | **AT LIMIT** |
| Afternoon (12:00-16:00) | 1-2 | 0 | **GAP** — ZN-Afternoon in pipeline |
| Daily/Close | 1-2 | 0 | VolManaged + Treasury-Rolldown in pipeline |
| Overnight/Event | 1-2 | 0 | PreFOMC in pipeline |

### By Direction

| Direction | Target | Current |
|-----------|--------|---------|
| Long-only | 4-5 | 3 core + most probation |
| Short-only | 2-3 | 1 core (PB-MGC) |
| Both-direction | 2-3 | 0 core (ZN-Afternoon + Treasury-Rolldown in probation) |
| **Target ratio** | **< 2:1 long:short** | **Currently 3:1 — needs short exposure** |

---

## Promotion Path: Current Pipeline → Target

### Highest-Priority Promotions (if evidence confirms)

| Strategy | Target Role | What It Fills | Promotion Gate |
|----------|-------------|--------------|---------------|
| **VolManaged-EquityIndex** | Stabilizer | VOLATILITY factor, unique mechanism | 30 forward days, Sharpe > 0.5 |
| **Treasury-Rolldown-Carry** | Stabilizer / Diversifier | CARRY + Rates (2 gaps) | June 1 displacement, forward PnL > 0 |
| **ZN-Afternoon-Reversion** | Diversifier | STRUCTURAL + afternoon + short-biased | 30 trades, PF > 1.1 |
| **PreFOMC-Drift-Equity** | Event Sleeve | EVENT factor | 8 trades, PF > 1.2 |

### What the Portfolio Looks Like After Successful Promotions

```
CORE (10 strategies, 7.5 effective slots):
  Workhorses (3):
    VWAP-MNQ-Long          — MOMENTUM, equity, morning
    XB-PB-EMA-MES-Short    — MOMENTUM, equity, morning, SHORT
    NoiseBoundary-MNQ-Long — MOMENTUM, equity, all-day

  Tail Engine (1):
    BB-EQ-MGC-Long         — MEAN_REVERSION, metal, morning

  Stabilizers (3):
    VolManaged-Equity       — VOLATILITY, equity, daily (sizing overlay)
    Treasury-Rolldown-Carry — CARRY, rates, monthly (spread)
    ZN-Afternoon-Reversion  — STRUCTURAL, rates, afternoon, SHORT-BIASED

  Event Sleeves (2, counting at 0.5 each = 1 effective slot):
    PreFOMC-Drift-Equity    — EVENT, equity, overnight
    TV-NFP-High-Low-Levels  — EVENT, equity, multi-day

  GAP REMAINING:
    - No Energy strategy
    - No VALUE strategy
    - No FX core (MomPB-6J still in probation)
    - Morning session still heavy (3 of 10)
    - Long bias improved but not eliminated
```

### What Still Needs to Be Found

| Gap | Priority | Where to Look |
|-----|----------|--------------|
| **Energy (MCL)** | HIGH | Harvest catalog — currently 0 testable ideas |
| **VALUE** | HIGH | Harvest catalog — 0 ideas. Digest/blog feeds may produce |
| **Short-biased non-equity** | MEDIUM | ZN-Afternoon helps. Need more short exposure on non-equity |
| **FX core** | MEDIUM | MomPB-6J in probation — promote if evidence confirms |
| **Non-morning workhorse** | LOW | Most workhorses are morning. A daily or afternoon workhorse would reduce session concentration |

---

## Constraints (Non-Negotiable)

1. **No factor > 40% of active exposure** — portfolio construction policy
2. **No asset > 5 strategies** — attention budget limit
3. **No session > 5 strategies** — morning crowding is the #1 risk
4. **Long:short ratio < 3:1** — must actively seek short exposure
5. **Every core strategy must have forward evidence** — no backtest-only core
6. **Every promotion must improve marginal Sharpe** — must be additive
7. **Event sleeves count at 0.5 slots** — low monitoring cost
8. **Displacement rules apply** — weakest incumbent must be weaker than new entrant

---

## Live Deployment Constitution

### Prerequisites Before Any Live Broker Deployment

| Requirement | Threshold |
|-------------|-----------|
| Forward evidence | ≥ 3 months paper trading with positive PnL |
| Core strategies | ≥ 6 promoted with forward evidence |
| Factor coverage | ≥ 3 factors represented in core |
| Kill switch tested | At least 1 live drill of each kill trigger |
| Drawdown protocol | Max DD limit defined and tested |
| Data feed reliability | ≥ 30 days of automated data refresh without failure |
| Execution adapter | Built and tested for each broker/platform |
| Position sizing | Vol-targeted, tested across regime changes |

### Safety Checks (Non-Negotiable for Live)

| Check | Requirement |
|-------|-------------|
| Daily loss limit | Hard stop at defined $ amount |
| Trailing DD limit | Hard stop at defined $ from HWM |
| Consecutive loss breaker | Pause after N consecutive losers |
| Correlated loss detection | Halt if 3+ strategies lose on same day |
| Data feed watchdog | Alert + pause if data goes stale mid-session |
| Position limit | Max contracts per asset, enforced by execution layer |
| No manual override in production | All entries/exits are systematic |

### Scaling Path

| Phase | Capital | Strategies | Contract Size |
|-------|---------|-----------|---------------|
| **Current (Paper)** | $50K simulated | 4 core + 8 probation | 1 micro |
| **Phase 1 (Live proof)** | $50K prop | 6-8 core | 1 micro |
| **Phase 2 (Proven)** | $50-100K | 8-10 core | 1-2 micro, vol-targeted |
| **Phase 3 (Scale)** | $100K+ | 10 core | Vol-targeted, multi-contract |
