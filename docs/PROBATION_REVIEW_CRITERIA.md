# Probation Strategy Review Criteria

*Forward evidence thresholds for promotion, continuation, and removal.*
*Effective: 2026-03-17 onward*

---

## Active Probation Strategies

### 0. XB-ORB-EMA-Ladder Workhorse Family (MNQ / MCL / MYM)

| Strategy | Asset | Backtest PF | Backtest Trades | Promoted |
|----------|-------|-------------|-----------------|----------|
| XB-ORB-EMA-Ladder-MNQ | MNQ | 1.62 | 1183 | 2026-04-06 |
| XB-ORB-EMA-Ladder-MCL | MCL | 1.33 | 898  | 2026-04-08 |
| XB-ORB-EMA-Ladder-MYM | MYM | 1.67 | 340  | 2026-04-13 |

**Governed by:** [`docs/XB_ORB_PROBATION_FRAMEWORK.md`](./XB_ORB_PROBATION_FRAMEWORK.md)
(effective 2026-04-13). That framework is the single source of truth for
review gates (20 / 30 / 50 / 100 forward trades), promotion/downgrade/
archive logic, behavioral flag criteria, and the core-promotion
engineering checklist for all XB-ORB variants.

**Do NOT duplicate XB-ORB criteria in this document.** If the framework
needs to change, edit `XB_ORB_PROBATION_FRAMEWORK.md` and leave this
pointer intact. Keeping XB-ORB rules in one place prevents the exact
doc-drift failure mode the framework was created to solve.

This document (`PROBATION_REVIEW_CRITERIA.md`) continues to govern all
**non-XB-ORB** probation strategies — the legacy watch set and event
sleeves listed below.

---

### 1. DailyTrend-MGC-Long

| Field | Value |
|-------|-------|
| Asset | MGC (Micro Gold) |
| Horizon | Daily bars |
| Direction | Long only |
| Validation | PASS 7/8 |
| Backtest PF | 3.65 |
| Allocation tier | REDUCED |
| Promotion threshold | 15 forward trades |
| Convergent confirmation | DualThrust MGC long PF 2.79 (independent entry) |

**Promote to ACTIVE if:**
- 15+ forward trades accumulated
- Forward PF > 1.2
- Forward Sharpe > 0.5
- No catastrophic drawdown event (> $3K single-strategy DD)
- Walk-forward consistency holds (no regime where all trades lose)

**Continue probation if:**
- 15+ trades but PF 1.0-1.2 (edge present but thin)
- OR fewer than 15 trades after 3 months (low frequency is expected for daily bars)
- OR forward metrics are healthy but data is still accumulating

**Downgrade to MONITOR if:**
- Forward PF < 1.0 after 15+ trades
- OR 3+ consecutive losing trades with total drawdown > $2K
- OR gold enters a sustained ranging regime where the strategy generates no signals for 6+ weeks

**Remove if:**
- Forward PF < 0.7 after 20+ trades (structural failure)
- OR single event drawdown > $5K

---

### 2. MomPB-6J-Long-US ~~(ARCHIVED 2026-03-18)~~

> **HISTORICAL RECORD — NO LONGER ACTIVE PROBATION.**
> Archived 2026-03-18 per `research/data/strategy_registry.json`
> (`status=archived`, `controller_action=ARCHIVE_REVIEW`). The
> thresholds below are retained for design-record reasons only;
> this strategy is not in the live/probation path and is not
> tracked by the drift monitor. Current authority for probation
> membership: `strategy_registry.json`.

| Field | Value |
|-------|-------|
| Asset | 6J (Japanese Yen) |
| Horizon | Intraday 5m |
| Direction | Long only |
| Session | US only (08:00-17:00 ET) |
| Validation | CONDITIONAL_PASS 5/7 |
| Backtest PF | 1.58 |
| Allocation tier | REDUCED |
| Promotion threshold | 30 forward trades |

**Promote to ACTIVE if:**
- 30+ forward trades accumulated
- Forward PF > 1.2
- Forward Sharpe > 0.8
- US session edge confirmed (majority of profitable trades in US hours)
- No regime catastrophe

**Continue probation if:**
- 30+ trades but PF 1.0-1.2
- OR fewer than 30 trades after 3 months (moderate frequency expected)
- Edge appears real but noisy

**Downgrade to MONITOR if:**
- Forward PF < 1.0 after 30+ trades
- OR US session edge disappears (majority of profitable trades NOT in US hours)
- OR 6J daily volume drops significantly (liquidity concern)

