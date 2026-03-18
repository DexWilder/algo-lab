# FQL Blocked-Unlock Roadmap & Research Capital Allocation Policy

*Framework for deciding which data buys, engineering upgrades, and
infrastructure unlocks are worth doing and in what order.*
*Effective: 2026-03-18*

---

## Principle

Every dollar and hour spent on infrastructure competes with discovery
and forward evidence collection. An unlock is justified only when it
unblocks ideas that the portfolio actually needs — not because the
infrastructure would be nice to have. The catalog tells you what's
blocked. The portfolio construction policy tells you what's needed.
This document connects the two.

---

## 1. Unlock Types

| Type | What It Is | Examples | Typical Cost | Typical Time |
|------|-----------|----------|-------------|-------------|
| **DATA** | Acquiring new market data or extending history | Rates backfill ($12.59), FX depth ($3.97), OVX proxy, auction imbalance feed | $3-50 per asset | Hours to days |
| **ENGINEERING** | Building new code infrastructure | Carry lookup table, CTD mapping, curve hedging engine, spread trading, vol-targeting sizing model | $0 (time only) | Days to weeks |
| **INFRASTRUCTURE** | System capabilities beyond strategy code | Multi-contract roll expressions, sub-minute bar support, automated execution pipeline | $0 (time only) | Weeks |
| **EXECUTION** | Capabilities needed to trade a strategy live | Spread execution, tick-level timing, auction participation, multi-leg entry | $0 (time only) | Days to weeks |
| **ANALYTICS** | Tooling that improves research quality | True term-structure decomposition, carry/momentum signal separation, regime classification upgrades | $0 (time only) | Days |

---

## 2. Ranking by Research Leverage

Research leverage = how many blocked ideas does this unlock, weighted by
the quality and priority of those ideas.

### Leverage Score Formula

```
Leverage = Σ (idea_priority_weight × factor_gap_weight)
           for each idea unblocked by this unlock

idea_priority_weight:
  testable_now (after unlock) = 3
  needs_one_more_thing        = 1
  still_blocked_by_other      = 0.5

factor_gap_weight:
  Fills a factor with 0 active/probation = 3
  Fills a factor with <3 ideas           = 2
  Adds to a factor with 3+ ideas         = 1
  Adds to MOMENTUM (>50% already)        = 0.5
```

### Current Unlock Leverage Ranking

| Rank | Unlock | Type | Ideas Unblocked | Key Factors | Leverage Score |
|------|--------|------|----------------|-------------|----------------|
| **1** | Carry lookup table + tenor mapping | ENGINEERING | 4 (Treasury-Rolldown, CrossCurrency-YieldCurve, Commodity-Carry-TailRisk, ManagedFutures-Carry) | CARRY (0 active) | **~24** |
| **2** | Rates data backfill (pre-2019) | DATA | 3 directly + enables carry lookup testing (Treasury-2Y-FOMC, Treasury-Curve-Drift, Treasury-Rolldown) | CARRY, EVENT | **~18** |
| **3** | Strategy ambiguity resolution (mechanical rule definition) | ANALYTICS | 4 (TV-NFP-Price-Zones, TV-FOMC-Sweep, TV-Gap-Filling, TV-VVIX-Divergence) | EVENT, STRUCTURAL, VOL | **~12** |
| **4** | Spread trading infrastructure | ENGINEERING + EXECUTION | 3 (Treasury-Curve-Drift, Treasury-Roll-Microstructure, WTI-CMA-Roll) | STRUCTURAL, CARRY | **~10** |
| **5** | Sub-minute / tick-level bar support | INFRASTRUCTURE | 1 directly (EIA-30s-Box) + improves execution modeling | EVENT | **~4** |
| **6** | Auction imbalance data feed | DATA | 1 (Equity-Closing-Auction-Flow) | STRUCTURAL | **~4** |
| **7** | OVX proxy data pipeline | DATA | 1 (TV-Crude-OVX-Regime-Shift) | VOLATILITY | **~3** |
| **8** | CTD mapping + repo infrastructure | ENGINEERING | 1 (Treasury-CashFutures-Basis) | CARRY | **~3** |
| **9** | Vol-targeting sizing model | ENGINEERING | 1 (TV-Treasury-Macro-Vol-Targeting) | VOLATILITY | **~2** |

