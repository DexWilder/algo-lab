# Elite Robustness Upgrades — Top 3 Highest-Leverage Improvements
## 2026-03-18

---

## 1. Replacement Scoreboard (Challenger vs Incumbent Board)

### Why It Matters

The displacement check is currently a manual process — Claude runs it
per-candidate when asked. But the elite standard demands that competitive
pressure is always visible. A live scoreboard that continuously tracks
every active strategy's rubric score, displacement vulnerability, and
challenger pipeline would make portfolio quality legible at a glance.

Without this, weak incumbents linger because nobody re-scored them this
week. With this, every Friday scorecard shows who's strongest, who's
weakest, and who's next in line.

### What It Would Measure

For every active strategy (core + conviction + watch):
- **Current rubric score** (cached from last review, refreshable on demand)
- **Displacement pressure:** is there a testing/idea candidate that would
  score higher + fill a gap this incumbent doesn't?
- **Survival probability:** based on forward evidence trajectory, is this
  strategy trending toward promote, continue, or expire?
- **Deadline countdown:** days remaining until watch expiry or probation
  checkpoint

For every testing-stage candidate:
- **Rubric estimate** (based on first-pass metrics)
- **Which incumbent it would challenge** (auto-computed from asset/factor/session overlap)
- **Gap bonus** (auto-computed from current concentration state)

### What Files/Modules It Would Touch

| Component | Action |
|-----------|--------|
| **NEW: `research/replacement_scoreboard.py`** | Core module. Reads registry, computes scores, outputs board. |
| `research/data/strategy_registry.json` | Reads rubric scores, status, tags, deadlines |
| `research/data/strategy_genome_map.json` | Reads concentration state for gap bonus |
| `docs/ELITE_REVIEW_RUBRIC.md` | Source of scoring criteria (reference, not modified) |
| `research/weekly_scorecard.py` | Add scoreboard section to Friday output |
| `scripts/claw_control_loop.py` | Add displacement pressure to directives (optional) |

### Minimal v1

A single Python script that:

1. Loads every core/conviction/watch strategy from the registry
2. Loads or computes each one's rubric score (from cached `rubric_score`
   field, or estimates from available metrics if not cached)
3. Sorts by score, flags the bottom of each bucket
4. Loads every testing-stage strategy, estimates rubric score
5. For each testing candidate, identifies which incumbent it would
   challenge (match on asset/factor/session, compare scores)
6. Outputs a ranked board:

```
CORE VULNERABILITY          Score  Pressure  Challenger
PB-MGC-Short                  16   HIGH      Treasury-Rolldown (18+gap)

CONVICTION (sorted by score)  Score  Deadline   Status
PreFOMC-Drift-Equity           22    Week 8     ELITE — safe
DailyTrend-MGC-Long            21    Week 8     ELITE — safe
MomPB-6J-Long-US               19    Week 8     STRONG — safe
NoiseBoundary-MNQ-Long         18    Week 8     STRONG — at threshold
TV-NFP-High-Low-Levels         18    Week 8     STRONG — at threshold

WATCH (sorted by score)       Score  Deadline   Survive?
FXBreak-6J-Short-London        17    Jun 01     Needs fwd PF > 1.2
TTMSqueeze-M2K-Short           17    Jun 01     Needs fwd PF > 1.3
GapMom                         16    Jun 01     Unlikely (MGC duplicate)
CloseVWAP-M2K-Short            16    Jun 01     Unlikely (decaying)
MomIgn-M2K-Short               14    Jun 01     FIRST EXPIRY

CHALLENGERS (testing)         Est.Score  Target Slot   Gap Bonus
Treasury-Rolldown-Carry        18(+2)    → MomIgn       CARRY+Rates
Commodity-TS-Carry             17(+2)    → MomIgn       CARRY
MomPB-6E-Long-US               16       Blocked (MOM>50%)
```

7. Run weekly as part of Friday scorecard, or on demand.

**Engineering time:** ~4 hours. Reads existing data, no new infrastructure.

### Expected Portfolio Benefit

Makes competitive pressure visible and continuous. Prevents the two
failure modes of a capped system:
- **Stagnation:** weak incumbents survive because nobody reviewed them
- **Queue blindness:** strong challengers wait in testing because nobody
  compared them to incumbents