**Remove if:**
- Forward PF < 0.8 after 40+ trades
- OR consistent losing in US session specifically

---

### 3. FXBreak-6J-Short-London ~~(REJECTED 2026-03-18)~~

> **HISTORICAL RECORD — NO LONGER ACTIVE PROBATION.**
> Rejected 2026-03-18 per `research/data/strategy_registry.json`
> (`status=rejected`). Strategy is not in the live/probation path
> and is not tracked by the drift monitor. Current authority:
> `strategy_registry.json`.
>
> **Portfolio-construction consequence (not re-litigated here):**
> This was the only STRUCTURAL primary in the portfolio at the
> time of rejection — the factor-diversification role it filled
> has not been formally replaced. Worth flagging in any future
> portfolio-composition exercise.

| Field | Value |
|-------|-------|
| Asset | 6J (Japanese Yen) |
| Horizon | Intraday 5m |
| Direction | Both (short bias) |
| Session | London (03:00-08:00 ET) |
| Validation | CONDITIONAL_PASS 5/8 |
| Backtest PF | 1.20 |
| Allocation tier | MICRO |
| Promotion threshold | 50 forward trades |
| **Factor role** | **Only STRUCTURAL primary in portfolio. Provides genuine factor diversification beyond momentum.** |

**Strategic importance:** Factor decomposition shows the portfolio is 54% MOMENTUM.
FXBreak-6J is the ONLY probation strategy that adds a different primary factor
(STRUCTURAL — session-transition edge). This makes it strategically more valuable
than its PF alone suggests. Even at borderline metrics, it deserves extra weight
in promotion decisions because of the factor diversification it provides.

**Promote to ACTIVE if:**
- 50+ forward trades accumulated
- Forward PF > 1.1 (lower bar than MomPB because backtest PF is thinner)
- Short trades outperform long trades (confirms directional bias)
- London session generates majority of signals (confirms session structure)
- Bootstrap CI lower bound improves toward 1.0 with more data

**Continue probation if:**
- 50+ trades but PF 1.0-1.1
- OR fewer than 50 trades after 3 months
- London session structure intact even if overall PF is borderline

**Downgrade to MONITOR if:**
- Forward PF < 0.95 after 50+ trades (edge too thin for costs)
- OR London session stops producing signals (Asian range structure changed)
- OR short bias disappears (long and short perform equally badly)

**Remove if:**
- Forward PF < 0.85 after 60+ trades
- OR strategy conflicts with MomPB-6J in ways that net-reduce 6J portfolio value

---

### 6. Treasury-Rolldown-Carry-Spread (RE-PROBATED 2026-04-14 — out-of-band monthly)

> **RE-PROBATED 2026-04-14 via out-of-band monthly execution path.**
> Previously archived 2026-04-13 with reason "structurally broken —
> runner tracks ZN but strategy requires ZF/ZB spread." Post-archive
> review determined the trigger was **infrastructure mismatch, not
> strategy failure**: the intraday forward runner loads one asset
> per strategy, so Treasury-Rolldown (a 3-tenor ZN/ZF/ZB spread)
> produced zero signals and was auto-archived. The spread's
> backtest evidence (PF 1.11, 79 trades, rate-neutral per
> component_validation_history) was never invalidated.
>
> **New execution path:** `research/run_treasury_rolldown_spread.py`
> fires on the first business day of each month via launchd
> (`com.fql.treasury-rolldown-monthly`). Evidence accrues in
> `logs/spread_rebalance_log.csv` (one row per rebalance, preserves
> spread identity via `spread_id`). The strategy stays
> `controller_action=OFF` in the registry so it never enters the
> intraday runner — the registry now carries an explicit
> `execution_path="out_of_band_monthly_batch"` field to make this
> intentional separation machine-readable.
>
> **Drift monitor handling:** listed in
> `live_drift_monitor.py BASELINE["excluded_from_strategy_drift"]`.
> Per-trade severity does not apply to monthly spread rebalances;
> review via direct inspection of `logs/spread_rebalance_log.csv`
> and the registry's `component_validation_history`.
>
> **June 1 displacement plan:** still moot (MomIgn-M2K-Short
> remains off). Treasury-Rolldown's re-probation does not
> automatically revive that displacement target — the portfolio
> slot left open by MomIgn is a separate design decision.
>
> **Thresholds below stand** as the probation gates (8 forward
> rebalance cycles → promote with PF > 1.1 and Sharpe > 0.3; 3
> consecutive negative months → downgrade). The clock started
> with the first real rebalance after 2026-04-14; seeded
> historical entries (2026-03, 2026-04 in the spread log) are
> marked in notes and do not count toward the 8-cycle threshold.

