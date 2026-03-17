# TradingView Harvest Prompt: STRUCTURAL Factor Strategies

## Instructions for Claw / Research Assistant

Search TradingView's public script library for futures-compatible STRUCTURAL strategies. These exploit session transitions, overnight gaps, closing mechanics, or time-of-day microstructure — not directional momentum or trend following.

## Search Terms (use these on TradingView)

1. "session breakout futures"
2. "London open breakout strategy"
3. "Asian session range breakout"
4. "overnight gap strategy futures"
5. "closing range strategy futures"
6. "afternoon mean reversion futures"
7. "end of day strategy futures"
8. "opening range breakout futures"
9. "session transition strategy"
10. "overnight drift equity futures"
11. "power hour strategy futures"
12. "market on close strategy"

## What to Look For

ACCEPT ideas that:
- Trade specific session transitions (Asia→London, London→NY, close, overnight)
- Exploit time-of-day patterns (overnight premium, closing auction, afternoon reversion)
- Use range-based logic anchored to session boundaries (Asian range, London range, OR)
- Work on futures or are clearly adaptable (ES, NQ, GC, CL, ZN, ZB, 6E, 6J)
- Are genuinely different from simple breakout/momentum (the edge is in the SESSION STRUCTURE, not the direction)

REJECT ideas that:
- Are generic momentum or trend strategies with no session-specific logic
- Are morning ORB on equity indices (FQL already has 13+ morning breakout strategies — AVOID)
- Are ICT/SMC concepts (FQL AVOID list)
- Are crypto-only or forex-spot-only
- Have no clear entry/exit rules
- Are invite-only or paywalled

## IMPORTANT: Distinguish STRUCTURAL from MOMENTUM

A strategy is STRUCTURAL if the edge comes from WHEN it trades (session timing, overnight hold, closing mechanics).
A strategy is MOMENTUM if the edge comes from WHICH DIRECTION price is moving (trend, breakout, continuation).

If a script is really just "breakout in the morning" with no session-specific logic, it is MOMENTUM, not STRUCTURAL. Reject it.

## Output Format

For each promising script, create a markdown file with this exact format:

```
- title: [Script name as shown on TradingView]
- source URL: [Full TradingView URL to the public script page]
- author: [TradingView username]
- target futures instruments: [CME symbols: MES, MNQ, MGC, MCL, ZN, ZB, 6E, 6J]
- timeframe: [1m, 5m, 15m, 1H, daily, etc.]
- strategy family: structural / session_transition
- explicit entry idea: [Summarize entry logic in 1-3 sentences. Do NOT copy Pine code.]
- explicit exit idea: [Summarize exit logic in 1-2 sentences.]
- session logic: [Specific session windows, time-of-day rules, overnight holds]
- why it may fit FQL: [One line on why this fills the STRUCTURAL factor gap]
- notes: [Caveats, how it differs from existing FQL session strategies, adaptation needed]
```

## Rules

- Do NOT copy full Pine Script source code. Summarize the logic in plain English.
- Do NOT interact with TradingView (no follows, comments, likes, saves).
- Do NOT access any private, invite-only, or paywalled scripts.
- Each intake note goes into: ~/openclaw-intake/inbox/
- Filename format: tv_structural_[short_descriptor].md (e.g., tv_structural_london_close_fade.md)
- Maximum 8 notes per search session.
