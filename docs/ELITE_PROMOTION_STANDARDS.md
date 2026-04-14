# Elite Promotion Standards by Strategy Shape

**Purpose:** Define the evaluation framework that applies to each kind of
strategy before promotion. Different shapes require different gates.
Applying the wrong framework is itself a failure mode — this document
exists to make that failure mode impossible to commit by accident.

**Scope:** This is a **promotion / probation-review** standard. It does
not govern harvest or first-pass discovery (those can be more
exploratory). It applies when a strategy is being moved toward or
through active probation and in any post-probation promotion decision.

**Authority relationship:**
- This doc names the **evaluation framework** per shape.
- `docs/PROBATION_REVIEW_CRITERIA.md` names the **specific thresholds** for individual non-XB-ORB strategies.
- `docs/XB_ORB_PROBATION_FRAMEWORK.md` names the **specific thresholds** for the XB-ORB family.
- `research/data/strategy_registry.json` is the **lifecycle state** source of truth.

If a strategy fits no shape below, do not promote it. Add a shape here first.

---

## Cross-shape: The wrong-framework failure mode

**The most dangerous evaluation mistake is applying the wrong shape's
framework to a strategy.** This has now been observed twice in recent
history:

- **Treasury-Rolldown-Carry-Spread** (spread strategy) ran through the
  intraday-single-asset runner, produced 0 signals, and was auto-archived
  as "structurally broken." The strategy was fine; the infrastructure
  couldn't host it. Recovered via out-of-band monthly path.

- **FXBreak-6J-Short-London** (sparse session-transition structural)
  was routed through the workhorse path of the dual-archetype batch. It
  failed the 500-trade workhorse threshold (it's naturally a 128-trade
  London-session strategy) and was flagged SALVAGE. Separately, the elite
  rubric scored it 17/24 vs an 18 conviction bar.

**Rule:** Before any promotion or archive decision, confirm:

1. What shape is this strategy? (This doc.)
2. Is the evaluation framework being applied the one named for that
   shape below? (Not the default workhorse framework by accident.)
3. Is the runtime infrastructure capable of hosting this shape
   end-to-end? (Or is an out-of-band path required?)

A verdict rendered under the wrong framework is not a verdict at all.

---

## Shape 1: Intraday Single-Asset Workhorse

**Examples:** XB-ORB-EMA-Ladder-{MNQ, MCL, MYM}, ORB-MGC-Long, PB-MGC-Short

### Defining characteristics
- One asset per strategy (the runner loads one data feed per strategy).
- Per-trade PnL accrues in `logs/trade_log.csv` via the intraday forward runner.
- Signals expected at trade-per-day cadence of >= 0.3 on average.
- Trade and hold durations measured in minutes to hours.

### Minimum evidence for promotion
- **Backtest trades:** >= 500.
- **Backtest PF:** >= 1.2 (workhorse primary) or >= 1.3 for STRONG.
- **Walk-forward H1 and H2 both > 1.0** (no regime where all trades lose).
- **Forward trades:** >= 30 for first formal review (20 for flag-only preview).

### Acceptable concentration
- Top-3 trade share < 30% of total PnL.
- Top-10 trade share < 55%.
- Max single year < 40% of total PnL.
- Median trade PnL > 0.

### Framework to use
**Dual-archetype classifier in `research/batch_first_pass.py`**, workhorse path. The tail-engine path may also run (trades < 500 would anyway route through both with stricter verdict winning), but pure intraday single-asset is the workhorse archetype and should hit the workhorse thresholds above.

### Kill criteria (immediate archive)
- Forward PF < 0.7 after 40+ forward trades.
- Single event drawdown > 2× backtest max DD.
- Silent failure (0 signals over 10k+ bars when expected frequency > 0).

### Promotion gate example
See `docs/XB_ORB_PROBATION_FRAMEWORK.md` sections "Formal review gates"
and "Promotion Criteria" for the canonical workhorse promotion
sequence (20 / 30 / 50 / 100 forward-trade gates).

---

## Shape 2: Sparse Event-Driven

**Examples:** TV-NFP-High-Low-Levels, PreFOMC-Drift-Equity (archived), other macro-event strategies

