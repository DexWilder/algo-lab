# Probation Strategy Review Criteria

*Forward evidence thresholds for promotion, continuation, and removal.*
*Effective: 2026-03-17 onward*

---

## Active Probation Strategies

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

### 2. MomPB-6J-Long-US

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

### 3. FXBreak-6J-Short-London

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

### 6. Treasury-Rolldown-Carry-Spread (Active Carry Challenger)

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

## Sparse Event Strategy Vitality Note

**Effective 2026-03-20.** Event strategies with `event_cadence.cadence_class
= "sparse_event"` use adjusted vitality weights:

- Backtest decay: 50% (up from 30%) — dominates when forward sample is tiny
- Forward deviation: 30% (down from 40%)
- Forward decay: 20% (down from 30%)

FADING alerts are suppressed until the strategy has accumulated ≥ 4 event
occurrences with forward trade data. This prevents false FADING alerts
during inter-event silence.

**Affected strategies:** TV-NFP-High-Low-Levels, PreFOMC-Drift-Equity.

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