---

## 3. Ranking by Cost vs Option Value

An unlock has option value when it makes future research sprints possible
that are currently impossible. Cheap unlocks with high option value should
be done early. Expensive unlocks with narrow value should wait.

### Cost/Value Matrix

| | **High Option Value** (unlocks many future paths) | **Low Option Value** (unlocks one thing) |
|---|---|---|
| **Low Cost** (<$20, <1 day) | **DO NOW** — no reason to wait | **DO WHEN NEEDED** — cheap but don't rush |
| **High Cost** (>$50 or >1 week eng) | **PLAN AND SCHEDULE** — worth doing but sequence carefully | **DEFER** — only if the specific idea proves out first |

### Current Unlocks Classified

| Unlock | Cost | Option Value | Classification |
|--------|------|-------------|----------------|
| Rates data backfill (pre-2019) | ~$13 | HIGH (enables 8+ rate strategies) | **DO NOW** |
| FX data backfill (6J/6E depth) | ~$4 | MEDIUM (strengthens 2 probation strategies) | **DO WHEN NEEDED** (Week 8 review) |
| Carry lookup table | ~2 days eng | HIGH (enables entire CARRY factor) | **PLAN AND SCHEDULE** |
| Strategy ambiguity resolution | ~1 day per idea | MEDIUM (4 ideas, mixed quality) | **DO WHEN NEEDED** (pick best 1-2) |
| Spread trading infra | ~1 week eng | MEDIUM (3 ideas, all rates/energy) | **PLAN AND SCHEDULE** |
| Sub-minute bar support | ~3 days eng | LOW (1 idea directly) | **DEFER** |
| Auction imbalance feed | Unknown (vendor) | LOW (1 idea) | **DEFER** |
| OVX proxy pipeline | ~1 day eng | LOW (1 idea) | **DEFER** |
| CTD + repo infrastructure | ~2 weeks eng | LOW (1 complex idea) | **DEFER** |
| Vol-targeting model | ~3 days eng | MEDIUM (sizing overlay, not standalone) | **DEFER** (until cash-account overlay) |

---

## 4. When to Execute: Immediate vs Deferred

### Execute Immediately When ALL Are True

1. The unlock costs less than $25 or less than 2 days of engineering
2. It unblocks 3+ ideas (not just one niche strategy)
3. At least one unblocked idea fills a HIGH-priority factor or asset gap
4. The system is not in the middle of a probation review or critical
   forward evidence collection period
5. You have confirmed that the ideas being unblocked are worth testing
   (not just theoretically interesting)

### Defer When ANY Are True

1. The unlock costs more than $50 or more than 1 week of engineering
   AND the unblocked ideas haven't been validated as high-priority
2. The unlock enables only one strategy and that strategy hasn't passed
   first-pass testing yet
3. The system is in a critical forward evidence phase (e.g., Week 8 review)
   and the unlock would distract from monitoring
4. The unblocked ideas are all in the same factor that's already at or
   above the 40% concentration cap
5. A cheaper unlock would achieve 80% of the same research leverage

### Never Spend On

- Data for asset classes with no ideas in the catalog (buy data only
  after ideas exist that need it)
- Engineering infrastructure for a single strategy that hasn't been
  first-pass tested (test the proxy version first, build infra only
  if the signal shows promise)
- Execution improvements for strategies still in testing (execution
  quality matters at probation/core, not at idea/testing stage)
- Analytics upgrades that don't directly unblock catalog ideas

---

## 5. Integration with Portfolio Priorities

### Factor Gap → Unlock → Ideas → Conversion Pipeline

