# FQL Cash-Account Deployment Roadmap

*How FQL transitions from prop-first to cash-account deployment.*
*This is Layer C of the portfolio construction policy, fully specified.*
*Effective: When prerequisites are met. Not active until then.*

---

## Principle

The prop account proves the system works. The cash account scales what
works. Nothing deploys to cash that hasn't earned its place in prop first.
The research engine, governance, and elite standard are universal — they
don't change. What changes is sizing, risk limits, reporting, and
execution infrastructure.

---

## 1. What Stays Universal (Layer A → Cash)

These carry over unchanged from the prop deployment:

| Component | Status in Cash |
|-----------|---------------|
| Factor diversification (6 factors, weighting, caps) | Unchanged |
| Asset diversification (classes, gap targeting) | Unchanged |
| Session diversification (overlap rules) | Unchanged |
| Portfolio role taxonomy (6 roles, replacement rules) | Unchanged |
| Elite Review Rubric (6 questions, scoring, displacement) | Unchanged |
| Strategy Lifecycle Policy (7 stages, all gates) | Unchanged |
| Add vs replace framework | Unchanged |
| Portfolio-level warning triggers (14) | Unchanged |
| Continuous discovery engine (Claw + Claude loop) | Unchanged |
| Carry lookup, vitality monitor, scoreboard, counterfactual | Unchanged |
| Elite standard principle | Unchanged |
| Family closure rules, salvage limits, one-retry rule | Unchanged |
| Forward evidence > backtest at every decision | Unchanged |

**The entire research and governance stack transfers.** Cash deployment
is a configuration change, not a system rewrite.

---

## 2. What Changes Under Cash Overlay (Layer C)

### 2a. Position Sizing

| Dimension | Prop (Layer B) | Cash (Layer C) |
|-----------|---------------|----------------|
| **Sizing method** | Fixed 1 micro contract per strategy | Volatility-targeted per strategy |
| **Base unit** | 1 contract | Dollar risk budget per strategy |
| **Scaling formula** | None (always 1 lot) | `contracts = risk_budget / (ATR × point_value × SL_mult)` |
| **Tier meaning** | Priority ordering only (all 1 lot) | Actual capital allocation: MICRO=0.5%, REDUCED=1%, BASE=2%, BOOST=3% of AUM |
| **Rebalancing** | None | Monthly or after significant AUM change (>10%) |

**Tier-to-allocation mapping (cash):**

| Tier | % of AUM | At $500K | At $2M |
|------|----------|----------|--------|
| OFF | 0% | $0 | $0 |
| MICRO | 0.5% | $2,500 | $10,000 |
| REDUCED | 1.0% | $5,000 | $20,000 |
| BASE | 2.0% | $10,000 | $40,000 |
| BOOST | 3.0% | $15,000 | $60,000 |
| MAX_ALLOWED | 5.0% | $25,000 | $100,000 |

Total portfolio risk budget: 20-30% of AUM across all strategies.
Remaining capital is margin reserve and cash buffer.

### 2b. Drawdown Tolerance

| Dimension | Prop (Layer B) | Cash (Layer C) |
|-----------|---------------|----------------|
| **Portfolio max DD** | Personal tolerance (~15-20%) | **10% hard limit** |
| **Strategy max DD** | $5K remove trigger | **2% of AUM** per strategy |
| **Rolling DD gate** | None | If portfolio DD > 5%, reduce all tiers by 1 |
| **Emergency halt** | Kill switch (manual) | **Automated halt at 8% DD**, manual review required to resume |
| **Recovery protocol** | Resume when comfortable | Resume at reduced tiers (all at MICRO) until DD < 3%, then rebuild |

### 2c. Portfolio Construction (Tightened)

| Dimension | Prop (Layer B) | Cash (Layer C) |
|-----------|---------------|----------------|
| **Factor hard cap** | 50% | **35%** |
| **Factor soft cap** | 40% | **30%** |
| **Correlation hard cap** | 0.35 | **0.25** |
| **Session hard cap** | 5 per session | **4 per session** |
| **Asset hard cap** | 5 per asset | **By notional: max 20% of AUM on one asset** |
| **Direction ratio** | 3:1 hard | **2:1 hard** |
| **Core cap** | 10 | **12** (larger capital base supports more strategies) |
| **Conviction cap** | 5 | **6** |
| **Minimum factor coverage** | No minimum | **At least 3 of 6 factors represented in core** |

### 2d. Concentration Rules (Notional-Based)

In prop, concentration is measured by strategy count (max 5 per asset).
In cash, it's measured by capital allocation:

