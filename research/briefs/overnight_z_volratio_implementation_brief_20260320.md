# FQL Implementation Brief: Overnight Z-VolRatio Open-Drive

**Date:** 2026-03-20 (Friday)
**Status:** Implementation-grade spec for conversion
**Source:** TradingView — FoxchaseTrading, "Overnight Z-VolRatio Signal"
**Harvest note:** `2026-03-19_04_overnight_z_volratio_open_drive.md`

---

## Candidate Selection: Why This One First

### Head-to-Head: Overnight Z-VolRatio vs Treasury Cash-Close Reversion

| Dimension | Overnight Z-VolRatio | Treasury Cash-Close Reversion |
|-----------|---------------------|------------------------------|
| **Factor gap filled** | VOLATILITY (0 active, 0 probation) | STRUCTURAL (1 active: FXBreak-6J) |
| **Asset** | MES/MNQ (existing, deep data) | ZN/ZB (existing, but ZB data ends 15:25 — may miss 15:30 exit) |
| **Mechanism clarity** | High — z-score + volume ratio, mechanical | Medium — "exceeds 1.5x median move" + macro calendar exclusion |
| **Trade count expectation** | ~100-200/year (daily filter, not daily trade) | ~50-100/year (one 15m window per day) |
| **Data readiness** | Full — 187K overnight bars on MES, 6.7 years | Partial — ZB data may not cover the 15:00-15:30 exit window |
| **Portfolio usefulness** | VOLATILITY is the #2 gap (after CARRY) | STRUCTURAL has coverage via FXBreak-6J |
| **Overlap risk** | Low — overnight signal, not morning momentum | Low — rates close microstructure is unique |
| **Simplification risk** | Low — inputs are standard (range, volume) | Medium — macro release exclusion filter adds complexity |
| **Existing registry overlap** | 5 overnight/gap ideas exist but all REJECTED or MONITOR | No close-reversion ideas in registry |

### Decision: Overnight Z-VolRatio

**Reason:** VOLATILITY is the larger gap. The strategy has clearer
mechanism, higher expected trade count, cleaner data availability, and
no macro-calendar dependency. The overnight signal space has several
REJECTED strategies, but this candidate is explicitly differentiated —
it's a volatility-conditioned filter, not a raw overnight drift bet.
The prior rejections (Equity-Overnight-Drift PF 1.09, GapFill-M2K PF
0.68) failed because they were unconditional. This strategy's edge IS
the conditioning: only trade when overnight z-score AND volume ratio
confirm the move is real.

**Queue position for Treasury Cash-Close Reversion:** Next in line. If
Z-VolRatio ADVANCES, convert Treasury close reversion as a second rates-
native structural strategy. If Z-VolRatio is REJECTED, convert Treasury
close reversion as the primary next candidate.

---

## 1. Strategy Design

### 1a. Hypothesis

Overnight futures price action contains information about the next
session's direction, but most of the time this information is noise.
The key is filtering: when the overnight range is unusually large
(z-score > threshold) AND early-session volume confirms participation
(volume ratio > threshold), the overnight directional tilt has
follow-through value. Otherwise, it's noise and should be ignored.

This is a VOLATILITY strategy, not a MOMENTUM strategy. The edge is in
the volatility condition (large overnight move + volume confirmation),
not in price direction itself. The factor tag is VOLATILITY because the
signal fires on vol-expansion conditions and is silent during normal
volatility.

### 1b. Signal Logic

```
Inputs:
  overnight_range   = high - low from 18:00 ET to 09:30 ET (prior session)
  overnight_dir     = sign(close_09:30 - open_18:00)
  overnight_z       = (overnight_range - mean_20d) / std_20d
  volume_ratio      = volume_09:30_to_09:45 / mean_volume_09:30_to_09:45_20d

Signal:
  IF overnight_z > Z_THRESHOLD
     AND volume_ratio > VOL_THRESHOLD
     AND overnight_dir != 0:
    THEN entry = overnight_dir (long if overnight was up, short if down)
  ELSE:
    FLAT (no trade)

Entry:   09:45 ET (after 15-minute open confirmation window)
Exit:    11:00 ET fixed time exit (early-session window only)
         OR trailing stop at 1.5x ATR from entry
         OR target at 2x overnight range from entry
Stop:    1.5x ATR(20) from entry price
```

### 1c. Parameters (Initial)

```python
Z_THRESHOLD = 1.5          # Overnight range z-score threshold
VOL_THRESHOLD = 1.2        # Volume ratio threshold (1.2x normal)
OVERNIGHT_LOOKBACK = 20    # Days for z-score and volume ratio baseline
ATR_LEN = 20               # For stop/target calculation
SL_ATR_MULT = 1.5          # Stop distance
EXIT_TIME = "11:00"        # Fixed exit (ET)
ENTRY_TIME = "09:45"       # Entry after 15m confirmation
OVERNIGHT_START = "18:00"  # Prior day session close
OVERNIGHT_END = "09:30"    # RTH open
```