```
Portfolio Construction Policy (Layer A)
  identifies: CARRY factor = 0 active, 0 probation = GAP
       ↓
Harvest Config priorities
  targets: CARRY factor in discovery lanes
       ↓
Catalog accumulates CARRY ideas
  5 ideas, 4 blocked → blocker analysis
       ↓
This Roadmap
  ranks: carry lookup table = Leverage #1, $0 cost, 2 days eng
       ↓
Decision: BUILD carry lookup table
       ↓
4 CARRY ideas become testable → enter conversion queue
       ↓
Strategy Lifecycle Policy
  governs: TESTED → VALIDATION → PROBATION → CORE
```

### How Unlock Priority Maps to Portfolio Gaps

| Portfolio Gap | Highest-Leverage Unlock | Current State |
|---------------|------------------------|---------------|
| CARRY factor (0 active) | Carry lookup table | 5 ideas blocked, 1 testing (proxy) |
| Rates asset class (0 active) | Rates data backfill | 4 failures, need pre-2019 for full cycle |
| STRUCTURAL factor (1 active) | Spread trading infra | 3 ideas blocked by execution/engineering |
| EVENT factor (2 probation) | Strategy ambiguity resolution | 4 ideas blocked by unclear rules |
| Afternoon session (0 active) | No infrastructure blocker | Harvest gap, not an unlock problem |
| VOLATILITY factor (3 probation) | OVX proxy + ambiguity | 4 ideas blocked, mixed quality |

### Rule: Unlock Budget Follows Factor Gaps

When deciding between two unlocks of similar cost, choose the one that
unblocks ideas in the highest-priority factor gap. Currently:
1. CARRY unlocks > everything else (0 active, 0 probation, biggest gap)
2. STRUCTURAL unlocks > EVENT/VOL (thin coverage)
3. EVENT unlocks = VOL unlocks (both growing but not urgent)
4. MOMENTUM unlocks = lowest priority (already overcrowded at 61%)

---

## 6. Avoiding Low-Leverage Spending

### Anti-Patterns to Avoid

**"Build it and they will come"**
Don't build infrastructure hoping ideas will appear. The catalog must
already contain blocked ideas that the infrastructure would unlock.
No blocked ideas = no justification for the spend.

**"One more data source will fix it"**
If a strategy failed on existing data, more data rarely fixes it.
Only buy data when: (a) the strategy showed partial promise (SALVAGE
or MONITOR, not REJECT), or (b) the failure mode was explicitly
"insufficient sample" and more data would provide the missing regime.

**"We need this for completeness"**
Completeness is not a goal. If the carry lookup table unlocks 4 ideas
but the auction imbalance feed unlocks 1, build the lookup table first
even if the auction feed feels like a "missing piece."

**"It's cheap so why not"**
Cheap dollar cost doesn't mean cheap attention cost. Every unlock
creates work: data validation, pipeline testing, strategy re-testing,
registry updates. Budget attention, not just money.

**"The engineering would be fun"**
Engineering is not the bottleneck. Forward evidence is. Build only what
the catalog demands, when the catalog demands it.

### Spending Discipline Rules

1. **Max 1 active unlock at a time.** Finish one before starting the next.
   Parallel unlocks split attention and delay everything.
2. **Log the expected leverage before starting.** Write down: "This unlock
   will make strategies X, Y, Z testable. Their factors are A, B.
   Expected portfolio value: [HIGH/MEDIUM/LOW]." If you can't write this
   sentence, don't start the unlock.
3. **Verify within 2 weeks.** After completing an unlock, at least one of
   the unblocked ideas should enter testing within 2 weeks. If not, the
   unlock was lower-leverage than expected — log the lesson.
4. **No unlock during Week 6-8 probation reviews.** Focus on forward
   evidence, not infrastructure, during critical review windows.
5. **Quarterly unlock budget review.** Every quarter, assess: What did we
   spend? What did it unlock? Was the leverage real? Adjust priorities.

---

## 7. Current Recommended Sequence

Based on the scoring above and the current portfolio state:

### Phase 1: Now (Prop Phase, Pre-Week 8 Review)