| Field | Value |
|-------|-------|
| Asset | ZN/ZF/ZB (3-tenor spread) |
| Horizon | Monthly rebalance |
| Direction | Both (spread: long rich-carry, short poor-carry) |
| Validation | MONITOR (first-pass PF 1.11, 79 trades) |
| Backtest PF | 1.11 (equal-notional) |
| Allocation tier | MICRO |
| Promotion threshold | 8 forward rebalance cycles |
| **Factor role** | **First CARRY + first Rates strategy. Fills the two biggest portfolio gaps.** |
| **Displacement target** | MomIgn-M2K-Short at June 1, 2026 deadline |

**Entered forward runner:** 2026-03-20. Accumulating forward evidence.

**Promote to CONVICTION if:**
- 8+ forward rebalance cycles completed (~8 months)
- Forward PF > 1.1
- Forward Sharpe > 0.3
- Walk-forward stability maintains (no regime where all trades lose)
- No catastrophic drawdown (> $3K single-strategy DD)

**Displace MomIgn at June 1 if:**
- Forward PnL positive over March–May 2026 (3 cycles)
- Rubric score remains ≥ 18 (eff. 20 with gap bonus)
- MomIgn fails its own promote condition by deadline

**Continue probation if:**
- Forward PnL flat or slightly negative but mechanism intact
- OR fewer than 3 rebalance cycles completed (monthly = slow evidence)

**Downgrade to WATCH if:**
- 3 consecutive months of negative forward spread PnL
- OR forward PF < 0.8 after 8 cycles

**Remove if:**
- Forward PF < 0.5 after 12 cycles
- OR carry signal stops producing rank changes (spread is static)

---

### 7. ZN-Afternoon-Reversion (Falsification Discovery)

| Field | Value |
|-------|-------|
| Asset | ZN (10-Year Note) |
| Horizon | Intraday (25-minute hold, 14:00-14:25 ET) |
| Direction | Both, short-biased (89% backtest PnL from shorts) |
| Validation | First-pass PF 1.32, 300 trades, WF 1.31/1.33 |
| Backtest PF | 1.32 |
| Allocation tier | MICRO |
| Promotion threshold | 30 forward trades |
| **Origin** | Variant B from Treasury-Cash-Close-Reversion falsification (parent REJECTED) |
| **Factor role** | STRUCTURAL — rates afternoon microstructure. Zero overlap with morning equity strategies. |

**Entered forward runner:** 2026-03-20. Accumulating forward evidence.

**Distinguished from Treasury-Rolldown-Carry-Spread:** Same asset (ZN),
but different mechanism (25m intraday reversion vs monthly carry spread),
different session (14:00-14:25 vs daily close evaluation), different
factor (STRUCTURAL vs CARRY). They are independent bets.

**Monitoring flags:**
- HIGH_VOL dependency: PF 1.64 in high-vol vs 1.04 in low-vol. Will
  underperform in quiet rate regimes.
- Window-specific: ±15m shift degrades results. Monitor for CME session
  changes.
- Data caveat: ~18% of weekdays excluded (sparse ZN bars). Forward
  results conditioned on afternoon liquidity.
- Tuesday weakness: backtest PF 0.87 on Tuesdays (4/5 other days positive).

**Promote to CONVICTION if:**
- 30+ forward trades accumulated
- Forward PF > 1.1
- Forward Sharpe > 0.5
- Short bias confirmed in forward (majority of PnL from shorts)
- No catastrophic DD (> $3K single-strategy)
- Contribution check: correlation < 0.20 with all existing strategies

**Continue probation if:**
- 30+ trades but PF 1.0-1.1 (thin edge, needs more data)
- OR fewer than 30 trades after 6 months (low vol = fewer signals)

**Downgrade to WATCH if:**
- Forward PF < 0.9 after 30+ trades
- OR strategy generates no signals for 4+ consecutive weeks (vol regime too low)

**Remove if:**
- Forward PF < 0.7 after 40+ trades
- OR ZN afternoon session structure changes materially

---

### 8. VolManaged-EquityIndex-Futures (Volatility Gap Fill)