The board turns the Friday scorecard from "is anything broken?" into
"is the portfolio as strong as it could be?"

---

## 2. Forward-Integrated Counterfactual Analysis

### Why It Matters

The counterfactual engine exists (`research/counterfactual_engine.py`)
and computes 6 dimensions of opportunity cost. But it runs on **backtest
data only** and is **not scheduled**. This means:
- Portfolio decisions are based on historical contribution, not live
- A strategy that was valuable 2 years ago but is now dilutive won't
  be caught until a manual review
- The elite standard requires that every strategy continuously earns
  its slot — not that it earned it once in a backtest

### What It Would Measure

Same 6 dimensions the counterfactual engine already computes, but on
**forward/live trading data** from `logs/trade_log.csv`:

1. **Forward marginal Sharpe:** Portfolio Sharpe WITH vs WITHOUT each
   strategy, using actual forward trade PnL
2. **Forward drawdown contribution:** Did this strategy help or hurt
   during the worst portfolio drawdowns in the forward period?
3. **Forward overlap cost:** Is this strategy's forward PnL correlated
   with another strategy's forward PnL? (Different from backtest
   correlation — regime may have changed)
4. **Forward slot efficiency:** Risk-adjusted return per attention slot,
   using forward data
5. **Forward displacement signal:** If marginal Sharpe is negative for
   3+ consecutive weeks, flag for review

### What Files/Modules It Would Touch

| Component | Action |
|-----------|--------|
| `research/counterfactual_engine.py` | **MODIFY:** Add forward data path alongside backtest path |
| `logs/trade_log.csv` | Read forward trades (already exists, normalized to 10 columns) |
| `research/fql_research_scheduler.py` | **MODIFY:** Add counterfactual to weekly pipeline |
| `research/weekly_scorecard.py` | **MODIFY:** Add forward counterfactual section |
| `research/data/counterfactual_log.json` | Append forward counterfactual entries |

### Minimal v1

Don't rewrite the counterfactual engine. Instead:

1. Add a `--forward` flag to `counterfactual_engine.py` that builds the
   daily PnL matrix from `logs/trade_log.csv` instead of from backtest data
2. Run the same 6-dimension analysis on forward data
3. Output a comparison: backtest counterfactual vs forward counterfactual
   - If a strategy is KEEP_FULL on backtest but REVIEW on forward →
     the edge may be decaying in live trading
   - If a strategy is REVIEW on backtest but KEEP_FULL on forward →
     the strategy improved (regime favorable)
4. Add to weekly pipeline (Friday, after scorecard)
5. Log to `counterfactual_log.json` for trend tracking

**Key constraint:** Forward trade count is still small (14 trades across
4 strategies over 304 days). The forward counterfactual will be noisy
initially. That's fine — the trend matters more than the point estimate.
As forward evidence accumulates, the signal strengthens.

**Engineering time:** ~3 hours. Mostly wiring the forward data path into
the existing engine and adding it to the scheduler.

### Expected Portfolio Benefit

Catches the #1 portfolio-level failure mode: **a strategy that was
valuable in backtest but is now dilutive in live trading.** The
counterfactual engine already knows how to compute this — it just needs
to be pointed at real data and scheduled to run automatically.

The forward marginal Sharpe is the ultimate accountability metric. If
a strategy's forward marginal Sharpe is negative for 3+ consecutive
weeks, the elite standard demands a review — regardless of how good
the backtest looked.

---

## 3. Faster Decay / Drift Detection

### Why It Matters

The current system has two separate decay detectors:
- **Live drift monitor:** Fast (daily), but uses a static backtest
  baseline. It detects when forward deviates from one historical
  reference point, not when the edge is actively dying.
- **Half-life monitor:** Comprehensive (rolling windows), but runs on
  **backtest data only**. It caught RangeExpansion's decay, but only
  because the backtest data itself showed the decline. It cannot detect
  forward-only decay.

Neither system combines backtest decay trajectory with forward evidence
to produce a unified "is this edge alive?" signal. The result:
RangeExpansion's Sharpe went from 2.39 to -0.13 over 6 months before
being flagged. That's too slow for elite standard.