| Priority | Unlock | Type | Cost | Unblocks | Status |
|----------|--------|------|------|----------|--------|
| **1** | Rates data backfill (pre-2019) | DATA | ~$13 | 3 rate strategies + carry testing | **READY** — execute when probation isn't in critical window |

### Phase 2: Post-Week 8 Review

| Priority | Unlock | Type | Cost | Unblocks |
|----------|--------|------|------|----------|
| **2** | Carry lookup table | ENGINEERING | ~2 days | 4 CARRY ideas → testable |
| **3** | FX data backfill (6J/6E depth) | DATA | ~$4 | Strengthens 2 probation strategies |
| **4** | Top 2 ambiguity resolutions | ANALYTICS | ~1 day each | 2 best EVENT/VOL ideas |

### Phase 3: After First Core Promotions

| Priority | Unlock | Type | Cost | Unblocks |
|----------|--------|------|------|----------|
| **5** | Spread trading infrastructure | ENGINEERING | ~1 week | 3 rates/energy structural ideas |
| **6** | OVX proxy pipeline | DATA | ~1 day | 1 VOL idea (MCL regime) |

### Phase 4: Defer Until Justified

| Unlock | Why Deferred |
|--------|-------------|
| Sub-minute bar support | Only 1 idea needs it; test 5m proxy first |
| Auction imbalance feed | Only 1 idea; vendor cost unknown; test proxy first |
| CTD + repo infrastructure | 1 complex idea; 2+ weeks eng; too heavy for current phase |
| Vol-targeting sizing model | Sizing overlay, not standalone; wait for cash-account phase |

---

## 8. Blocked Idea Inventory (Current State)

### By Blocker Type

| Blocker | Count | Key Ideas |
|---------|-------|-----------|
| `blocked_by_data` | 6 | Treasury-2Y-FOMC, FX-Carry, CrossCurrency-YieldCurve, FX-PPP-Value, Equity-Closing-Auction, Gold-Overnight-Drift |
| `blocked_by_engineering` | 4 | Treasury-Curve-Drift, Treasury-CashFutures-Basis, Treasury-Macro-Vol-Targeting, Treasury-Rolldown-Carry |
| `blocked_by_strategy_ambiguity` | 4 | TV-NFP-Price-Zones, TV-Gap-Filling, TV-VVIX-Divergence, Commodity-Carry-TailRisk |
| `blocked_by_execution` | 3 | EIA-30s-Box, Treasury-Roll-Microstructure, WTI-CMA-Roll |
| `blocked_by_sample_size` | 2 | CPI-Reaction-Bias, CrudeOil-OPEC-Announcement |
| `blocked_by_proxy_data` | 1 | TV-Crude-OVX-Regime-Shift |
| `blocked_by_discretion` | 1 | TV-FOMC-Sweep-Reaction |
| `blocked_by_tail_risk` | 1 | TV-VIX-Term-Structure-Hedge |
| `blocked_by_source_translation` | 1 | Gold-Overnight-Drift |
| `blocked_by_instrument_definition` | 1 | WTI-CMA-Roll-Structure |
| `blocked_by_data_pipeline` | 1 | Treasury-Rolldown-Carry-Spread |

### By Factor (blocked ideas)

| Factor | Blocked | Notes |
|--------|---------|-------|
| CARRY | 5 | Biggest cluster — carry lookup + rates data would unblock most |
| EVENT | 4 | Mixed: sample size, ambiguity, execution |
| STRUCTURAL | 4 | Spread trading + auction data needed |
| VOLATILITY | 4 | Ambiguity + proxy data |

---

## Appendix: Decision Template

Before approving any unlock, fill this out:

```
Unlock: ___________________
Type: DATA / ENGINEERING / INFRASTRUCTURE / EXECUTION / ANALYTICS
Cost: $_____ / _____ days of engineering
Ideas unblocked: [list strategy IDs]
Factors filled: [list factors]
Highest-priority idea: ___________________
Expected leverage score: _____
Portfolio gap addressed: ___________________
Current phase compatibility: YES / NO (why?)
Approved: YES / NO
Date: ___________
```
