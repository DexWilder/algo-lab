# FQL Deployment Sequence

*Concrete rollout from paper forward through real-cash pilot.*
*Every stage has a purpose, a gate, and a parallel requirement.*
*Effective: 2026-03-18*

---

## Sequence Overview

```
STAGE 1: Paper Forward (ACTIVE NOW)
    ↓ gate
STAGE 2: Small Live Prop
    ↓ gate (paper continues in parallel)
STAGE 3: Cash Paper
    ↓ gate (prop live + paper both continue)
STAGE 4: Small Real-Cash Pilot
    (prop live + cash paper + paper forward all continue)
```

Every later stage runs in parallel with every earlier stage. Nothing
shuts down. Paper forward runs forever as the system's ground truth.

---

## Stage 1: Paper Forward

*Prove the system generates signals, accumulates evidence, and the
lifecycle pipeline works end-to-end.*

### What's Running
- Forward paper trading runner (`run_forward_paper.py`)
- All automated pipelines (daily research, twice-weekly batch, weekly integrity)
- Claude↔Claw discovery loop (30-min cadence)
- Replacement scoreboard, counterfactual, vitality monitor
- Master Operating Brief

### What's Being Proven
- Strategies generate signals on live market data
- The forward runner logs trades correctly
- Probation strategies accumulate evidence at expected rates
- The lifecycle works: idea → tested → validation → probation → promotion
- The elite standard produces meaningful quality pressure
- The automation runs reliably without manual intervention
- At least one full probation cycle completes (16-24 weeks)

### Key Metrics Tracked
- Forward trades per strategy per week
- Forward PF per strategy (accumulating)
- Forward portfolio Sharpe (rolling 60-day)
- Forward max DD
- Automation health (all components HEALTHY)
- Probation checkpoint decisions made on evidence

### Current Status (2026-03-18)
- Forward runner: 5 runs, 14 trades, 4 strategies trading
- Equity: $49,224 (DD $776 from $50K HWM)
- Probation: 5 conviction + 5 watch
- Core: 4 strategies
- Automation: all HEALTHY except weekly_research NOT_YET_DUE
- Discovery: Claw completing 4 phases/day, 110 registry entries

### Gate to Stage 2

**ALL must be true:**

| # | Gate | Threshold | Why |
|---|------|-----------|-----|
| 1 | Forward duration | **6+ months continuous** | Covers multiple market regimes, not just one favorable stretch |
| 2 | Core promotions | **3+ strategies promoted** from probation with forward PF > 1.2 | Proves the lifecycle pipeline works end-to-end |
| 3 | Factor diversity | **2+ distinct factors** in core (not just MOMENTUM) | Proves the portfolio isn't a single-factor bet |
| 4 | Forward portfolio Sharpe | **> 0.3** (trailing 6 months, annualized) | Bare minimum: system generates positive risk-adjusted return in paper |
| 5 | Forward max DD | **< 20%** over the paper period | Proves drawdown is controlled even without DD limits |
| 6 | Automation health | **HEALTHY for 30+ consecutive days** | Proves the system runs without babysitting |
| 7 | No critical governance gaps | All docs current, all standing rules enforced | System is operable, not just by you but in principle by a successor |
| 8 | Manual review | **You are personally confident** the system works | No gate replaces judgment. If the numbers pass but your gut says no, don't proceed. |

### Blocking Conditions (Do NOT proceed if)
- Forward Sharpe is negative over any rolling 3-month window
- More than 2 strategies were killed during the paper period for decay
- Automation had a failure lasting > 48 hours that wasn't caught by the brief
- Any probation strategy was promoted despite failing the rubric threshold

---

## Stage 2: Small Live Prop

*Prove the system generates real PnL on real capital with real fills.*

### What's Running
- **NEW: Live prop account** ($25-50K, micro contracts, 1 lot per strategy)
- Paper forward continues in parallel (identical strategy set)
- All automated pipelines unchanged
- Discovery loop unchanged

### What's Being Proven
- Real fills match paper fills within expected slippage
- Real commissions match estimates
- The forward runner operates correctly in live mode
- Drawdown behavior on real capital matches paper expectations
- Psychological discipline holds (no manual overrides outside governance)
- Paper-to-live divergence is small and explainable

