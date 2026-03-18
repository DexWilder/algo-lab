# FQL Deployment Sequence

*Concrete rollout from paper forward through real-cash pilot.*
*Every stage has a purpose, a gate, and a parallel requirement.*
*Effective: 2026-03-18*

---

## Sequence Overview

```
STAGE 1:  Paper Forward (ACTIVE NOW)
    ↓ gate
STAGE 2:  Small Live Prop (1 account, 3-5 core strategies, $10-25K)
    ↓ gate (paper continues)
STAGE 3A: Cash Paper — Small ($50-100K simulated, validate mechanics)
    ↓ gate (prop live + paper continue)
STAGE 3B: Cash Paper — Full ($200-500K simulated, validate scale)
    ↓ gate (prop live + paper continue)
STAGE 4:  Small Real-Cash Pilot ($200-500K real)
    (all prior stages continue in parallel)
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

*Smallest real prop footprint that meaningfully tests execution.
This is NOT scaling. This is operational proof.*

### Scope

- **1 account, $10-25K, micro contracts, 1 lot per strategy**
- Deploy only strategies that have been promoted to core with forward
  evidence. Not the full strategy set — the proven subset.
- Likely 3-5 strategies live, not 10+. The rest stay paper-only.
- Purpose: test execution plumbing, fill quality, discipline, and
  paper-to-live divergence. NOT to maximize PnL or prove the portfolio.

### What's Running
- **NEW: Live prop account** (1 account, $10-25K, 3-5 core strategies only)
- Paper forward continues in parallel (full strategy set, unchanged)
- All automated pipelines unchanged
- Discovery loop unchanged

### What's Being Proven
- Real fills match paper fills within expected slippage
- Real commissions match estimates
- The forward runner operates correctly in live mode
- Broker API integration works end-to-end (order routing, confirmation, reconciliation)
- Psychological discipline holds (no manual overrides outside governance)
- Paper-to-live divergence is small and explainable on the live subset

### What Is NOT Being Proven Yet
- Full portfolio performance at scale
- Multi-contract sizing
- DD halt logic (that's Stage 3)
- Cash-account reporting

### What Changes From Paper
- `FORWARD_ENABLED=true` in forward runner config for the live subset
- Orders route to broker API (Interactive Brokers or equivalent)
- Pre-trade checks activated (margin, position limits, fat-finger guard)
- Daily reconciliation: compare live fills vs paper signals for the same strategies
- Real money on the line — governance discipline is tested for real

### Strategy Selection for Live
Deploy only strategies that meet ALL of:
- Status = core (promoted through full lifecycle)
- Forward PF > 1.2 on paper
- Rubric score >= 18
- No active kill flags or decay signals

The remaining strategies (conviction, watch, testing) stay paper-only
and continue accumulating evidence.

### What Continues In Parallel
- **Paper forward runs the full set.** Same strategies, same signals,
  same timing. The live subset should match paper exactly for those
  strategies. Divergence > 5% of PnL per month is investigated.
- All automation, discovery, scoreboard, vitality monitor unchanged.
- Master Operating Brief adds a "Live vs Paper" comparison section
  for the live subset only.

### Key Metrics Tracked
- Live PnL vs paper PnL for the live subset (should be within 5%)
- Slippage: actual vs estimated (should be < 2 ticks average)
- Commission: actual vs estimated
- Fill rate: % of signals that execute successfully (target 100%)
- Live max DD (tracked against paper DD for divergence)
- Psychological log: any manual overrides or interventions documented
- Broker uptime: any API failures or missed signals

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

## Stage 3A: Cash Paper — Small Scale

*Validate the cash overlay mechanics at a comfortable scale before
testing them at full size.*

### Scope

- **Simulated $50-100K with vol-targeted sizing**
- Same strategy set as live prop (core + conviction)
- Position sizes will be 1-3 micro contracts per strategy (similar
  to prop, but computed by the sizing engine rather than fixed)
- Purpose: prove the sizing engine, DD logic, and NAV calculation
  work correctly — before scaling up introduces market impact risk

### What's Running
- **NEW: Cash paper account** (simulated $50-100K, vol-targeted sizing)
- Live prop continues ($10-25K, 1 lot, proven subset)
- Paper forward continues (full set, 1 lot)

### What's Being Proven
- Volatility-targeted sizing engine produces correct contract counts
- DD tier-reduction logic fires at 5% and recovers correctly
- DD emergency halt fires at 8%
- Daily NAV calculation matches manual spot-check
- Cash paper PnL tracks prop live PnL closely (same strategies,
  similar sizing at this scale — divergence means a sizing bug)
- Notional concentration limits (20% per asset, 35% per factor)
  produce correct alerts

### What Changes From Prop
- Sizing: `contracts = risk_budget / (ATR × point_value × SL_mult)`
- DD management: automated tier reduction at 5%, halt at 8%
- Concentration: notional-based instead of count-based
- NAV: daily mark-to-market calculation
- Correlation cap tightened to 0.25

### Key Metrics Tracked
- Sizing accuracy: computed contracts vs expected (should be exact)
- DD halt accuracy: did triggers fire at correct levels?
- Cash-prop divergence: PnL difference per strategy (should be < 10%)
- NAV accuracy: computed vs manual spot-check (should be < 0.1% error)

### Gate to Stage 3B

| # | Gate | Threshold | Why |
|---|------|-----------|-----|
| 1 | Duration | **3+ months** | Enough time to observe at least one vol regime shift |
| 2 | Sizing accuracy | **Zero incorrect computations** | Sizing bugs are catastrophic with real money |
| 3 | DD halt tested | **At least 1 tier-reduction event** observed and handled correctly | Can't trust untested halt logic |
| 4 | Cash-prop divergence | **< 10%** cumulative PnL difference | Proves the sizing engine doesn't introduce unexpected behavior |
| 5 | NAV accuracy | **100% of daily NAV calculations correct** to within 0.1% | NAV errors compound and erode trust |

### Blocking Conditions
- Any sizing computation error (wrong contract count)
- DD halt fails to fire when threshold is crossed
- Cash paper DD > 10% (halt should have prevented this)
- NAV calculation error > 0.5% on any day

---

## Stage 3B: Cash Paper — Full Scale

*Test vol-targeted sizing at the capital scale where market impact
and multi-contract execution become real considerations.*

### Scope

- **Simulated $200-500K with vol-targeted sizing**
- Position sizes will be 3-10+ contracts on some strategies
- At this scale, market impact on illiquid micros (MCL, M2K) becomes
  a factor. The paper simulation won't capture this perfectly, but
  sizing and concentration limits can be validated.
- Reporting pipeline (monthly letter, quarterly review) activated

### What's Running
- **SCALED: Cash paper account** ($200-500K, vol-targeted)
- Live prop continues (baseline)
- Paper forward continues (ground truth)

### What's Being Proven
- Multi-contract positions don't create unrealistic concentration
- Larger sizes on illiquid micros (MCL, M2K) would be executable
  (check average daily volume vs computed position size)
- Monthly reporting template produces a useful, complete letter
- The portfolio behaves as expected at this capital level
- Gross exposure stays within 150% of AUM limit
- Net directional stays within 80% of AUM limit

### Key Metrics Tracked
- Cash paper Sharpe vs prop Sharpe (should be similar or better)
- Position size vs average daily volume per asset (flag if > 1% of ADV)
- Monthly letter: produced on schedule, accurate, useful
- Gross and net exposure levels vs limits
- DD halt behavior at larger PnL swings

### Gate to Stage 4

**ALL must be true:**

| # | Gate | Threshold | Why |
|---|------|-----------|-----|
| 1 | Stage 3B duration | **6+ months** | Full regime exposure at scale |
| 2 | Cash paper Sharpe | **> 0.5** (trailing 6 months) | Vol-targeted sizing should improve Sharpe vs fixed-lot |
| 3 | Cash paper max DD | **< 10%** | DD limits must work at scale |
| 4 | Reporting pipeline | **6 consecutive monthly letters** produced | Reporting is automatic and reliable |
| 5 | Live prop Sharpe | Still **> 0.3** during this period | Prop baseline hasn't degraded |
| 6 | Factor coverage | **3+ factors in core** | Institutional-grade diversification |
| 7 | Market impact check | **No asset requires > 2% of ADV** | Positions must be executable without moving the market |
| 8 | Legal/compliance | Entity and account structure complete | Required before real capital |
| 9 | Personal conviction | **You believe this is ready** | No gate replaces judgment |

### Blocking Conditions
- Cash paper DD > 10% (halt logic failure at scale)
- Any asset requires > 5% of ADV (position too large for the market)
- Reporting pipeline misses a month or produces materially incorrect NAV
- Live prop diverges materially from paper during this period

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

| Component | Stage 1 | Stage 2 | Stage 3A | Stage 3B | Stage 4 |
|-----------|---------|---------|----------|----------|---------|
| Paper forward (1 lot, full set) | **RUN** | **RUN** | **RUN** | **RUN** | **RUN** |
| Live prop (1 lot, proven subset) | — | **RUN** | **RUN** | **RUN** | **RUN** |
| Cash paper small ($50-100K) | — | — | **RUN** | Retired | — |
| Cash paper full ($200-500K) | — | — | — | **RUN** | Optional |
| Real cash ($200-500K+) | — | — | — | — | **RUN** |
| Discovery engine | **RUN** | **RUN** | **RUN** | **RUN** | **RUN** |
| All automation | **RUN** | **RUN** | **RUN** | **RUN** | **RUN** |
| Master Brief | **RUN** | + live section | + cash section | + scale section | + cash section |

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
