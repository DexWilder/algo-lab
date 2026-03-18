# FQL Portfolio Construction Policy

*Layered framework: universal principles + deployment overlays.*
*Effective: 2026-03-18*

---

## Architecture

This policy is structured in three layers:

1. **Layer A — Universal Base:** Research and construction principles that
   hold regardless of deployment context. These are permanent.
2. **Layer B — Prop-First Overlay:** Rules specific to the current
   prop-account deployment. These are the active operating constraints.
3. **Layer C — Cash-Account Overlay (Placeholder):** Future rules for
   cash-account or multi-account deployment. Not active — reserved for
   when the capital base and opportunity set justify it.

Layer A is the constitution. Layers B and C are deployment configurations
that sit on top of it. When FQL transitions to cash-account deployment,
Layer B stays in place for the prop book and Layer C activates alongside
it. Nothing in Layer A changes.

---

# LAYER A — UNIVERSAL BASE

*These principles persist across all deployment contexts.*

---

## A1. Core Construction Principle

The goal is to maximize the number of genuinely independent, elite-quality
bets while controlling concentration risk. Every rule exists to prevent
the portfolio from silently collapsing into a single bet disguised as
many strategies.

**Elite standard applies to portfolio construction.** A portfolio of 20
mediocre strategies is worse than a portfolio of 8 strong ones. Every
slot costs attention, margin, and complexity. A strategy that merely
doesn't lose money is not earning its place — it must actively contribute
edge, diversification, or structural resilience. When in doubt, fewer
and stronger beats more and weaker.

This applies whether the portfolio runs $50K on a prop account or $5M
across managed accounts.

---

## A1b. Cap Philosophy: Competition, Not Stagnation

Caps apply to attention-consuming active slots only:

| Layer | Capped? | Max | Purpose |
|-------|---------|-----|---------|
| **Core** | Yes | 10 | Replacement pressure — to add #11, archive the weakest |
| **Conviction probation** | Yes | 5 | Weekly monitoring budget — only the strongest candidates |
| **Watch** | Yes | 3 | Quarterly review budget — promising but unproven |
| **Testing** | No | Unlimited | Factory pipeline, zero monitoring cost |
| **Ideas / Catalog** | No | Unlimited | Discovery engine — grows without bound |

### Caps Create Competition, Not Stagnation

**A full cap does NOT block an elite new candidate from entering.**

Instead, a full cap forces a displacement decision. If a new candidate
scores higher on the Elite Review Rubric than the weakest incumbent in
the capped bucket, it may replace that incumbent. The displaced strategy
moves down one layer (core → watch, conviction → watch, watch → testing).

This means:
- The catalog and testing pipeline are never constrained — discovery
  is relentless and unlimited
- Every capped slot is earned and defended — incumbents must remain
  elite or risk displacement
- The portfolio trends toward higher quality over time as stronger
  candidates displace weaker ones
- No strategy survives on tenure alone — only on current evidence
  and rubric score

### Displacement Rules

1. **New candidate must score higher** than the weakest incumbent on
   the Elite Review Rubric (6-question total score)
2. **Ties go to the incumbent** — burden of proof is on the new entrant
3. **Gap-filling candidates get +2 rubric bonus** when competing for
   displacement. A strategy that fills a factor/asset/session gap is
   more valuable than one that adds depth to a covered area.
4. **Event sleeves count at 0.5 slots** against conviction and core
   caps. Low monitoring cost, high diversification value.
5. **Displacement is logged** in the registry with state_history entry
   documenting what was displaced and why.

---

## A2. Factor Diversification

### Rules (Universal)

| Rule | Threshold | Action |
|------|-----------|--------|
| Single factor > 40% of weighted active exposure | **SOFT CAP** | No new strategies in that factor until another factor grows |
| Single factor > 50% of weighted active exposure | **HARD CAP** | Actively reduce; high-bar rule on new entrants |
| Factor with 0 active or probation strategies | **GAP** | Prioritize in harvest targeting |
| Factor with 5+ active strategies | **OVERCROWDED** | No new entrants unless clearly superior to weakest existing |

### Factor Weighting Method

- Primary factor = 1.0 weight
- Secondary factor = 0.5 weight
- A strategy with primary=MOMENTUM, secondary=CARRY contributes 1.0 to
  MOMENTUM and 0.5 to CARRY

