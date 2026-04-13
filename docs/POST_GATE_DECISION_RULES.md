# Post-Gate Decision Rules

*What happens after the 20-trade review, based on outcomes.*

---

## Decision Tree

### If XB-ORB forward quality HOLDS (all 3 GO at 20 trades)

**Action:** Stay focused on the XB-ORB lane.
- Continue accumulating to 30-trade gate
- Do NOT open a new strategy family
- If all 3 remain strong at 30 trades, begin promotion engineering
  (intraday runner, order routing — see promotion checklist)

### If XB-ORB is MIXED (some GO, some EXTEND/DOWNGRADE)

**Action:** Maintain strong variants, open ONE new candidate.
- Continue strong variants to 30-trade gate
- EXTEND variants get tighter monitoring with same 30-trade gate
- DOWNGRADE variants move to WATCH (stop forward runner evidence)
- Open exactly one new gap-filling candidate:
  - **First choice:** TV-EOD-Sentiment-Flip (afternoon/close session gap)
  - **Second choice:** Top crossbreeding candidate (#1: Afternoon Pullback
    + EMA slope + profit ladder)
- Do NOT open multiple new lanes simultaneously

### If XB-ORB forward quality FAILS (all 3 DOWNGRADE)

**Action:** Fundamental reassessment.
- Archive all 3 XB-ORB variants from probation
- Review whether the edge has structurally decayed
- Open a controlled 3-candidate build wave:
  1. TV-EOD-Sentiment-Flip (different session, different mechanism)
  2. Top crossbreeding candidate
  3. Top CONVERT_NEXT idea (VWAPPullback-MES or IB-Breakout-Gold)
- Apply full house style gates to all new candidates

---

## Activation Path Priority

When ready to build the NEXT candidate (any scenario):

| Priority | Source | Rationale |
|----------|--------|-----------|
| **1** | Crossbreeding with proven donors | Higher hit rate than raw ideas (genealogy evidence) |
| **2** | TV-EOD-Sentiment-Flip | Fills biggest session gap (afternoon/close) |
| **3** | VWAPPullback-MES-Long | Strongest spec, documented edge, high density |
| **4** | IB-Breakout-Gold | Different mechanism, but overlap risk with ORB-MGC |

**Rule:** Prefer crossbreeding over raw conversion when both are available,
because the only validated winner came from recombination, not raw harvest.

---

## MYM-Specific Rules

MYM has less backtest evidence (340 trades / 2 years vs 900-1183 / 5-7 years).

- If MYM at 20 trades looks significantly weaker than MNQ/MCL:
  → Reclassify as MONITOR, not DOWNGRADE
  → It may be a sparser workhorse, not a failure
  → Only DOWNGRADE if forward PF < 0.85

- If MYM trade density is lower than expected (< 10/month vs 14 expected):
  → Flag as "slower cousin" — keep monitoring but adjust expectations
  → Do not hold it to the same density standard as MNQ

---

## What NOT to Do at Any Gate

- Do NOT open more than 1 new strategy lane at a time
- Do NOT start a broad conversion wave before resolving the current workhorses
- Do NOT change the running workhorse parameters based on 20 trades
- Do NOT start data expansion just because blocked ideas look interesting
- Do NOT rebuild the forward runner before promotion engineering is justified