### What It Would Measure

A unified **Edge Vitality Score** per strategy that combines:

1. **Backtest decay trajectory:** From half-life monitor (rolling Sharpe
   across windows). Is the backtest edge declining over time?
2. **Forward deviation:** From drift monitor. Is forward performance
   diverging from the backtest baseline?
3. **Forward-specific decay:** Rolling Sharpe on forward trades only
   (when enough trades exist). Is the forward edge declining over the
   forward period itself?
4. **Combined vitality signal:** Weighted composite:
   - 40% forward deviation (most important — real market evidence)
   - 30% backtest decay trajectory (historical trend)
   - 30% forward-specific decay (if available, else backtest weight)

Output: a single score per strategy, updated daily:

| Vitality | Range | Meaning |
|----------|-------|---------|
| VITAL | > 0.7 | Edge is alive and consistent |
| STABLE | 0.4-0.7 | Edge exists but showing some wear |
| FADING | 0.1-0.4 | Edge is declining — active monitoring required |
| DEAD | < 0.1 | Edge is gone — immediate review |

### What Files/Modules It Would Touch

| Component | Action |
|-----------|--------|
| **NEW: `research/edge_vitality_monitor.py`** | Unified scorer combining 3 data sources |
| `research/strategy_half_life_monitor.py` | Read decay scores (existing, no modification) |
| `research/live_drift_monitor.py` | Read drift severity (existing, no modification) |
| `logs/trade_log.csv` | Read forward trades for forward-specific decay |
| `research/fql_research_scheduler.py` | Add to daily pipeline (after half-life and drift) |
| `research/weekly_scorecard.py` | Add vitality column to probation/core sections |
| `research/data/strategy_registry.json` | Write `edge_vitality` score per strategy |

### Minimal v1

1. Read half-life decay score from the latest half-life report
2. Read drift severity from the latest drift log entry
3. Compute forward rolling Sharpe from `trade_log.csv` (if 10+ forward
   trades exist for a strategy)
4. Combine into a single vitality score using the weighted formula
5. Write to registry as `edge_vitality` field
6. Flag any strategy below 0.4 (FADING) in the daily decision report
7. Flag any strategy below 0.1 (DEAD) as an immediate review trigger

**Detection speed improvement:** Currently, decay detection requires
manual review or the weekly scorecard to notice. With vitality scoring
in the daily pipeline, a FADING signal would appear within 1 trading
day of the underlying metrics crossing the threshold. RangeExpansion
would have been flagged months earlier.

**Engineering time:** ~5 hours. Reads from 3 existing data sources,
writes one composite score. No new data collection needed.

### Expected Portfolio Benefit

Turns decay from a "discovered during quarterly review" event into a
"flagged within 24 hours" event. The elite standard demands that
dying edges are caught before they cost real capital. The vitality
score makes edge health as visible as PnL — it appears in every daily
report, every scorecard, and every displacement check.

Combined with the replacement scoreboard: when a strategy's vitality
drops to FADING, the scoreboard immediately shows which challenger is
next in line. The transition from "this edge is dying" to "this is what
replaces it" becomes seamless.

---

## Priority Ranking

| Rank | Upgrade | Time | Impact | Depends On |
|------|---------|------|--------|------------|
| **1** | Replacement Scoreboard | ~4h | Makes competitive pressure visible and continuous | Nothing — pure read from registry |
| **2** | Forward Counterfactual | ~3h | Catches live dilution that backtest misses | Forward trade data (exists, growing) |
| **3** | Edge Vitality Monitor | ~5h | Catches decay within 24h instead of months | Half-life + drift outputs (both exist) |

All three are read-only analytics. None modify live trading logic,
strategy code, or the forward runner. They consume existing data and
produce advisory outputs that inform human decisions.

### Sequencing

Build in order: 1 → 2 → 3. Each upgrade makes the next one more
valuable:
- Scoreboard shows WHO is vulnerable
- Counterfactual shows WHETHER they're still earning their slot
- Vitality shows HOW FAST they're declining

Together, they create a continuous quality-pressure loop: discover →
test → challenge → replace. The portfolio never rests on past results.