### Six Factors

| Factor | What It Captures |
|--------|------------------|
| MOMENTUM | Directional continuation, trend, breakout, pullback-with-trend |
| MEAN_REVERSION | Fade extremes, VWAP fade, RSI bounce, range reversion |
| VOLATILITY | Vol expansion/compression, squeeze, NR7, ATR-based |
| CARRY | Macro/yield directional bias, roll yield, term structure |
| EVENT | Calendar or news driven (FOMC, NFP, CPI, OPEC, auctions) |
| STRUCTURAL | Session microstructure, time-of-day, handoff, closing auction |

---

## A3. Asset Diversification

### Rules (Universal)

| Rule | Threshold | Action |
|------|-----------|--------|
| Single asset ≥ hard cap (deployment-specific) | **HARD CAP** | No new strategies on that asset |
| Single asset class ≥ 50% of active strategies | **REBALANCE** | Prioritize other asset classes |
| Asset with 0 active strategies | **GAP** | Flag in harvest targeting |

### Asset Classes

| Class | Instruments |
|-------|-------------|
| Equity Index | MES, MNQ, M2K, MYM |
| Metal | MGC, SI, HG |
| Energy | MCL, NG |
| FX | 6E, 6J, 6B |
| Rates | ZN, ZF, ZB |
| Agriculture | ZS, ZC, ZW (future) |

---

## A4. Session and Time-of-Day Diversification

### Rules (Universal)

| Rule | Threshold | Action |
|------|-----------|--------|
| Single session ≥ hard cap (deployment-specific) | **HARD CAP** | No new strategies in that session |
| Any session ≥ 50% of active strategies | **REBALANCE** | Prioritize underrepresented sessions |
| Session with 0 active strategies | **GAP** | Flag in harvest targeting |
| 3+ strategies signaling in same 30-min window on same asset | **CROWDED** | Correlation check; stagger or remove weakest |

### Time Overlap Rule

When 3+ strategies trade the same asset in the same 30-minute window,
run a correlation check on their daily PnL. If correlation > 0.35,
they are effectively one bet. Either remove the weakest, stagger entry
times, or accept the overlap only if factor diversity justifies it.

---

## A5. Portfolio Role Taxonomy

Every active strategy gets a role label. Roles determine sizing behavior,
replacement rules, and how the strategy contributes to the whole.

| Role | Description | Expected Behavior |
|------|-------------|-------------------|
| **Workhorse** | High trade count, moderate PF, consistent. Backbone. | 100+ trades/year, PF 1.15-1.4, low variance |
| **Tail Engine** | Low frequency, high payoff. Captures rare large moves. | 10-30 trades/year, PF > 1.5, high per-trade variance |
| **Stabilizer** | Low correlation, smooths equity curve. Modest PF OK. | Correlation < 0.15 to portfolio, PF > 1.1 |
| **Event Sleeve** | Calendar-driven, trades only around specific events. | 5-15 trades/year, PF > 1.2, zero non-event overlap |
| **Diversifier** | Fills an underrepresented factor, asset, or session. | Valued for what it ISN'T as much as what it earns |
| **Gap Filler** | Temporary. Holds a gap while a proper candidate develops. | Lower PF bar (> 1.1) if gap is critical. MICRO only. |

### Role-Based Replacement Rules (Universal)

- **Workhorses:** never replaced, only added alongside
- **Tail Engines:** coexist if different events/regimes; replace only if
  strictly superior on same asset/session
- **Diversifiers:** replace only if better gap-filler appears in same
  dimension AND old one is underperforming
- **Event Sleeves:** one per event type (FOMC, NFP, OPEC, CPI, etc.)
- **Gap Fillers:** explicitly temporary; replace when proper candidate validated

---

## A6. Add vs Replace Decision Framework

### When to ADD alongside

- Different factor, session, or asset than existing
- Correlation < 0.20 with all existing strategies
- Portfolio has room under concentration limits

### When to REPLACE

- Same factor + same asset + same session as existing AND demonstrably
  superior (higher forward PF, higher Sharpe, lower DD, better WF stability)
- Existing strategy has a kill flag or decay flag
- Existing strategy is a Gap Filler being replaced by a validated candidate

### When to REJECT

- Concentration limits breached for the new strategy's factor/asset/session
- Correlated > 0.35 with a better-performing existing strategy
- Doesn't fill any gap and portfolio has no room