| Dimension | Cash Limit |
|-----------|-----------|
| Single asset | Max 20% of AUM |
| Single asset class | Max 40% of AUM |
| Single factor | Max 35% of risk-weighted exposure |
| Single session | Max 30% of risk-weighted exposure |
| Single strategy | Max 5% of AUM (MAX_ALLOWED tier) |
| Gross exposure | Max 150% of AUM (moderate leverage OK) |
| Net directional | Max 80% of AUM (can't be all-in one direction) |

### 2e. Reporting

| Report | Prop (Layer B) | Cash (Layer C) |
|--------|---------------|----------------|
| **Daily** | Master Operating Brief (internal) | Daily NAV report + brief |
| **Weekly** | Friday scorecard | Weekly performance letter |
| **Monthly** | Operating dashboard | **Formal monthly letter**: NAV, attribution, factor exposure, DD, benchmark comparison |
| **Quarterly** | Genome map refresh | Quarterly review: strategy-level attribution, factor rotation, risk budget utilization |
| **Annual** | Changelog | Annual report: full-year attribution, Sharpe, benchmark, strategy lifecycle summary |

**NAV calculation:** Mark-to-market at 17:00 ET daily. Include unrealized
PnL on open positions. Subtract commissions and slippage at actuals.

**Benchmark:** CTA index (SG CTA Index or similar). NOT S&P 500 — FQL is
a systematic futures program, not an equity portfolio.

### 2f. Execution and Safety

| Dimension | Prop (Layer B) | Cash (Layer C) |
|-----------|---------------|----------------|
| **Execution** | Manual start, automated downstream | **Fully automated** with human override |
| **Forward runner** | Manual trigger (start_forward_day.sh) | **Scheduled launchd agent**, fires at RTH open |
| **Order routing** | Not implemented (paper trading) | **Live broker API** (Interactive Brokers or similar) |
| **Pre-trade checks** | None (paper) | **Margin check, position limit check, fat-finger protection** |
| **Reconciliation** | None | **Daily reconciliation** of positions vs expected state |
| **Disaster recovery** | Git history | **Automated state backup**, position snapshot to cloud, rollback capability |
| **Monitoring** | Automation health (scripts/automation_health.py) | **24/7 heartbeat** with alerting (SMS/email on failure) |

---

## 3. Prerequisites Before Cash Deployment

### Hard Prerequisites (ALL must be true)

| # | Prerequisite | Why It Matters | How to Verify |
|---|-------------|----------------|---------------|
| 1 | **12+ months of continuous prop forward evidence** | Proves the system works across multiple regimes, not just one favorable period. | `state/account_state.json` run_count, date range |
| 2 | **At least 3 core strategies promoted with forward PF > 1.2** | Proves the lifecycle pipeline works end-to-end: discovery → testing → validation → probation → promotion. | Registry: count status=core with forward evidence |
| 3 | **Factor coverage: at least 3 of 6 factors in core** | Proves the portfolio isn't a disguised single-factor bet. Currently 1 (MOMENTUM). Need CARRY and/or VOL to join. | Registry: unique factors in core strategies |
| 4 | **Prop portfolio Sharpe > 0.5 over trailing 12 months** | Bare minimum risk-adjusted return to justify managing capital. Below 0.5 is not worth the operational complexity. | Forward equity curve Sharpe calculation |
| 5 | **Max DD < 15% in the trailing 12 months** | Proves drawdown control works before applying tighter cash limits. | Forward equity curve max drawdown |
| 6 | **Automation health HEALTHY for 30+ consecutive days** | Proves the system runs reliably without manual intervention. | `scripts/automation_health.py` history |
| 7 | **All governance docs current and consistent** | The system must be documented well enough that someone else could operate it. | Manual review of all docs/ files |
| 8 | **Legal/compliance framework in place** | If accepting external capital: entity structure, investor agreements, regulatory compliance. If personal capital only: tax structure, account setup. | Legal counsel sign-off |

### Soft Prerequisites (Recommended but not blocking)

| # | Prerequisite | Why It Matters |
|---|-------------|----------------|
| 9 | 5+ core strategies promoted | More strategies = more diversification = lower DD |
| 10 | CARRY or RATES factor in core | Genuinely uncorrelated to equity momentum |
| 11 | Automated execution pipeline tested in paper | Don't go live with untested order routing |
| 12 | VolManaged-EquityIndex overlay tested | Vol-managed sizing is the natural Layer C sizing mechanism |
| 13 | Monthly reporting template built and tested | Don't discover reporting gaps after capital is deployed |

---

## 4. Staged Rollout Path

### Stage 0: Current (Prop-First, Layer B Active)

```
Capital: $50K prop account
Strategies: 4 core + 5 conviction + 5 watch
Sizing: 1 micro contract per strategy
Execution: Manual forward runner
Reporting: Master Operating Brief (internal)
Status: ACTIVE
```

### Stage 1: Prop Scale-Up (Layer B Enhanced)

**When:** After 3+ core promotions and 12+ months forward evidence.
**What changes:** Increase prop capital to $100-200K. Begin trading
multiple contracts on BOOST-tier strategies. Test position sizing
logic in prop before deploying to cash.

```
Capital: $100-200K prop account
Strategies: 6-8 core, 3+ factors
Sizing: 1-3 micro contracts by tier
Execution: Still manual start, but sizing now matters
Reporting: Internal + monthly self-review
Status: PREREQUISITE CHECK
```

### Stage 2: Cash Pilot (Layer C Activated, Small Scale)

**When:** All 8 hard prerequisites met. Personal capital only (no
external investors yet). Small allocation to test Layer C mechanics.

```
Capital: $200-500K (personal cash account)
Strategies: Same as prop (identical strategy set, different sizing)
Sizing: Volatility-targeted, 20% of AUM risk budget
Execution: Automated forward runner (scheduled launchd)
Reporting: Daily NAV, weekly letter, monthly formal report
Monitoring: 24/7 heartbeat with SMS alerting
DD limits: 10% hard halt, 5% tier reduction
Status: PILOT
```

**Prop account continues running in parallel.** The cash account mirrors
the prop strategy set with volatility-targeted sizing. Discrepancies
between prop and cash performance are tracked and investigated.

### Stage 3: Cash Steady-State (Layer C Full)

**When:** Cash pilot runs for 6+ months with DD < 10%, Sharpe > 0.5,
and no automation failures requiring manual intervention.

```
Capital: $500K-2M (personal or small external)
Strategies: Full core + conviction set
Sizing: Full volatility-targeted across all tiers
Execution: Fully automated with human override
Reporting: Investor-grade (daily NAV, monthly letter, quarterly review)
Monitoring: 24/7 with automated failover
DD limits: 10% hard halt, automated recovery protocol
Status: OPERATIONAL
```

### Stage 4: External Capital (Optional, Future)

**When:** 24+ months of cash steady-state with auditable track record.
Business decision, not a technical trigger.

```
Capital: $2M+ (external investors)
Structure: LLC or LP fund vehicle
Compliance: Regulatory filing, investor agreements, audit
Reporting: Audited annual, quarterly investor letter, monthly factsheet
Fees: Management + performance (standard 1/10 or 1.5/15)
Status: FUTURE CONSIDERATION
```

---

## 5. Transition Checklist

### Layer B → Stage 1 (Prop Scale-Up)

- [ ] 3+ core strategies promoted with forward PF > 1.2
- [ ] 12+ months continuous forward evidence
- [ ] Portfolio Sharpe > 0.5 trailing 12 months
- [ ] Max DD < 15% trailing 12 months
- [ ] Increase prop capital to $100-200K
- [ ] Test multi-contract sizing on BOOST strategies
- [ ] Verify margin requirements at higher size

### Stage 1 → Stage 2 (Cash Pilot)

- [ ] All 8 hard prerequisites met
- [ ] Volatility-targeted sizing logic built and tested in prop
- [ ] Automated forward runner scheduled and tested (2+ weeks paper)
- [ ] Daily NAV calculation implemented
- [ ] DD halt logic implemented (8% emergency, 5% tier reduction)
- [ ] Pre-trade checks implemented (margin, position limits)
- [ ] Daily reconciliation implemented
- [ ] Monthly report template built
- [ ] Cash account opened and funded
- [ ] Prop + cash run in parallel for 1+ month before cash goes live

### Stage 2 → Stage 3 (Cash Steady-State)

- [ ] Cash pilot: 6+ months operational
- [ ] Cash DD < 10% throughout pilot
- [ ] Cash Sharpe > 0.5 during pilot
- [ ] No automation failures requiring manual intervention
- [ ] Reporting pipeline fully tested (daily, weekly, monthly, quarterly)
- [ ] Disaster recovery tested (state backup, position snapshot, rollback)

### Stage 3 → Stage 4 (External Capital — Optional)

- [ ] 24+ months auditable cash track record
- [ ] Legal entity established
- [ ] Regulatory compliance confirmed
- [ ] Investor agreements drafted
- [ ] Third-party audit of track record
- [ ] Fee structure defined
- [ ] Marketing materials (factsheet, pitch deck)
- [ ] Strategic decision: is this the right path for FISH?

---

## 6. What Does NOT Change at Any Stage

- The research engine runs continuously at every stage
- The elite standard applies to every decision at every stage
- Discovery is relentless, deployment is selective — always
- Forward evidence outranks backtest at every decision
- The replacement scoreboard, counterfactual, and vitality monitor
  run at every stage
- No strategy enters live trading without completing the full lifecycle
- The portfolio construction policy (Layer A) is permanent
- The prop account (Layer B) continues running even after cash deploys