### Defining characteristics
- Signals fire only on specific calendar events (NFP, FOMC, CPI, OPEX).
- Trade count measured by event count, not daily cadence.
- Expected ~1 trade per event type per occurrence; sample size grows with the event calendar, not with market open days.
- Between events, legitimate long silence.

### Minimum evidence for promotion
- **Backtest event count:** >= 30 occurrences of the triggering event.
- **Backtest PF:** >= 1.4 per event (higher bar than workhorse — sparse strategies must earn attention against their small sample).
- **Forward event count:** >= 4 occurrences before any forward verdict.

### Acceptable concentration
- Max single event < 40% of total PnL (sparse strategies naturally concentrate; bar is higher than workhorse).
- Per-event-type PF variance < 2x across sub-types (e.g., if NFP-surprise-up and NFP-surprise-down have wildly different PFs, flag).

### Framework to use
**Tail-engine classifier in `research/batch_first_pass.py`**, via the classify_with_tail_engine routing when trades < 500. Use `per_event_decomposition` when the strategy exposes `EVENT_CLASSIFIER` — factory does this automatically. Concentration gates must be **event-based, not trade-based.**

**Vitality adjustments for sparse events** (from `docs/PROBATION_REVIEW_CRITERIA.md`):
- Backtest decay weight 50% (up from 30%).
- Forward deviation weight 30% (down from 40%).
- Forward decay weight 20% (down from 30%).
- FADING alerts suppressed until >= 4 event occurrences with forward data.

### Kill criteria
- Forward PF < 0.7 after 8+ event occurrences.
- Edge vitality tier DEAD on sparse-adjusted weights.
- Event type disappears or changes structure (regulatory/calendar shift).

### Wrong-framework warning
Applying workhorse concentration gates (top-3 < 30%) to sparse event strategies is wrong. An event strategy with 8 trades and 40% in the top event is operating normally, not failing. Use event-count thresholds.

---

## Shape 3: Out-of-Band Monthly

**Examples:** Treasury-Rolldown-Carry-Spread (re-probated 2026-04-14)

### Defining characteristics
- Monthly rebalance cadence.
- May require multi-asset data (see spread shape below for the subcase).
- Position held for ~1 month between rebalances.
- Evidence accrues at ~12 cycles per year, not hundreds.
- Execution must NOT use the intraday forward runner; requires a dedicated script + launchd agent.

### Minimum evidence for promotion
- **Backtest rebalance cycles:** >= 60 months (5 years of history).
- **Backtest PF:** >= 1.1 (lower than workhorse — spread / carry strategies have inherently lower PF ceilings and compensate with low correlation).
- **Forward cycles:** >= 8 before promotion to CONVICTION.

