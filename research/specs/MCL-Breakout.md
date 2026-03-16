# Strategy Spec: MCL-Breakout

## Hypothesis
Crude oil micro futures exhibit strong intraday momentum after breaking out of the opening range, driven by energy sector news flow, inventory positioning, and institutional order clustering in the first 1-2 hours of the NYMEX session.

## Entry
- Condition 1: Define opening range as first 30 minutes of NYMEX session (09:00-09:30 ET)
- Condition 2: Long on close above OR high; Short on close below OR low
- Condition 3: ATR filter — opening range must be between 0.3x and 2.5x ATR(20) (not too tight, not already extended)
- Condition 4: Volume confirmation — bar volume > 1.2x rolling 50-bar average at breakout
- Direction: both

## Exit
- Stop: 1.5x ATR(20) beyond the opposite side of the opening range
- Target: 2.0x ATR(20) from entry (crude tends to extend hard on breakout days)
- Trail: after 1.5R profit, trail at 1.0x ATR below best close (longs) or above worst close (shorts)
- Time stop: flatten at 14:00 ET (before NYMEX settlement activity)

## Session
- Opening range: 09:00-09:30 ET (NYMEX open)
- Entry window: 09:30-12:00 ET (allow breakout within first 3 hours)
- Flatten: 14:00 ET
- No overnight holds

## Assets
- Primary: MCL (Micro Crude Oil)
- Test also: MGC (different commodity, structural comparison)

## Parameters (initial)
- OR_MINUTES: 30 (opening range window)
- OR_START: "09:00" (NYMEX session start)
- ATR_LEN: 20
- ATR_RANGE_MIN: 0.3 (OR must be > 0.3x ATR)
- ATR_RANGE_MAX: 2.5 (OR must be < 2.5x ATR)
- SL_ATR_MULT: 1.5
- TP_ATR_MULT: 2.0
- TRAIL_ACTIVATION_R: 1.5
- TRAIL_ATR_MULT: 1.0
- VOLUME_MULT: 1.2
- MIN_BARS_BETWEEN: 6 (30 min cooldown)
- FLATTEN_HOUR: 14

## Source
- Adapted from FQL orb_009 (equity ORB) with crude-specific session timing
- Crude oil ORB is documented in futures trading literature (Crabel, Toby)
- cl_orb strategy exists in FQL but is long-only; this tests both directions

## Diversification Role
- **Asset class:** Energy (correlation to equities ~0.3-0.7, lower than M2K/MNQ)
- **Family:** Breakout (same family as ORB-MGC but different asset class)
- **Session:** NYMEX hours (09:00-14:00 ET, partially overlaps but different microstructure)
- **Expected contribution:** Adds energy exposure to equity-heavy portfolio. Crude has different vol drivers (OPEC, inventories, geopolitics) providing genuine diversification even within breakout family.
