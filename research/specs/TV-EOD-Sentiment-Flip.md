# Strategy Spec: TV-EOD-Sentiment-Flip

## Hypothesis
End-of-day positioning near the close (~15:55 ET) reveals institutional sentiment for the overnight session. By scoring the current day's price action relative to the prior day's range, prior close, and close-location value, we can identify whether the session ended with bullish or bearish positioning bias. A clearly bullish or bearish end-of-day score predicts the direction of the overnight move (close-to-open).

This is a STRUCTURAL strategy — the edge is in the close-session microstructure and overnight positioning dynamics, not in price momentum.

## Signal Construction
Score the end-of-day state at 15:55 ET using three components:

1. **Close vs prior day's range:**
   - Close above prior high → +1 (bullish expansion day)
   - Close in upper half of prior range → +0.5
   - Close in lower half of prior range → -0.5
   - Close below prior low → -1 (bearish expansion day)

2. **Close vs prior close:**
   - Close > prior close → +0.5
   - Close < prior close → -0.5

3. **Close location value (CLV):**
   - CLV = (close - low) / (high - low) for today's session
   - CLV > 0.7 → +0.5 (closed near highs — bullish)
   - CLV < 0.3 → -0.5 (closed near lows — bearish)
   - Otherwise → 0

**Composite score:** sum of all three components (range: -2.0 to +2.0)
- Score >= +1.0 → bullish overnight bias → long
- Score <= -1.0 → bearish overnight bias → short
- Score between -1.0 and +1.0 → neutral → no trade

## Entry
- Condition 1: Evaluate composite score at 15:55 ET
- Condition 2: Score >= +1.0 → enter long; Score <= -1.0 → enter short
- Condition 3: One trade per day maximum
- Direction: both (directional based on score)

## Exit
- Primary: next day's RTH open (~09:35 ET) — overnight hold only
- Stop: toggle (none vs 1.5x ATR from entry)
- No trailing stop, no target — fixed close-to-open window

## Target Assets
- Primary: MES (S&P — most institutional close activity)
- Secondary: MNQ (Nasdaq — may show different close dynamics)

## Parameters (initial)
- EVAL_HOUR: 15, EVAL_MIN: 55
- EXIT_HOUR: 9, EXIT_MIN: 35
- SCORE_LONG_THRESHOLD: 1.0 (minimum bullish score to enter)
- SCORE_SHORT_THRESHOLD: -1.0 (minimum bearish score to enter)
- USE_STOP: toggle (True/False)
- ATR_LEN: 20
- SL_ATR_MULT: 1.5

## Source
- TradingView: "QQQ EOD Sentiment + Flip Points" by Papertradesbyaj
- Public script, QQQ-focused but portable to futures

## Key Failure Mode to Watch
- **Overlap with Equity-Overnight-Drift:** The overnight drift (MONITOR, PF 1.09) showed a weak positive overnight premium. This strategy adds a FILTER (score threshold) — only trading when the close-session sentiment is clearly directional. If the filter improves the overnight drift, the value is in the filtering, not the overnight premium itself.
- **Score threshold sensitivity:** If most days score neutral (no trade), the trade count could be too low. If most days score extreme, the filter isn't selective enough.
- **Bear market behavior:** Close-session sentiment in bear markets may consistently score bearish, which would make the short side profitable but regime-dependent.

## Important Notes
- This is similar in structure to Equity-Overnight-Drift (close-to-open hold) but adds a quality filter based on close-session price positioning. The overnight drift was MONITOR at PF 1.09 — this tests whether filtering by end-of-day sentiment improves the edge.
- The scoring system is simple enough to avoid overfitting but complex enough to differentiate from a random overnight hold.
- With ~250 trading days/year, expect 40-60% to score extreme enough to trade (~100-150 trades per year).

## Diversification Role
- **Factor:** STRUCTURAL — close-session microstructure determines overnight bias
- **Session:** Close-to-open (15:55 → 09:35 next day) — overnight hold, different from all intraday strategies
- **Correlation to existing:** Should be low — this fires based on end-of-day positioning, not intraday momentum or breakout
- **Expected contribution:** Improves on the weak overnight drift by adding a structural quality filter. If it works, it validates that the overnight premium is real but needs to be filtered, not traded blind.
