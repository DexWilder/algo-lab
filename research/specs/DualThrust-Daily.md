# Strategy Spec: DualThrust-Daily

## Hypothesis
DualThrust is a classic CTA range-based breakout system widely used by professional commodity trading advisors. It defines a dynamic range from the previous day's OHLC, then trades breakouts of that range on the current day. Unlike fixed-channel breakouts (Donchian), DualThrust adapts its trigger levels daily based on recent price action, making it responsive to changing volatility. It operates on daily bars and is designed to be portable across liquid futures.

## Entry
- Condition 1: Compute the previous N days' range metrics:
  - HH = highest high of last N days
  - HC = highest close of last N days
  - LC = lowest close of last N days
  - LL = lowest low of last N days
- Condition 2: Range = max(HH - LC, HC - LL)
- Condition 3: Buy trigger = today's open + K1 * Range
- Condition 4: Sell trigger = today's open - K2 * Range
- Condition 5: Long if close > buy trigger; Short if close < sell trigger
- Direction: both

## Exit
- Trail: 2.0x ATR(20) trailing stop
- No fixed target (let trends run, similar to MGC daily trend)
- Trend reversal: exit long if close < sell trigger; exit short if close > buy trigger (range flip)
- No time stop (daily-bar holds, position carried until stopped or flipped)

## Session
- Daily bars (resampled from 5m internally)
- Signals generated at daily close
- Position held until trail, flip, or stop

## Assets
- Primary: test across all assets with data (MES, MNQ, MGC, M2K, MCL, ZN, ZB, ZF, 6E, 6J, 6B)
- This is a generic CTA system — the whole point is multi-asset portability

## Parameters (initial)
- N_DAYS: 4 (lookback for range calculation — classic DualThrust default)
- K1: 0.5 (buy trigger multiplier)
- K2: 0.5 (sell trigger multiplier — symmetric initially)
- ATR_LEN: 20
- TRAIL_ATR_MULT: 2.0

## Source
- DualThrust is a well-documented CTA system, widely attributed to Michael Chalek
- Used by systematic commodity funds since the 1990s
- Registry notes: "Widely used by CTAs. Better as daily overlay."
- One of the most tested daily range breakout systems in futures literature

## Diversification Role
- **Asset class:** Multi-asset by design (the key value of this strategy)
- **Family:** Daily range breakout (different from Donchian — adaptive range, not fixed channel)
- **Horizon:** Daily bars (multi-horizon lane)
- **Expected contribution:** If it works on even 3-4 assets, it adds multiple independent bets from a single strategy family. The CTA origin means it's designed for the exact instrument types FQL trades.