### What Changes From Paper
- `FORWARD_ENABLED=true` in forward runner config
- Orders route to broker API (Interactive Brokers or equivalent)
- Pre-trade checks activated (margin, position limits)
- Daily reconciliation: compare live fills vs paper signals
- Real money on the line — governance discipline is tested for real

### What Continues In Parallel
- **Paper forward runs identically.** Same strategies, same signals,
  same timing. The paper and live accounts should produce near-identical
  trade logs. Divergence > 5% of PnL per month is investigated.
- All automation, discovery, scoreboard, vitality monitor unchanged.
- Master Operating Brief adds a "Live vs Paper" comparison section.

### Key Metrics Tracked
- Live PnL vs paper PnL (should be within 5%)
- Slippage: actual vs estimated (should be < 2 ticks average)
- Commission: actual vs estimated
- Fill rate: % of signals that execute successfully
- Live max DD (tracked against paper DD for divergence)
- Psychological log: any manual overrides or interventions documented

### Gate to Stage 3

**ALL must be true:**

| # | Gate | Threshold | Why |
|---|------|-----------|-----|
| 1 | Live duration | **6+ months** | Full regime diversity in live trading |
| 2 | Live-paper divergence | **< 10% cumulative PnL divergence** | Proves paper ≈ live. Larger gaps mean execution or data problems. |
| 3 | Live portfolio Sharpe | **> 0.3** (trailing 6 months) | System is profitable live, not just on paper |
| 4 | Live max DD | **< 15%** | Drawdown controlled with real capital |
| 5 | Core strategies | **3+ promoted** with live (not just paper) PF > 1.2 | Forward evidence must include real fills |
| 6 | Factor diversity in core | **2+ factors** | Same bar as paper but confirmed with live data |
| 7 | Zero manual overrides | No trades added/removed outside governance | Discipline proven under real pressure |
| 8 | Automation uptime | **> 99%** (missed < 3 trading days in 6 months) | System is reliable enough for larger capital |

### Blocking Conditions
- Live-paper divergence > 20% (execution problem)
- Live DD > 15% (risk management problem)
- Any manual override not documented and approved
- Broker API failure > 2 trading days without automated detection

---

## Stage 3: Cash Paper

*Prove the cash-account sizing, DD limits, and reporting work before
risking real cash capital.*

### What's Running
- **NEW: Cash paper account** (simulated $200-500K with vol-targeted sizing)
- Live prop continues ($25-50K, 1 lot per strategy)
- Paper forward continues (1 lot per strategy)
- All three run the same strategy set with different sizing

### What's Being Proven
- Volatility-targeted sizing produces correct position sizes
- DD halt logic fires correctly (5% tier reduction, 8% emergency halt)
- Multi-contract execution is viable (larger position sizes on micros)
- Reporting pipeline works (daily NAV, monthly letter)
- Cash-specific concentration limits (notional-based) produce correct alerts
- The portfolio behaves differently at scale (larger positions may
  move markets on illiquid micros — test for market impact)

### What Changes From Prop
- Sizing engine: `contracts = risk_budget / (ATR × point_value × SL_mult)`
- DD management: automated tier reduction at 5%, emergency halt at 8%
- Concentration: notional-based limits (20% per asset, 35% per factor)
- Reporting: daily NAV calculation, monthly letter template
- Correlation cap tightened to 0.25

### What Continues In Parallel
- **Paper forward (1 lot)** — permanent ground truth
- **Live prop (1 lot)** — real capital baseline
- **Cash paper (vol-targeted)** — testing cash mechanics
- All three share the same strategy set. Divergence between them is
  tracked and investigated.

### Key Metrics Tracked
- Cash paper Sharpe vs prop live Sharpe (should be similar or better due to sizing)
- DD halt accuracy: did the 5% and 8% triggers fire at the right times?
- Position sizing accuracy: did computed contract sizes match expectations?
- NAV calculation accuracy: does daily NAV match manual spot-check?
- Monthly letter quality: is the report useful and complete?
- Market impact: on illiquid micros, do larger sizes degrade fill quality?