### 1d. Direction

**Both.** The signal is directional based on overnight tilt. Long when
overnight was up + conditions met, short when overnight was down +
conditions met. This is important — the existing portfolio is long-biased
(4 long-only strategies). A strategy that takes both sides based on
volatility conditions adds directional balance.

---

## 2. Required Data Fields

| Field | Source | Status |
|-------|--------|--------|
| MES/MNQ 5m OHLCV | `data/processed/{sym}_5m.csv` | Available — 187K overnight bars, 6.7 years |
| Overnight session bars (18:00-09:30 ET) | Derived from 5m data | Available — need timezone-aware session split |
| 20-day rolling overnight range mean/std | Computed in strategy | Available |
| 09:30-09:45 volume | Derived from 5m data | Available (3 bars) |
| 20-day rolling volume baseline | Computed in strategy | Available |
| 20-day ATR | Computed in strategy | Available |

**No new data required.** All inputs are derivable from existing 5m OHLCV.

---

## 3. Assumptions and Simplifications

| Assumption | Justification | Risk If Wrong |
|------------|---------------|---------------|
| Overnight range captures pre-session information | Institutional flow happens during overnight/globex session | If range is driven by low-liquidity noise, z-score will not predict direction |
| Volume ratio at 09:30-09:45 confirms participation | Early RTH volume reflects institutional engagement | If retail-dominated opens, volume ratio is not informative |
| Fixed 11:00 exit captures the open-drive window | Most open-drive follow-through exhausts within 60-90 minutes | May exit too early on strong trend days, too late on fast reversals |
| 20-day lookback for z-score baseline | Balances recency with stability | Shorter lookback (10d) may adapt faster to volatility regime changes |
| Z threshold of 1.5 is a reasonable starting point | ~7% of days exceed 1.5 std — selective enough to be meaningful | May need calibration — too high = too few trades, too low = too noisy |

### Simplifications Accepted for First Pass

1. **No macro calendar exclusion.** Unlike the Treasury close reversion
   candidate, this strategy does NOT need a macro release filter. The
   z-score threshold naturally captures macro release days (they produce
   large overnight ranges) and the volume filter confirms whether the
   market is engaged. This is a simplification advantage over the
   Treasury candidate.

2. **Fixed time exit.** No trailing target optimization in v1. Fixed
   11:00 ET exit keeps the strategy simple and testable. If the first-pass
   shows that most PnL comes from exits before 11:00, a tighter window
   can be tested in v2.

3. **Single z-score threshold for both directions.** Long and short use
   the same Z_THRESHOLD. If directional asymmetry exists (e.g., large
   down moves are more predictive than large up moves), a split threshold
   can be tested in v2.

---

## 4. Validation Battery

### 4a. Walk-Forward

| Test | Method | Pass Criteria |
|------|--------|---------------|
| Year splits | 50/50 time split (H1/H2) | Both halves PF > 1.0 |
| Rolling windows | 12-month rolling, 6-month step | >= 75% of windows PF > 1.0 |

### 4b. Cross-Regime

| Regime | Test Method | Pass Criteria |
|--------|-------------|---------------|
| Vol regime (LOW/NORMAL/HIGH) | Segment by ATR percentile | Edge present in HIGH_VOL and NORMAL; acceptable if weak in LOW_VOL |
| Trend regime (TRENDING/RANGING) | Segment by 20d EMA slope | No cell with >= 10 trades has PF < 0.5 |
| VIX proxy (ATR percentile as substitute) | Top/bottom quartile comparison | Top quartile (high vol) should outperform |

**Key expectation:** This strategy SHOULD perform better in high-vol
regimes and worse in low-vol. That's by design — it's a volatility-
conditioned signal. A flat result across vol regimes would suggest the
vol filter isn't working.

### 4c. Parameter Stability

| Parameter | Base | Perturbation Range | Pass Criteria |
|-----------|------|-------------------|---------------|
| Z_THRESHOLD | 1.5 | 1.0, 1.25, 1.75, 2.0 | >= 60% of variants PF > 1.0 |
| VOL_THRESHOLD | 1.2 | 0.8, 1.0, 1.4, 1.6 | >= 60% of variants PF > 1.0 |
| EXIT_TIME | 11:00 | 10:30, 10:45, 11:15, 11:30 | >= 60% of variants PF > 1.0 |
| SL_ATR_MULT | 1.5 | 1.0, 1.25, 2.0, 2.5 | >= 60% of variants PF > 1.0 |

### 4d. Asset Robustness

| Asset | Expected Behavior | Pass Criteria |
|-------|-------------------|---------------|
| MES | Primary — most liquid equity index micro | PF > 1.0 |
| MNQ | Secondary — higher beta, more volatile | PF > 1.0 |
| M2K | Tertiary — small cap, different microstructure | Informational |
| MGC | Cross-class check — should NOT work on metals | No requirement |