### Decision Checklist (Universal)

Before adding or replacing:
- [ ] Factor concentration stays within limits
- [ ] Asset concentration stays within limits
- [ ] Session concentration stays within limits
- [ ] Correlation with every existing active strategy documented
- [ ] Portfolio role assigned
- [ ] Net portfolio Sharpe improves or is neutral with diversification benefit

---

## A7. Portfolio-Level Warning Triggers

These trigger a review even if individual strategies look acceptable.

### Concentration Warnings

| Warning | Trigger | Action |
|---------|---------|--------|
| Factor tilt | Any factor > 40% | Pause new entrants; prioritize gap factors |
| Asset crowding | Any asset at hard cap | Reject new entrants unless replacing weaker |
| Session pile-up | Any session ≥ 50% of active | Target underrepresented sessions |
| Direction imbalance | Long:Short > 3:1 or < 1:3 | Add directional counterweight |

### Correlation Warnings

| Warning | Trigger | Action |
|---------|---------|--------|
| Pairwise redundancy | Two strategies corr > 0.35, same asset/direction/family | Flag weaker for removal |
| Portfolio correlation spike | Average pairwise corr > 0.20 | Check hidden factor exposure |
| Simultaneous drawdown | 3+ strategies losing same day, 3+ times/month | Correlation analysis |

### Performance Warnings

| Warning | Trigger | Action |
|---------|---------|--------|
| Portfolio Sharpe decay | Rolling 60-day Sharpe < 0.5 | Review regime fit |
| Drawdown breach | DD > 2x historical max | Emergency review |
| Win rate collapse | WR < 35% over 30+ trades | Review structural vs regime edge |
| Dead capital | 3+ strategies at MICRO with 0 trades in 4+ weeks | Remove to free slots |

### Structural Warnings

| Warning | Trigger | Action |
|---------|---------|--------|
| Regime concentration | 60%+ PnL from one regime | Prioritize regime-neutral strategies |
| Vintage concentration | All core from same 3-month dev period | Overfitting risk |
| Horizon collapse | 80%+ on same bar frequency | Prioritize other horizons |
| Event calendar gap | 0 event trades in next 30 days | Monitor evidence pace |

---

## A8. Portfolio Review Cadence (Universal)

| Review | Frequency | What It Checks |
|--------|-----------|----------------|
| Factor concentration | Weekly | Over 40%? GAP factors? |
| Asset concentration | Weekly | Over cap? |
| Pairwise correlation | Monthly | Any pair > 0.35? |
| Portfolio Sharpe | Weekly | Rolling 60-day above 0.5? |
| Session distribution | Monthly | Dominant session? Gaps? |
| Role balance | Quarterly | Enough workhorses and diversifiers? |
| Probation slot count | Before any new entry | Under cap? Room? |

---

# LAYER B — PROP-FIRST DEPLOYMENT OVERLAY

*Active operating constraints for the current prop-account deployment.*
*These rules sit on top of Layer A and may be tightened or loosened*
*without changing the universal base.*

---

## B1. Deployment Context

- **Account type:** Single prop account (micro futures)
- **Starting capital:** $50,000
- **Contract size:** 1 micro contract per strategy per signal
- **Margin model:** exchange minimums, no portfolio margin
- **Execution:** Manual start with automated downstream (forward runner)
- **Objective:** Compound capital with mechanical edges; prove the system
  works before scaling

---

## B2. Prop-Specific Slot Structure and Concentration Limits

### Slot Caps (Active)

| Bucket | Cap | Monitoring | Displacement? |
|--------|-----|-----------|---------------|
| **Core** | 10 | Daily (automated) + weekly review | Yes — weakest can be displaced by stronger promoted strategy |
| **Conviction probation** | 5 | Weekly review, active promotion timeline | Yes — weakest displaced by stronger validated candidate |
| **Watch** | 3 | Quarterly review, passive evidence accumulation | Yes — weakest displaced, or expires at deadline |
| **Event sleeves** | Count at 0.5 | Checkpoint review only | Same displacement rules |

### Uncapped (Unlimited)

| Bucket | Monitoring | Purpose |
|--------|-----------|---------|
| Testing | Zero (batch pipeline handles it) | Factory throughput |
| Ideas / Catalog | Zero | Discovery engine |