### Gate to Stage 4

**ALL must be true:**

| # | Gate | Threshold | Why |
|---|------|-----------|-----|
| 1 | Cash paper duration | **6+ months** | Full regime exposure at cash sizing |
| 2 | Cash paper Sharpe | **> 0.5** (trailing 6 months) | Vol-targeted sizing should improve Sharpe vs fixed-lot |
| 3 | Cash paper max DD | **< 10%** | DD limits must work as designed |
| 4 | DD halt tested | At least 1 tier-reduction event observed and handled correctly | Can't trust a DD halt that's never fired |
| 5 | Reporting pipeline | Monthly letter produced for 6 consecutive months | Reporting must be automatic and reliable |
| 6 | Live prop Sharpe | Still **> 0.3** during cash paper period | Prop baseline hasn't degraded while testing cash |
| 7 | Factor coverage | **3+ factors in core** | Institutional-grade diversification |
| 8 | Legal/compliance | Entity structure and account setup complete | Can't deploy real cash without legal framework |
| 9 | Personal conviction | **You believe this is ready** | Same as Stage 2 — no gate replaces judgment |

### Blocking Conditions
- Cash paper DD > 10% (the limit was supposed to prevent this — if it didn't, the halt logic is broken)
- Live prop diverges materially from paper during the cash paper period
- Reporting pipeline misses a month or produces incorrect NAV
- Market impact is material (> 3 ticks average on larger sizes)

---

## Stage 4: Small Real-Cash Pilot

*First real external or scaled personal capital deployment.*

### What's Running
- **NEW: Real cash account** ($200-500K, vol-targeted sizing, live orders)
- Live prop continues (baseline)
- Paper forward continues (ground truth)
- Cash paper may be retired or kept as a shadow book

### What's Being Proven
- Everything from Stage 3, but with real money and real fills
- Cash-to-paper divergence is small
- DD limits work under real market stress
- The system operates at this scale without degradation
- Reporting is investor-grade (even if the only investor is you for now)

### Scale Progression Within Stage 4

| Phase | Capital | Duration | Gate to Next |
|-------|---------|----------|--------------|
| 4a: Pilot | $200-500K | 6 months | Sharpe > 0.5, DD < 10%, zero system failures |
| 4b: Scale | $500K-2M | 12 months | Consistent, auditable track record |
| 4c: External (optional) | $2M+ | Indefinite | Business decision, legal, regulatory |

---

## Parallel Running Summary

| Component | Stage 1 | Stage 2 | Stage 3 | Stage 4 |
|-----------|---------|---------|---------|---------|
| Paper forward (1 lot) | **RUN** | **RUN** | **RUN** | **RUN** |
| Live prop (1 lot) | — | **RUN** | **RUN** | **RUN** |
| Cash paper (vol-target) | — | — | **RUN** | Optional |
| Real cash (vol-target) | — | — | — | **RUN** |
| Discovery engine | **RUN** | **RUN** | **RUN** | **RUN** |
| All automation | **RUN** | **RUN** | **RUN** | **RUN** |
| Master Brief | **RUN** | + live section | + cash section | + cash section |

Paper forward never stops. It is the permanent control group that
proves the system still works even if live execution has issues.

---

## What Blocks Progression at Every Stage

These are universal blockers — if any are true, do not advance:

1. **Forward evidence is insufficient.** If you haven't accumulated
   enough trades to be statistically confident, wait. Time is cheap;
   bad deployment decisions are expensive.

2. **The elite standard has been compromised.** If strategies were
   promoted despite weak rubric scores, or governance was bypassed,
   the track record is unreliable. Fix the process before scaling.

3. **Automation is unreliable.** If jobs are failing, logs are missing,
   or the brief isn't updating, the system isn't ready for larger
   stakes. Reliability at $50K is non-negotiable for reliability at $500K.

4. **You're not confident.** Every gate includes "personal conviction"
   because no metric fully captures readiness. If the numbers pass but
   you're not sure, the right answer is to wait. The system improves
   every week it runs. There is no penalty for patience.