**If MES and MNQ both pass:** strategy is robust across equity indices.
**If only one passes:** single-asset variant, lower priority.

### 4e. Portfolio Contribution / Overlap

| Test | Method | Pass Criteria |
|------|--------|---------------|
| Factor overlap | Correlate daily PnL with portfolio | Correlation < 0.20 |
| Marginal Sharpe | Add to portfolio, measure delta | Delta >= 0 |
| Overnight drift decomposition | Compare to unconditional overnight drift (MONITOR PF 1.09) | Must show improvement over unconditional baseline |
| Session overlap | Check entry/exit times against existing strategies | Entry 09:45 overlaps with morning session — check crowding |

**Critical test: unconditional overnight drift comparison.** If this
strategy's PnL correlates > 0.7 with the simple unconditional overnight
drift (which was classified MONITOR at PF 1.09), the vol filter isn't
adding value and this is just overnight drift with extra steps.

---

## 5. Expected Portfolio Role

| Dimension | Value |
|-----------|-------|
| **Factor** | VOLATILITY (primary) — fills the #2 gap |
| **Role** | Workhorse or Diversifier (depends on trade count) |
| **Asset** | MES primary, MNQ secondary |
| **Session** | Overnight signal → morning execution (09:45-11:00 ET) |
| **Horizon** | Intraday (hold 75 minutes) |
| **Direction** | Both (long and short based on overnight tilt) |
| **Expected trades** | 40-80/year per asset (if ~15-20% of days clear both thresholds) |
| **Correlation** | Near zero with existing carry/event strategies; some overlap possible with morning momentum on same assets |

### Overlap Risk Assessment

| Strategy | Overlap Risk | Mitigation |
|----------|-------------|------------|
| ORB-MGC-Long | LOW — different asset (MGC vs MES/MNQ), different signal (opening range breakout vs overnight continuation) | None needed |
| VWAP-MNQ-Long | MEDIUM — same asset (MNQ), same session (morning), but different signal (VWAP vs overnight z-score) | Check PnL correlation; if > 0.35, flag |
| NoiseBoundary-MNQ-Long | MEDIUM — same asset (MNQ), morning session | Check PnL correlation |
| XB-PB-EMA-MES-Short | LOW — same asset (MES), but this is short-only and pullback-based | Different mechanism |

**Morning session concentration is the primary risk.** Adding another
MES/MNQ morning strategy pushes the morning session concentration higher.
The portfolio construction policy already flags morning session at "OVER"
(~8 strategies). This strategy should only be added if it demonstrates
genuine factor independence (VOLATILITY vs MOMENTUM).

### Probation Design

**Probation-only at first.** MICRO tier.

| Gate | Criterion | Timeline |
|------|-----------|----------|
| First-pass | PF > 1.2, trades >= 30, WF both halves > 1.0 | This week |
| Validation battery | >= 7/10, 0 hard failures | If ADVANCE |
| Conviction probation | 30 forward trades, PF > 1.2, vol-regime edge confirmed | ~3-6 months |
| Core promotion | Forward evidence, contribution confirmed positive | ~9-12 months |

---

## 6. Promotion Criteria

### Gate 1: First-Pass (batch_first_pass)

| Criterion | Threshold |
|-----------|-----------|
| Overall PF (both directions) | > 1.2 |
| Trade count | >= 30 |
| Walk-forward | Both halves PF > 1.0 |
| Classification | ADVANCE |

### Gate 2: Validation Battery

Standard 6-test suite. >= 7/10 with 0 hard failures.

### Gate 3: Conviction Probation

| Criterion | Threshold |
|-----------|-----------|
| Forward trades | >= 30 |
| Forward PF | > 1.2 |
| Forward Sharpe | > 0.8 |
| Vol-regime edge confirmed | PF higher in HIGH_VOL vs LOW_VOL forward |
| Morning session crowding check | PnL correlation < 0.35 with all MES/MNQ morning strategies |
| Max DD | < $3K single-strategy |

---

## 7. Next Candidate Queued

**Treasury Cash-Close Reversion Window** queues as the next convert-now
candidate. It should be converted when:
- Overnight Z-VolRatio completes first-pass (regardless of outcome)
- ZB data coverage of 15:00-15:30 window is verified
- A macro release calendar exclusion list is built (or the strategy is
  simplified to not require one)

Treasury close reversion fills a different gap (Rates STRUCTURAL) and
has zero overlap with the overnight z-volratio strategy. They can coexist
in the portfolio.

---

*Filed: `research/briefs/overnight_z_volratio_implementation_brief_20260320.md`*
*Registry impact: None yet — pending spec approval and conversion*
*Next step: Write spec → strategy.py → batch_first_pass*
