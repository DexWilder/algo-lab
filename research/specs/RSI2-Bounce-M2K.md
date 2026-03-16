# Strategy Spec: RSI2-Bounce-M2K

## Hypothesis
Russell 2000 micro futures exhibit a strong mean-reversion pattern when RSI(2) reaches extreme oversold levels intraday. Thin M2K liquidity amplifies short-term overshoots beyond fair value, and institutional rebalancing creates systematic reversion. RSI(2) on equities has documented 78%+ win rates in academic and practitioner literature (Connors, Alvarez).

## Entry
- Condition 1: RSI(2) < 10 on 5-minute bars (extreme oversold)
- Condition 2: Price is above 200-bar EMA (only buy dips in uptrends — avoid catching falling knives)
- Condition 3: Close is below 20-bar EMA (confirms the dip has actually happened)
- Direction: long only (mean-reversion long is the documented edge; short-side RSI(2) is weaker on equities)

## Exit
- Target: close above 20-bar EMA (price has reverted to short-term mean)
- Stop: 2.0x ATR(20) below entry (protect against trend continuation)
- Time stop: 30 bars (2.5 hours) — if it hasn't reverted by then, the thesis is wrong
- No trailing stop (mean-reversion exits should be crisp, not trailed)

## Session
- Entry window: 09:45-14:30 ET (avoid the first 15 minutes of noise, exit before close dynamics)
- Flatten: 15:00 ET (no overnight holds)
- RSI and EMA computed on full session data

## Assets
- Primary: M2K (Micro Russell 2000)
- Test also: MES (S&P equivalent — check if M2K-specific or broad equity MR), MNQ (Nasdaq — typically less mean-reverting)

## Parameters (initial)
- RSI_LEN: 2 (ultra-short RSI for oversold detection)
- RSI_ENTRY_THRESH: 10 (extreme oversold)
- TREND_EMA_LEN: 200 (uptrend filter)
- PULLBACK_EMA_LEN: 20 (short-term mean for dip confirmation and exit target)
- ATR_LEN: 20
- SL_ATR_MULT: 2.0
- MAX_HOLD_BARS: 30 (2.5 hour time stop)
- ENTRY_START: "09:45"
- ENTRY_END: "14:30"
- FLATTEN: "15:00"
- MIN_BARS_BETWEEN: 6 (30 min cooldown)

## Source
- Connors & Alvarez: "Short Term Trading Strategies That Work" — RSI(2) < 10 on SPY documented at 78%+ win rate
- M2K-specific adaptation: Russell 2000 has thinner liquidity and wider spreads than ES/NQ, which amplifies overshoots and makes mean-reversion more pronounced
- Registry notes: "M2K-specific microstructure edge. Russell 2000 has documented RSI(2) oversold bounce"

## Diversification Role
- **Asset class:** Equity index (same as MES/MNQ but Russell 2000 is less correlated to large-cap, r~0.75-0.90)
- **Family:** Mean reversion (different entry mechanism from all current active strategies which are momentum/breakout/trend)
- **Session:** US RTH (overlaps with existing strategies, but different entry trigger)
- **Expected contribution:** Adds mean-reversion exposure to a portfolio currently dominated by momentum and breakout families. MR strategies typically profit in ranging/choppy markets where trend strategies lose — genuine behavioral diversification.
