# Standby Candidate: TV-EOD-Sentiment-Flip

*Pre-assessed and ready for immediate build when the system gives permission.*

---

## What It Actually Is

An **overnight directional bias trade**, not a pure close-session intraday strategy.

At 3:55 PM ET, score end-of-day positioning using:
- Prior day's range
- Prior close level
- Close-location value (CLV = where price closes within the day's range)
- Directional score → bullish, bearish, or neutral

If score is clearly directional → enter overnight hold.
If neutral → stay flat.
Exit on next session open or if overnight bias fails early.

**Important:** This is a close-to-open trade, not a close-within-session trade.
The session gap it fills is "overnight directional" not "afternoon intraday."

---

## Spec Assessment

### What's clear
- Entry timing: 3:55 PM ET (very precise)
- Assets: MES, MNQ (portable to any equity micro)
- Direction: both (long, short, or flat based on score)
- Exit: next session open (simple)

### What needs specification before build
- **Scoring formula:** The TradingView script uses CLV + prior range + prior
  close, but exact weights and thresholds are not published. Will need to
  reverse-engineer from the script or design a reasonable proxy.
- **Flip threshold:** What score value triggers long vs short vs flat?
- **Overnight gap risk:** How to handle gap opens that immediately invalidate?
- **Holding period:** Is it always to next open, or does it have an early exit?

### Estimated build effort
- Medium — scoring formula needs design, but entry/exit structure is simple
- ~2-3 hours including first-pass testing

---

## Portfolio Fit

### What it fills
- **Session gap:** overnight directional (currently uncovered)
- **Mechanism gap:** CLV/sentiment scoring (different from ORB/breakout)
- **Timing gap:** 15:55 ET entry (no existing strategy enters this late)

### Overlap risk: MODERATE

⚠️ **Closed family warning:** "Overnight equity premium" is a closed family
in FQL (PF 1.03-1.09, "too weak standalone"). This strategy IS an overnight
equity hold, but with a directional filter (sentiment score).

**Key difference from closed family:**
- Overnight premium = always long (captures premium)
- This strategy = directional (long OR short based on CLV score)
- If the directional filter genuinely adds value, it's a different mechanism
- If the filter doesn't add value, it's the same closed family in disguise

**Mitigation:** When building, explicitly test:
1. Long-only variant (is it just capturing overnight premium?)
2. Short-only variant (does short overnight work at all?)
3. Both-direction variant (does the score actually predict direction?)

If the long-only variant has PF ~1.05 and the score doesn't improve it,
this IS the closed family and should be rejected immediately.

---

## Expected Trade Density

- ~250 trading days/year
- If score is neutral ~30-40% of days → ~150-175 trades/year
- Over 6.8 years of MES data → ~1000-1200 trades
- **Above the 500-trade workhorse threshold** if density holds

---

## Validation Plan (when activated)

1. Build scoring formula (CLV + range + prior close)
2. First-pass on MES and MNQ
3. **Immediately check:** is long-only PF similar to overnight premium (1.03-1.09)?
   If yes → closed family, reject without further work.
4. If score adds real directional value → full concentration gate battery
5. Cross-asset test on M2K, MYM
6. If all gates pass → probation

---

## Decision: When to Activate

Activate TV-EOD-Sentiment-Flip when ANY of these triggers:
- XB-ORB 20-trade review produces a MIXED or FAIL outcome
- All 3 XB-ORB workhorses reach 30-trade gate and the portfolio
  needs diversification beyond the ORB family
- Weekly audit identifies afternoon/overnight as the priority gap

Do NOT activate:
- While all 3 XB-ORB workhorses are accumulating cleanly
- Just because it's "interesting" or "the top-ranked idea"
- Before the closed-family risk is explicitly addressed in the build
