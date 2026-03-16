# Strategy Spec: NR7-Breakout

## Hypothesis
When a bar's range (high minus low) is the narrowest of the last 7 bars (NR7 pattern), it signals volatility compression that often precedes a directional expansion. This is one of the oldest documented short-term patterns (Crabel, 1990) and works across liquid futures markets. The entry trades the breakout from the NR7 bar's range.

## Entry
- Condition 1: Identify NR7 — current bar's range is the smallest of the last 7 bars
- Condition 2: On the NEXT bar after NR7 is detected, arm for breakout
- Condition 3: Long if price closes above the NR7 bar's high; Short if price closes below the NR7 bar's low
- Condition 4: ATR filter — NR7 bar range must be < 0.6x ATR(20) (confirm true compression, not just a normal small bar)
- Direction: both

## Exit
- Stop: opposite side of the NR7 bar range + 0.5x ATR(20) buffer
- Target: 2.0x ATR(20) from entry (volatility expansion targets)
- Trail: after 1.0R profit, trail at 1.0x ATR below best close (longs) / above worst close (shorts)
- Time stop: 24 bars (2 hours) — compression breakout should resolve within 1-2 hours
- Flatten: 15:00 ET

## Session
- NR7 detection: anytime during RTH (09:30-15:30 ET)
- Entry: bar immediately following NR7 detection
- Entry window: 09:45-14:30 ET (avoid first 15 min noise and late-day)
- Flatten: 15:00 ET
- No overnight holds

## Assets
- Primary: M2K (Micro Russell 2000 — thinner liquidity amplifies compression/expansion)
- Test also: MES, MNQ (broader indices for comparison)

## Parameters (initial)
- NR_LOOKBACK: 7 (classic NR7)
- COMPRESSION_ATR_MAX: 0.6 (NR7 bar range must be < 0.6x ATR — true compression)
- ATR_LEN: 20
- SL_BUFFER_ATR: 0.5 (stop buffer beyond NR7 range)
- TP_ATR_MULT: 2.0
- TRAIL_ACTIVATION_R: 1.0
- TRAIL_ATR_MULT: 1.0
- MAX_HOLD_BARS: 24
- MIN_BARS_BETWEEN: 6
- ENTRY_START: "09:45"
- ENTRY_END: "14:30"
- FLATTEN: "15:00"

## Source
- Crabel, Toby: "Day Trading with Short Term Price Patterns and Opening Range Breakout" (1990)
- NR7 is one of the most tested short-term volatility patterns in futures literature
- Registry notes: "Classic Crabel contraction signal. Pairs well with squeeze strategies. Tier 2 candidate."

## Diversification Role
- **Asset class:** Equity index (M2K primary, multi-asset testable)
- **Family:** Volatility expansion (same family as bbkc_squeeze and ttm_squeeze but different detection method — range-based vs indicator-based)
- **Session:** Any time during RTH (not concentrated in morning like ORB)
- **Expected contribution:** Fires throughout the day when compression is detected, not tied to session open. Different timing from ORB (opening), VWAP (pullback), or momentum (trending). High trade count expected (~150-300 per year) because NR7 patterns are common. Value is in the breakout direction call, not rarity.
