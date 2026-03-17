# TradingView Harvest Prompt: EVENT Factor Strategies

## Instructions for Claw / Research Assistant

Search TradingView's public script library for futures-compatible EVENT-driven trading strategies. These are calendar-driven or news-reaction strategies that fire on specific dates or around scheduled economic releases.

## Search Terms (use these on TradingView)

1. "FOMC strategy futures"
2. "CPI trading strategy"
3. "NFP nonfarm payrolls strategy"
4. "economic calendar trading"
5. "event driven futures"
6. "FOMC drift"
7. "pre announcement drift"
8. "options expiration strategy futures"
9. "OPEX week trading"
10. "inventory report crude oil strategy"
11. "fed announcement trading system"
12. "macro event reaction futures"

## What to Look For

ACCEPT ideas that:
- Trade around specific scheduled events (FOMC, CPI, NFP, OPEX, EIA, etc.)
- Have clear entry timing relative to the event (before, during, or after)
- Work on futures or are adaptable to futures (ES, NQ, GC, CL, ZN, ZB, 6E, 6J)
- Have documented rules, not just "watch the chart around events"

REJECT ideas that:
- Are pure momentum/trend following with no event trigger
- Require real-time news feed or sentiment data
- Are crypto-only or forex-spot-only without futures applicability
- Are invite-only or paywalled scripts
- Have no clear entry/exit rules

## Output Format

For each promising script, create a markdown file with this exact format:

```
- title: [Script name as shown on TradingView]
- source URL: [Full TradingView URL to the public script page]
- author: [TradingView username]
- target futures instruments: [What assets — use CME symbols: MES, MNQ, MGC, MCL, ZN, ZB, 6E, 6J]
- timeframe: [1m, 5m, 15m, 1H, daily, etc.]
- strategy family: event_driven
- explicit entry idea: [Summarize the entry logic in 1-3 sentences. Do NOT copy Pine code.]
- explicit exit idea: [Summarize the exit logic in 1-2 sentences.]
- session logic: [Any time-of-day or calendar restrictions]
- why it may fit FQL: [One line on why this fills the EVENT factor gap]
- notes: [Caveats, sample size concerns, adaptation needed for futures, or quality flags]
```

## Rules

- Do NOT copy full Pine Script source code. Summarize the logic in plain English.
- Do NOT interact with TradingView (no follows, comments, likes, saves).
- Do NOT access any private, invite-only, or paywalled scripts.
- Each intake note goes into: ~/openclaw-intake/inbox/
- Filename format: tv_event_[short_descriptor].md (e.g., tv_event_fomc_drift_nq.md)
- Maximum 8 notes per search session.
