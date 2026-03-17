# Strategy Spec: Equity-Overnight-Drift

## Hypothesis
Equity index futures earn a disproportionate share of their total returns during overnight hours (close-to-open) rather than during regular trading hours (open-to-close). This "overnight drift" or "overnight premium" is one of the most documented structural anomalies in equity markets. The effect is attributed to risk premia for holding overnight uncertainty, after-hours earnings/news absorption, and institutional order flow at the open.

## Entry
- Condition 1: Buy at the last bar before regular session close (~15:55 ET)
- Condition 2: No directional filter — the hypothesis is that the overnight premium is positive on average regardless of trend or regime
- Condition 3: Entry every trading day (high frequency — ~250 trades/year)
- Direction: long only

## Exit
- Primary: sell at the first bar after regular session open (~09:35 ET next day)
- Alternative (v2 test): sell at 10:00 ET (let the opening auction settle before exiting)
- Stop: toggle — test with no stop (pure overnight hold) and with 1.5x ATR stop (protect against overnight crash)
- No trailing stop, no target — this is a fixed-window structural hold

## Holding Window
- Entry: ~15:55 ET
- Exit: ~09:35 ET next day (or 10:00 ET for v2)
- Hold duration: ~17.5 hours (overnight + pre-market)
- Exposure: overnight session only — zero exposure during regular trading hours
- This means zero overlap with ALL existing intraday strategies

## Assets
- Primary: MES (Micro E-mini S&P 500)
- Test also: MNQ (Micro Nasdaq — may show stronger or weaker overnight effect)

## Parameters (initial)
- ENTRY_HOUR: 15, ENTRY_MIN: 55 (last bar before close)
- EXIT_HOUR: 9, EXIT_MIN: 35 (first bar after open, let opening bar settle)
- EXIT_VARIANT: "open" (09:35) vs "settled" (10:00) — test both
- USE_STOP: toggle (True/False)
- ATR_LEN: 20
- SL_ATR_MULT: 1.5
- MIN_BARS_BETWEEN: 0 (trade every day)

## Source
- Academic: Cliff, Cooper, Gulen (2008) "Return Differences between Trading and Non-Trading Hours"
- Lou, Polk, Skouras (2019) "A Tug of War: Overnight Versus Intraday Expected Returns"
- Registry entry: Equity-Overnight-Drift, status=idea, STRUCTURAL priority #1

## Important Notes
- With ~250 trades per year and 6.7 years of MES data, we get ~1,600+ trades. This is by far the highest trade count of any expansion candidate.
- The high trade count means validation battery results will have strong statistical power.
- The overnight premium may have weakened in recent years as it became more widely known. Year-by-year analysis is critical.
- This strategy is the OPPOSITE of intraday strategies — it profits from holding when intraday strategies are flat. This is genuine structural diversification.

## Diversification Role
- **Factor:** Pure STRUCTURAL — the edge is in WHEN you hold (overnight), not WHICH DIRECTION price moves
- **Correlation to existing portfolio:** Should be very low or slightly negative. All existing strategies trade during regular hours and are flat overnight. This strategy is long overnight and flat during regular hours.
- **Session:** Overnight only (15:55 ET to 09:35 ET) — zero session overlap with any existing strategy
- **Expected contribution:** Adds return during hours when the entire rest of the portfolio is idle. If the overnight premium exists, this is "free" diversification.