| Field | Value |
|-------|-------|
| Asset | MES (S&P 500 Micro) |
| Horizon | Daily (always-in, daily rebalance of position weight) |
| Direction | Long only |
| Validation | Conviction-ready — rubric 22 effective (highest in system) |
| Backtest Sharpe | 0.92 (vs 0.64 unscaled buy-and-hold, +44%) |
| Allocation tier | MICRO / REDUCED only |
| Promotion threshold | 30 forward days with daily weight tracking |
| **Factor role** | **First VOLATILITY strategy. Fills the #1 portfolio gap.** |
| **Mechanism** | Sizing regime, not entry/exit timing — unique in portfolio |

**Entered forward runner:** 2026-03-20.

**This strategy is always long.** It does not generate entry/exit signals
like other strategies. It adjusts HOW MUCH to hold based on realized vol.
Forward evaluation compares vol-managed returns vs unscaled returns on
the same days.

**Promote to CONVICTION if:**
- 30+ forward trading days accumulated
- Forward Sharpe > 0.5 (vol-managed)
- Forward Sharpe improvement > 20% vs unscaled baseline on same days
- No crisis DD exceeding 1.5x backtest worst ($4,674 backtest max DD)
- Portfolio contribution confirmed additive (marginal Sharpe > 0)

**Continue probation if:**
- Sharpe 0.3-0.5 (edge present but thinner than backtest)
- OR fewer than 30 forward days (slow market period)
- OR crisis DD within 1.0-1.5x backtest range (monitoring)

**Downgrade to WATCH if:**
- Forward Sharpe < 0.3 after 60+ forward days
- OR crisis DD exceeds 1.5x backtest worst
- OR portfolio contribution turns dilutive (marginal Sharpe < 0)
- OR daily weight diverges >20% from backtest expectation on same dates
  (signal replication failure)

**Remove if:**
- Forward Sharpe < 0 after 90+ forward days
- OR crisis DD exceeds 2x backtest worst ($9,348)
- OR long-bias concern confirmed: VolManaged DD clusters with portfolio DD
  on same days, proving the "unique mechanism" thesis is wrong

**Monitoring flags:**
- Crisis DD: compare forward max DD to backtest $4,674
- Weight replication: compare live weights to what backtest would produce
- Long-bias interaction: track same-day DD clustering with portfolio
- Contribution: marginal Sharpe must remain positive

---

## Sparse Event Strategy Vitality Note

**Effective 2026-03-20.** Event strategies with `event_cadence.cadence_class
= "sparse_event"` use adjusted vitality weights:

- Backtest decay: 50% (up from 30%) — dominates when forward sample is tiny
- Forward deviation: 30% (down from 40%)
- Forward decay: 20% (down from 30%)

FADING alerts are suppressed until the strategy has accumulated ≥ 4 event
occurrences with forward trade data. This prevents false FADING alerts
during inter-event silence.

**Affected strategies:** TV-NFP-High-Low-Levels.
~~PreFOMC-Drift-Equity~~ was rejected 2026-03-17 per registry and
is no longer an active probation strategy; the vitality adjustment
below no longer applies to it.

Do not act on vitality FADING alerts for these strategies unless ≥ 4
event occurrences show declining PnL trend.

---

## Review Schedule

| Week | Action |
|------|--------|
| 1-2 | Observe only. No review triggers expected. |
| 3-4 | First checkpoint: are trades accumulating? Any anomalies? |
| 6 | Mid-point review: enough data to see early patterns? |
| 8 | Formal review: apply promotion/downgrade criteria above. |
| 12 | Final probation review: promote, extend, or remove each strategy. |

---

## Warning Signs (any strategy, any time)

Act immediately if ANY of these occur:

- **Kill switch fires** — investigate, do NOT disable kill switch
- **Forward PF < 0.5 after 20+ trades** — likely structural failure, downgrade immediately
- **3 strategies losing on same day** — check for correlated risk event
- **No trades for 2+ consecutive weeks** — check data feed, strategy logic, controller blocking
- **Drift monitor ALARM on probation strategy** — review whether backtest-to-forward divergence is real

---

## MCL Daily Long — Exploratory Lane

**Status:** Low-intensity background test, not a build cycle.

**Action:** Run `fx_daily_trend` on MCL through batch_first_pass with long-only mode.
If PF > 1.2 with stable walk-forward, draft a spec. Otherwise, log and move on.
Do not spend more than 30 minutes on this.