### Concentration Limits

| Dimension | Soft Limit | Hard Cap | Rationale |
|-----------|-----------|----------|-----------|
| Asset (single) | 4 strategies | 5 | Attention budget is finite |
| Session (single) | 4 strategies | 5 | Morning concentration is #1 structural risk |
| Factor (single) | 40% | 50% | Force diversification; ELITE-only entrants above 40%, zero above 50% |
| Max conviction per asset | 3 | — | Prevent over-testing one asset |
| Max conviction per factor | 3 | — | Prevent loading same factor bet |
| Max time in conviction | 16 weeks (24 for events) | — | Promote, extend once, or remove |
| Max time in watch | 16 weeks | — | Promote, archive, or expire |
| Direction ratio | 1.5:1 | 3:1 | Push harder for short-side strategies |
| Horizon (single bar freq) | 60% | 80% | Push for non-5m strategies |

### Watch Slot Rules

Every watch strategy must have:
- **A review deadline** (max 16 weeks from entry)
- **A promote condition** (specific metric that elevates to conviction)
- **An archive condition** (specific metric that eliminates it)
- No indefinite passive survival — deadline is enforced

### Prop-Specific Asset Distribution Target

| Asset Class | Target Range |
|-------------|-------------|
| Equity Index | 30-50% |
| Metal | 15-25% |
| Energy | 10-20% |
| FX | 10-25% |
| Rates | 5-15% |

---

## B3. Prop-Specific Tier Sizing

| Tier | Contracts | When Used |
|------|-----------|-----------|
| OFF | 0 | Disabled, archived, or kill-flagged |
| MICRO | 1 | New probation entrants, event sleeves, gap fillers |
| REDUCED | 1 | Early probation with evidence, newly promoted |
| BASE | 1 | Proven core strategies with forward evidence |
| BOOST | 1 | Exceptional forward evidence (PF > 1.5, 100+ trades) |
| MAX_ALLOWED | 1 | Reserved; requires explicit approval |

On a micro-futures prop account, all tiers execute 1 contract. The tier
distinction matters for: controller action priority, which strategies
survive regime-driven cuts, and future position sizing when capital scales.

---

## B4. Prop-Specific Probation Thresholds

| Strategy | Target Trades | Promote PF | Downgrade PF | Remove PF |
|----------|--------------|------------|--------------|-----------|
| DailyTrend-MGC-Long | 15 | > 1.2 | < 1.0 | < 0.7 after 20 |
| MomPB-6J-Long-US | 30 | > 1.2 | < 1.0 | < 0.8 after 40 |
| FXBreak-6J-Short-London | 50 | > 1.1 | < 0.95 | < 0.85 after 60 |
| PreFOMC-Drift-Equity | 8 | > 1.2 | < 0.9 | < 0.7 after 12 |
| TV-NFP-High-Low-Levels | 8 | > 1.1 | < 0.9 | < 0.7 after 12 |

---

## B5. Prop-Specific Role Sizing

| Role | Default Tier | Tier-Up Criteria | Tier-Down Criteria |
|------|-------------|-----------------|-------------------|
| Workhorse | BASE | 3 consecutive positive months, PF > 1.3 | 2 consecutive negative months or PF < 1.0 |
| Tail Engine | REDUCED | Not tier-eligible (low frequency) | Kill flag or PF < 1.0 after 30+ trades |
| Stabilizer | REDUCED | Contribution confirmed positive for 3 months | Contribution turns dilutive |
| Event Sleeve | MICRO | Not tier-eligible (too few trades/year) | Forward PF < 0.9 after target trades |
| Diversifier | MICRO → REDUCED | Passes probation with promote-level PF | Kill flag or forward evidence weakens |
| Gap Filler | MICRO only | Cannot tier up (temporary by definition) | Replaced by proper candidate |

---

## B6. Current Portfolio State (Prop Overlay Snapshot)

### Factor State

| Factor | Core | Probation | % Active | Status |
|--------|------|-----------|----------|--------|
| MOMENTUM | 5 | 6 | ~61% | **OVER HARD CAP** |
| MEAN_REVERSION | 1 | 2 | ~17% | Adequate |
| VOLATILITY | 0 | 3 | ~17% | No core yet |
| EVENT | 0 | 2 | ~11% | Growing |
| CARRY | 0 | 0 | 0% | **GAP** |
| STRUCTURAL | 0 | 1 | ~6% | **THIN** |

