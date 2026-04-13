# XB-ORB 20-Trade Review Template

*Pre-defined decision packet. When any workhorse hits 20 forward trades,
this template generates the review automatically. No ad hoc analysis.*

---

## Review Trigger

When `fql probation-health` or `fql portfolio` shows a workhorse at
≥20 forward trades, run this review for that variant.

The review produces a GO / EXTEND / DOWNGRADE verdict.

---

## Section 1: Forward Performance Summary

| Metric | Forward | Backtest | Delta | Flag if |
|--------|---------|----------|-------|---------|
| PF | | | | Forward < 1.0 |
| Win Rate | | | | Delta > 10pp |
| Avg Winner | | | | |
| Avg Loser | | | | |
| Median Trade | | | | Forward < 0 |
| Total PnL | | | | |

**Hard fail:** Forward PF < 0.90 OR forward median trade < 0

---

## Section 2: Forward vs Backtest Alignment

### Entry Hour Distribution
Compare forward entry hours to backtest entry-hour histogram.
Flag if forward entries cluster in hours that represent < 5% of backtest.

### Hold Time Distribution
Compare forward median hold to backtest IQR.
Flag if forward median is outside [p25 × 0.5, p75 × 1.5].

### Long/Short Mix
| Direction | Forward % | Backtest % | Delta |
|-----------|-----------|-----------|-------|
| Long | | | |
| Short | | | |

Flag if delta > 20pp (direction bias drift).

---

## Section 3: Concentration Check (Forward Data)

| Metric | Forward | Threshold | Pass? |
|--------|---------|-----------|-------|
| Top-3 trades as % of PnL | | < 50% | |
| Max single trade as % of PnL | | < 30% | |
| Any month > 40% of PnL | | No | |

---

## Section 4: Behavioral Drift Flags

From `fql behavior` output:
- Total flags: __/__ trades flagged
- Consecutive flags: __ (downgrade warning if ≥ 3)
- Drift scoreboard trend: improving / stable / degrading

---

## Section 5: House Style Compliance

| Criterion | Pass? |
|-----------|-------|
| Dense entry (≥14 trades/month forward) | |
| Positive median trade | |
| Cross-asset (still profitable on siblings?) | |
| No single-trade dependence (top-1 < 30%) | |

---

## Section 6: MYM-Specific Cautions

*Only applies to XB-ORB-EMA-Ladder-MYM*

MYM has less backtest history (2y vs 5-7y for MNQ/MCL). Apply extra
scrutiny:

- Is forward trade density matching backtest expectation (~14/month)?
- Is the edge consistent or clustered in one period?
- Does it look like a real workhorse or a sparser cousin?

If MYM at 20 trades looks significantly weaker than MNQ/MCL at their
20-trade marks, **reclassify as MONITOR rather than continuing probation.**

---

## Decision Rules

### GO (continue to 30-trade gate)
All of these must hold:
- Forward PF ≥ 1.0
- Forward median trade ≥ 0
- Forward WR within 15pp of backtest
- < 30% of trades flagged for behavioral drift
- No single trade > 30% of total PnL
- No single month > 40% of total PnL

### EXTEND (keep in probation with caution)
- Forward PF between 0.85 and 1.0, OR
- WR delta > 15pp but < 25pp, OR
- 1-2 behavioral drift flags but no pattern
- Action: continue to 30 trades with closer monitoring

### DOWNGRADE (move to WATCH or ARCHIVE)
Any of these trigger:
- Forward PF < 0.85
- Forward median trade significantly negative
- WR delta > 25pp
- 3+ consecutive behavioral flags
- Forward trades clustered in one week (not continuous)
- Action: move to WATCH. If still failing at 30 trades, ARCHIVE.

---

## Post-Review Actions

After the 20-trade review:
1. Update registry with review_date, forward_pf, forward_wr
2. Set next gate (30 trades) with expected date
3. If any variant is DOWNGRADE, decide whether to replace with
   TV-EOD-Sentiment-Flip or a crossbreeding candidate
4. Document the decision in the trade log or registry notes
