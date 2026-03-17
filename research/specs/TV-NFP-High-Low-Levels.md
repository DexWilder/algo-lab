# Strategy Spec: TV-NFP-High-Low-Levels

## Hypothesis
The Non-Farm Payrolls release (first Friday of each month, 08:30 ET) creates a high-volatility session that establishes meaningful support and resistance levels. The NFP-day high and low become structural levels that price respects in subsequent trading days. A breakout beyond these levels — confirmed by consecutive closes — signals a sustained directional move driven by the market's digest of employment data.

## Event-Level Construction
- **NFP day:** First Friday of each month at 08:30 ET
- **NFP high:** Highest price from 08:30 ET through 16:00 ET on NFP day
- **NFP low:** Lowest price from 08:30 ET through 16:00 ET on NFP day
- These levels persist until the next NFP release (~1 month)
- Levels are recalculated fresh each NFP day

## Entry
- Condition 1: After NFP day is complete, carry the NFP high and NFP low forward
- Condition 2: Long when price has 2 consecutive daily closes above the NFP high (confirmed breakout above NFP resistance)
- Condition 3: Short when price has 2 consecutive daily closes below the NFP low (confirmed breakdown below NFP support)
- Condition 4: Only one entry per NFP cycle (until next NFP resets the levels)
- Direction: both

## Exit
- Target: next NFP release (exit before new levels are established)
- Stop: NFP midpoint (halfway between NFP high and NFP low) — if price falls back to the middle of the NFP range, the breakout thesis is invalidated
- Alternative stop: 1.5x ATR below entry for longs, above for shorts
- Time stop: exit 1 day before next NFP (avoid holding through the next event)

## Target Assets
- Primary: MES (S&P 500 — most liquid, most responsive to employment data)
- Test also: MNQ (Nasdaq — may show stronger/weaker NFP reaction)

## Parameters (initial)
- NFP_DAY: first Friday of each month (hardcoded calendar or day-of-week + week-of-month logic)
- NFP_SESSION_START: 08:30 ET
- NFP_SESSION_END: 16:00 ET
- CONFIRM_CLOSES: 2 (consecutive daily closes above/below NFP level)
- STOP_TYPE: "midpoint" (NFP range midpoint) or "atr" (1.5x ATR)
- ATR_LEN: 20
- SL_ATR_MULT: 1.5
- EXIT_BEFORE_NEXT_NFP: 1 day (exit day before next NFP)

## Source
- TradingView: "NFP High/Low Levels Plus" by rogman
- Public script, no private access required
- The concept treats NFP as a level-generator, not just a day-trade event

## Important Notes
- This is NOT an NFP-day scalp. It's a multi-day hold based on NFP-derived levels. The entry may come 2-10 days after NFP, once the breakout confirms.
- ~12 NFP events per year. Not every NFP will produce a confirmed breakout. Expect 6-10 trades per year (some months price stays inside the NFP range).
- With 6.7 years of MES data: ~40-65 potential trades. Adequate for first-pass but borderline for full validation.
- The 2-close confirmation filter is the quality gate. Without it, this would just be "trade around NFP levels" which is too vague.

## Diversification Role
- **Factor:** EVENT — macro employment release creates structural levels. The edge is in the EVENT creating the levels, not in price momentum.
- **Distinctness from PreFOMC:** Different event (employment vs rate decision), different mechanism (level breakout vs anticipation drift), different hold period (multi-day vs overnight). Zero overlap.
- **Session:** Multi-day hold triggered by daily closes (not intraday). Different session behavior from all existing strategies.
- **Expected contribution:** Builds EVENT sleeve breadth. Proves EVENT works across event types, not just FOMC. Adds a multi-day hold strategy alongside PreFOMC's overnight hold.