### Role Assignments

| Strategy | Role |
|----------|------|
| VWAP-MNQ-Long | Workhorse |
| XB-PB-EMA-MES-Short | Workhorse |
| NoiseBoundary-MNQ-Long | Workhorse |
| BB-EQ-MGC-Long | Tail Engine |
| DailyTrend-MGC-Long | Diversifier |
| MomPB-6J-Long-US | Diversifier |
| FXBreak-6J-Short-London | Diversifier |
| PreFOMC-Drift-Equity | Event Sleeve |
| TV-NFP-High-Low-Levels | Event Sleeve |
| CloseVWAP-M2K-Short | Stabilizer |

### Concentration Summary

| Dimension | Soft | Hard | Current | Status |
|-----------|------|------|---------|--------|
| Factor (MOMENTUM) | 40% | 50% | 61% | **OVER** |
| Asset (MNQ/MGC/M2K) | 4 | 5 | 4 each | **AT LIMIT** |
| Session (morning) | 5 | 6 | ~8 | **OVER** |
| Probation slots | 6 | 8 | 9 | **OVER (legacy)** |
| Horizon (5m intraday) | 70% | 80% | ~80% | **AT LIMIT** |

---

# LAYER C — CASH-ACCOUNT DEPLOYMENT OVERLAY (PLACEHOLDER)

*Reserved for future deployment to cash or managed accounts.*
*Not active. Layer A universal rules apply when this activates.*

---

## C1. Design Intent

When FQL's prop-account track record, strategy catalog, and infrastructure
justify managing external capital, Layer C activates alongside Layer B.
The prop book continues running under Layer B rules. The cash-account book
runs under Layer C rules. Both share the same Layer A universal base.

Key differences between prop and cash deployment:
- **Position sizing:** Multi-contract, volatility-targeted, not fixed 1-lot
- **Margin model:** Portfolio margin or prime broker margin
- **Risk budget:** Defined by investor mandate, not personal tolerance
- **Reporting:** Formal NAV, drawdown tracking, investor-grade reporting
- **Concentration limits:** Potentially tighter (institutional standards)

---

## C2. Placeholder Parameters (To Be Defined)

These will be set when the cash-account deployment is designed:

| Parameter | Prop (Layer B) | Cash (Layer C) | Notes |
|-----------|---------------|----------------|-------|
| Contract sizing | 1 micro | Volatility-targeted | Scale by strategy vol budget |
| Max portfolio DD | No hard limit (personal) | TBD (e.g., 10-15%) | Investor mandate |
| Max strategy DD | $5K remove trigger | TBD (% of allocation) | Proportional to AUM |
| Correlation hard cap | 0.35 | TBD (potentially 0.25) | Tighter for institutional |
| Factor hard cap | 50% | TBD (potentially 35%) | Institutional diversification |
| Asset hard cap | 5 strategies | TBD (potentially by notional) | Notional-based, not count-based |
| Probation slots | 8 | TBD | May run separate probation book |
| Reporting | Weekly scorecard | TBD (daily NAV, monthly letter) | Investor-grade |
| Execution | Manual start | TBD (automated or managed) | Depends on scale |

---

## C3. What Carries Over From Layer A

When Layer C activates, the following Layer A rules carry over unchanged:
- Factor diversification framework (6 factors, weighting method)
- Asset diversification framework (asset classes, gap targeting)
- Session diversification framework (time overlap rules)
- Portfolio role taxonomy (6 roles, replacement rules)
- Add vs replace decision framework
- Portfolio-level warning triggers (all 14)
- Review cadence structure

What changes in Layer C (relative to Layer B):
- Concentration limits may tighten
- Sizing moves from fixed-lot to volatility-targeted
- Drawdown limits become mandate-driven
- Reporting becomes investor-grade
- Execution may become fully automated

---

## C4. Transition Criteria (When to Activate Layer C)

Layer C should be designed and activated when:
- Prop account has 12+ months of forward evidence
- At least 3 core strategies promoted with forward PF > 1.2
- Factor coverage spans at least 3 of 6 factors in core
- Infrastructure supports multi-contract sizing
- Legal/compliance framework is in place for external capital

These are necessary conditions, not sufficient. The decision to accept
external capital is strategic and personal — not triggered automatically.
