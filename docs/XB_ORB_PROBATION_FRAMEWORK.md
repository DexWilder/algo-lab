# XB-ORB Probation Framework

*Established 2026-04-13. Governs all XB-ORB-EMA-Ladder probation variants.*

## Active Variants

| ID | Asset | Backtest PF | Backtest Trades | Promoted | Data Window |
|----|-------|-------------|-----------------|----------|-------------|
| XB-ORB-EMA-Ladder-MNQ | MNQ | 1.62 | 1183 | 2026-04-06 | 6.8y |
| XB-ORB-EMA-Ladder-MCL | MCL | 1.33 | 898 | 2026-04-08 | 4.7y |
| XB-ORB-EMA-Ladder-MYM | MYM | 1.67 | 340 | 2026-04-13 | 2.0y |

All use identical code: `strategies/xb_orb_ema_ladder/strategy.py` with
`stop_mult=2.0` baseline.

---

## Review Schedule

### Minimum forward trades before first formal review

| Variant | Min Trades | Expected Time to Gate |
|---------|-----------|----------------------|
| MNQ | 30 | ~2 months (14/month) |
| MCL | 30 | ~2 months (15/month) |
| MYM | 30 | ~2 months (14/month) |

**No statistical conclusions before 30 forward trades.** Early behavior
tracking is qualitative only (alignment checks, not pass/fail).

### Weekly check (every Friday, automated)

- Forward trade count and cumulative PnL
- Behavioral alignment score (% trades flagged)
- Any new drift signals
- No action expected unless flags accumulate

### Formal review gates

| Gate | Trigger | Action |
|------|---------|--------|
| **20 trades** | First meaningful sample | Check WR, hold time, direction mix vs backtest. Flag but do not act. |
| **30 trades** | First formal review | Full assessment: PF, WR, concentration, drift. Decide: continue / extend / downgrade. |
| **50 trades** | Mid-probation | Second review. Compare to backtest PF with confidence bands. |
| **100 trades** | Promotion gate | Full statistical comparison. Promote to core or archive. |

---

## Promotion Criteria (at 100+ trades)

All of these must hold:

1. **Forward PF ≥ 1.15** (backtest PFs range 1.33-1.67; forward should be at least ~70% of backtest)
2. **Forward win rate within 10pp of backtest** (MNQ backtest: 61%, so forward ≥ 51%)
3. **No behavioral drift** — <20% of trades flagged in behavior tracker
4. **Positive median forward trade** (same as backtest requirement)
5. **No single month > 40% of forward PnL** (concentration check on forward data)
6. **Max forward drawdown duration < 60 trading days** (~3 calendar months)

If all pass → **PROMOTE TO CORE**.

---

## Downgrade Criteria

### Immediate downgrade to WATCH (any one triggers):

- Forward PF < 0.90 after 30+ trades
- Forward WR < 40% (vs backtest 56-61%)
- 3+ consecutive behavioral flags
- Max drawdown exceeds 2× backtest max DD
- Zero trades for 20+ trading days (signal generation broken)

### Immediate ARCHIVE (any one triggers):

- Forward PF < 0.80 after 50+ trades
- Edge vitality tier reaches DEAD
- Forward median trade becomes negative after 30+ trades

---

## Behavioral Flag Criteria

A forward trade is flagged if ANY of these are true:

| Flag | Threshold |
|------|-----------|
| Entry hour never seen in backtest | entry_hour not in backtest distribution |
| Entry hour rare | <10 backtest trades at that hour |
| Hold too short | < 50% of backtest p25 |
| Hold too long | > 150% of backtest p75 |
| Loss too large | loss exceeds 1.5× backtest p10 |
| Win too large | win exceeds 2× backtest p90 |

Individual flags are normal variance. **3+ consecutive flags** triggers
a downgrade warning.

---

## Daily Digest Content

The operator digest should show for XB-ORB workhorses:

```
XB-ORB Portfolio: 3 trades, +$429 | MNQ 1t +$241 | MCL 2t +$188 | MYM 0t
Behavior: 3/3 ALIGNED | Next review: 30 trades (~May 2026)
```

---

## Weekly Summary Content

Friday review should show:

| Variant | Fwd Trades | Fwd PnL | Fwd WR | BT WR | Flags | Status |
|---------|-----------|---------|--------|-------|-------|--------|
| MNQ | N | $X | X% | 61% | N/M | ON_TRACK |
| MCL | N | $X | X% | 57% | N/M | ON_TRACK |
| MYM | N | $X | X% | 56% | N/M | ON_TRACK |

---

## Promotion Engineering Checklist

Before any strategy advances from probation to core with real capital,
ALL of the following must be verified:

| Gate | Current State | Required for Core |
|------|--------------|-------------------|
| **Forward evidence** | Paper batch (17:00 ET daily) | Same — evidence is valid |
| **Intraday runner** | ❌ Not built | ✅ Required: processes new 5m bars during session, tracks last_processed timestamps, avoids duplicates, supports real-time signal alerting |
| **Order routing** | ❌ Not built | ✅ Required: connects signals to broker API for execution |
| **Position management** | ❌ Not built | ✅ Required: tracks open positions, prevents double-entry |
| **Risk controls** | ❌ Not built | ✅ Required: max position size, daily loss limit, kill switch |

**IMPORTANT:** The current once-daily batch runner at 17:00 ET is correct
for paper forward evidence collection. It processes all 5-minute bars in
sequence and produces identical signals/trades to real-time processing.
The evidence quality is research-valid.

However, the batch runner CANNOT be used for live execution — it processes
bars after the fact, not at signal time. The intraday runner is a gated
engineering requirement for core promotion, not a current deficiency.

**Do not blur these layers:**
- Research-valid evidence → current batch runner ✅
- Paper-forward monitoring → current batch runner ✅
- Live execution readiness → requires intraday runner ❌ (build when needed)

---

## What This Framework Does NOT Cover

- **Non-XB-ORB probation strategies** (DailyTrend-MGC, MomPB-6J, etc.)
  have their own criteria in `docs/PROBATION_REVIEW_CRITERIA.md`
- **New XB-ORB asset expansions** — the autocorrelation doctrine governs
  which assets to test. This framework governs what happens after promotion.
- **Parameter changes** — the stop_mult=2.0 baseline is locked during
  probation. No mid-probation parameter changes unless forward data reveals
  a clear structural issue.
