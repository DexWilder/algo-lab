# TradingView Harvest Prompt: CARRY Factor Strategies

## Instructions for Claw / Research Assistant

Search TradingView's public script library for futures-compatible CARRY or macro-directional strategies. These use interest rate differentials, yield curve signals, macro regime indicators, or fundamental valuation as directional bias — not just price momentum.

## Search Terms (use these on TradingView)

1. "carry trade strategy"
2. "interest rate differential trading"
3. "yield curve strategy futures"
4. "macro momentum futures"
5. "bond futures trend following"
6. "treasury yield strategy"
7. "risk on risk off strategy"
8. "dollar strength strategy futures"
9. "gold macro strategy"
10. "commodity carry trade"
11. "term structure strategy futures"
12. "contango backwardation strategy"

## What to Look For

ACCEPT ideas that:
- Use interest rate levels or differentials as a directional signal
- Trade yield curve slope (2s10s, 5s30s) or term structure (contango/backwardation)
- Use macro regime indicators (risk-on/risk-off, dollar strength) as filters
- Work on futures: treasury futures (ZN, ZB, ZF), FX futures (6E, 6J, 6B), commodity futures (MCL, MGC)
- Operate on daily or weekly bars (carry signals are slow-moving by nature)
- Have a clear, testable rule — not just "follow the macro narrative"

REJECT ideas that:
- Are pure price-pattern momentum (trend following, breakout, EMA crossover) with no macro/rate signal
- Use carry language but are really just "buy the higher-yielding thing" without implementation detail
- Require live economic data feeds that FQL doesn't have (acceptable if a price-based proxy exists)
- Are crypto-only or equity-single-stock
- Are invite-only or paywalled
- Have no clear entry/exit rules

## IMPORTANT: Distinguish CARRY from MOMENTUM

A strategy is CARRY if the directional signal comes from RATES, YIELDS, or FUNDAMENTAL VALUE.
A strategy is MOMENTUM if the directional signal comes from PRICE TRENDS or TECHNICAL PATTERNS.

"Daily trend following on treasury futures" is MOMENTUM on rates, not CARRY.
"Long ZN when yield curve is inverted" is CARRY because the signal is the curve shape, not the price trend.

If a script is really just trend-following on bonds/FX, it is MOMENTUM. Apply the high-bar rule instead.

## Output Format

For each promising script, create a markdown file with this exact format:

```
- title: [Script name as shown on TradingView]
- source URL: [Full TradingView URL to the public script page]
- author: [TradingView username]
- target futures instruments: [CME symbols: ZN, ZB, ZF, 6E, 6J, 6B, MCL, MGC]
- timeframe: [daily, weekly, monthly]
- strategy family: carry / macro_directional / term_structure
- explicit entry idea: [Summarize entry logic in 1-3 sentences. Do NOT copy Pine code.]
- explicit exit idea: [Summarize exit logic in 1-2 sentences.]
- session logic: [Usually daily/weekly — note rebalance frequency]
- why it may fit FQL: [One line on why this fills the CARRY factor gap]
- notes: [Data requirements, whether a price-based proxy exists, implementation complexity]
```

## Rules

- Do NOT copy full Pine Script source code. Summarize the logic in plain English.
- Do NOT interact with TradingView (no follows, comments, likes, saves).
- Do NOT access any private, invite-only, or paywalled scripts.
- Each intake note goes into: ~/openclaw-intake/inbox/
- Filename format: tv_carry_[short_descriptor].md (e.g., tv_carry_yield_curve_zn.md)
- Maximum 8 notes per search session.