### Acceptable concentration
- Max single year < 50%.
- No single 3-cycle consecutive streak > 60% of total PnL.
- Per-asset-leg PnL distribution reasonably balanced (one tenor shouldn't drive all returns).

### Framework to use
**Custom review, not `batch_first_pass.py`.** The dual-archetype classifier assumes per-trade metrics from intraday bars. Monthly strategies must be evaluated via dedicated tooling that reads the strategy's own evidence source (e.g., `logs/spread_rebalance_log.csv`).

### Required infrastructure
- `execution_path: "out_of_band_monthly_batch"` field in registry.
- `controller_action` stays `OFF` so the intraday runner never loads it.
- Dedicated launchd agent with first-business-day guard inside the script.
- Evidence log in its own CSV with shape-appropriate columns (not intraday `trade_log.csv`).
- Drift monitor lists strategy in `BASELINE["excluded_from_strategy_drift"]` with a reason pointing at the evidence log.

### Kill criteria
- Forward PF < 0.5 after 12 cycles.
- Carry/spread signal stops producing rank changes for 6+ consecutive cycles (static ranking = dead mechanism).
- Sign of realized PnL on closed spreads consistently wrong vs backtest expectation across 4+ cycles.

### Wrong-framework warning
Running this shape through the intraday runner produces 0 signals and auto-archives the strategy. Treasury-Rolldown's 2026-04-13 archive was this exact mistake. Before archiving any monthly/spread strategy for "0 forward trades," verify the runner is even capable of producing them.

---

## Shape 4: Overlay / Sizing Regime

**Examples:** VolManaged-EquityIndex-Futures

### Defining characteristics
- Always-long (or always-short) position in a single asset.
- Strategy adjusts HOW MUCH to hold, not WHEN to enter or exit.
- Daily weight rebalance based on realized vol / signal input.
- No discrete "trades" in the normal per-trade sense.

### Minimum evidence for promotion
- **Backtest days:** >= 252 (one year of daily rebalances).
- **Backtest Sharpe improvement:** >= 20% vs unscaled baseline on the same days.
- **Forward days:** >= 30 with continuous daily weight tracking.

### Acceptable concentration
- Does not apply in the top-N trade sense.
- Concentration failure mode is **weight divergence**: forward realized weight should track what the backtest would have produced on the same inputs within < 20% deviation on any given day.

### Framework to use
**Custom weight-replication metric**, not per-trade. Compare:
- Forward realized position weight vs backtest-expected weight (same date, same inputs).
- Forward Sharpe vs unscaled Sharpe over same period (must remain > unscaled).
- Portfolio contribution: marginal Sharpe when added to portfolio must be > 0.

### Required infrastructure
- `BASELINE["excluded_from_strategy_drift"]` entry in `live_drift_monitor.py` — per-trade drift does not apply.
- Manual or custom review; no current automation for this shape.
- FOLLOW-UP noted: design a VolManaged-specific drift metric when capacity allows.

### Kill criteria
- Forward Sharpe < 0 after 90+ days.
- Crisis drawdown > 2x backtest max DD.
- Long-bias interaction failure: DD clusters with portfolio DD on same days (confirms the "unique mechanism" thesis was wrong).

### Wrong-framework warning
Applying trade-count or win-rate frameworks to this shape produces nonsense. VolManaged has 0 entry signals and 0 exit signals in the normal sense. If a dashboard reports "VolManaged: 0 trades this week, DRIFT alert," the dashboard is mis-modeling the strategy.

---

## Shape 5: Spread Strategy

**Examples:** Treasury-Rolldown-Carry-Spread (3-tenor ZN/ZF/ZB spread)

### Defining characteristics
- Requires simultaneous positions in 2+ related instruments.
- Rebalance can be monthly (fits shape 3 above) or other cadence.
- PnL is the net of the legs, not per-leg.
- Spread identity must be preserved in logs — NOT split into pseudo-independent trades.

### Minimum evidence for promotion
- **Backtest rebalance cycles:** shape-dependent (see shape 3 for monthly).
- **Rate-neutrality / factor-neutrality check:** spread's correlation with the dominant directional factor in its asset class must be < 0.10 (carry spreads are supposed to isolate carry, not direction).
- **Spread-level PF:** >= 1.1 (lower ceiling than directional strategies — spreads compete with cash-to-cash carry, not directional edge).

### Acceptable concentration
- Max single cycle < 25% (spreads with one dominant cycle are usually directional disguised as carry).
- Per-leg-pair rotation: if the same two legs appear > 80% of cycles, the "rank" mechanism isn't actually changing (static spread, not a carry strategy).

### Framework to use
**Spread-native evidence log** with columns that preserve long-leg/short-leg identity and net realized PnL. Examples:
- `logs/spread_rebalance_log.csv` for Treasury-Rolldown (14-column schema including `spread_id`, `long_leg_asset`, `short_leg_asset`, `realized_pnl_prior_spread`).
- NOT `logs/trade_log.csv` with two rows per rebalance — that schema pollution was explicitly rejected during Treasury-Rolldown's re-probation design.

### Required infrastructure
- Combines with shape 3 (out-of-band) almost always.
- Registry field `execution_path: "out_of_band_monthly_batch"` (or similar).
- `controller_action=OFF` so intraday runner doesn't attempt to host the strategy.
- Spread-aware drift handling: either exclude from per-trade drift (current Treasury-Rolldown handling) or build a dedicated spread-level drift metric when a second spread strategy appears.

### Kill criteria
- Legs stop rotating (static ranking = dead carry signal).
- Spread PnL correlation with directional factor exceeds 0.25 for 4+ consecutive cycles (strategy became directional, no longer a carry play).
- Cost-adjusted PF < 0.9 after 12 cycles.

### Wrong-framework warning
Testing a spread strategy as single-leg asset-by-asset is what rejected Treasury-Rolldown the first time. The per-asset results look terrible because the strategy doesn't work as three independent directional trades; it only works as a spread. Always evaluate spread strategies as spreads.

---

## New strategy qualification — before any shape evaluation

Before classifying and testing a new candidate under a shape above, verify:

- [ ] **Primary factor is explicitly stated** (MOMENTUM / MEAN_REVERSION / VOLATILITY / CARRY / STRUCTURAL / VALUE / EVENT). If the candidate is "kinda momentum, kinda breakout," it's not well-defined yet.
- [ ] **The portfolio has a real gap for this factor or asset class.** If momentum + equity index already has 7 active strategies, another momentum-on-MNQ is not elite candidacy — it's overcrowding.
- [ ] **Expected PnL mechanism is stated in one sentence.** If the "why does this work" takes a paragraph, the strategy is not understood yet.
- [ ] **Shape above has been identified before testing begins.** If no shape fits, either (a) the candidate belongs in a future shape that doesn't exist yet (add shape first), or (b) the candidate is ill-defined.
- [ ] **Evidence source has been chosen.** Where will the backtest numbers come from? Will the forward evidence fit the existing trade_log, or need a new log?
- [ ] **The candidate is evaluated by a diversifier, not a duplicate.** Four correlation checks: entry signal correlation, PnL daily-return correlation, factor primary, asset.

Candidates that can't clear all six should not consume batch first-pass time. They should be sent back to harvest/spec refinement.

---

## Kill-on-sight failure patterns

Any of these, observed at any point in a strategy's lifecycle, triggers immediate archive with documented failure mode — no forward-evidence accumulation required:

1. **Concentration catastrophe:** top-3 trades > 80% of total PnL, or max single year > 100% of total PnL (other years net-negative). Seen in FXBreak-6J. Not recoverable — the backtest edge is tail-event luck, not reproducible behavior.
2. **Wrong-direction bias confirmed:** a "long" strategy's long trades lose money in backtest while short trades drive the PnL, or vice versa. Indicates the signal logic is inverted and the reported direction is misleading.
3. **Data-leakage signal:** any strategy whose entries depend on same-bar-close prices, same-day totals, or any field computed AFTER the stated entry time. Verify bar close semantics; future-peeking invalidates all evidence.
4. **Silent failure:** strategy produces 0 signals over 10k+ bars when the backtest expected frequency would produce > 20. Either the data pipeline broke for this strategy, or the strategy's logic can't execute in the runtime infrastructure. Do not promote without resolving.
5. **Correlation breach with an existing live strategy:** signal correlation > 0.7 AND daily-return correlation > 0.7 with an already-active strategy. Not a diversifier; would only concentrate risk.
6. **Ill-defined factor:** candidate was promoted without an explicitly stated primary factor. These strategies become unclassifiable and fail the authority-consistency validator (when built).

Any kill-on-sight trigger should be recorded in the registry's `rejection_reason` with the specific numbers and a pointer to the verification commit.

---

## Wrong-framework self-check before rendering any verdict

Before writing a PROMOTE / ADVANCE / SALVAGE / ARCHIVE verdict for any strategy, confirm:

- [ ] What shape does this strategy fit per this document?
- [ ] Did the evaluation use the framework named for that shape?
- [ ] If the strategy produced 0 forward signals, can the runtime infrastructure actually host this shape? (Or is the 0 a shape-infra mismatch?)
- [ ] Are the concentration thresholds being applied in the scale appropriate for the shape? (Top-3 < 30% is a workhorse gate; sparse events can legitimately have one event as 40% of PnL.)
- [ ] Is the sample size ratio appropriate for the shape? (128 trades is thin for a workhorse but normal for a London-session strategy; 8 events is sparse but normal for FOMC.)

If any answer is "no" or "unclear," the verdict is not ready. Refuse to render it until the framework is correct.

---

*This document governs evaluation framework selection, not specific thresholds. For specific thresholds see `docs/PROBATION_REVIEW_CRITERIA.md` and `docs/XB_ORB_PROBATION_FRAMEWORK.md`. For current portfolio state see `docs/PORTFOLIO_TRUTH_TABLE.md`.*
