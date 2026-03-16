# Strategy Spec: EIA-Inventory-Surprise

## Hypothesis
The weekly EIA petroleum inventory report (Wednesday 10:30 ET) is the highest-volatility recurring event for crude oil futures. When the actual inventory number surprises vs consensus, crude reacts with a directional move that persists for 30-90 minutes. Trading the post-announcement momentum captures a structural, calendar-driven edge with ~48 events per year.

## Entry
- Condition 1: Wednesday only, entry window 10:30-11:00 ET (first 30 minutes after release)
- Condition 2: Directional momentum — close of the 10:30 bar is > 1.0x ATR(20) from the pre-announcement close (the 10:25 bar close)
- Condition 3: Long if 10:30 bar closes sharply higher; Short if sharply lower
- Direction: both (follow the surprise direction)

## Exit
- Target: 1.5x ATR(20) from entry (crude post-EIA moves tend to be fast but capped)
- Stop: 1.0x ATR(20) against entry (tight — if the move reverses quickly, the surprise was absorbed)
- Time stop: 18 bars (90 minutes) — post-EIA momentum typically exhausts within 1-2 hours
- Flatten: 13:00 ET at latest

## Session
- Only trades on Wednesdays
- Pre-announcement reference: 10:25 ET bar close
- Entry window: 10:30-11:00 ET
- Max hold: 90 minutes or 13:00 ET
- No overnight holds

## Assets
- Primary: MCL (Micro Crude Oil)
- Test also: none initially (this is crude-specific by design)

## Parameters (initial)
- EVENT_DAY: Wednesday (day_of_week == 2)
- ANNOUNCE_HOUR: 10, ANNOUNCE_MIN: 30
- PRE_ANNOUNCE_HOUR: 10, PRE_ANNOUNCE_MIN: 25
- ENTRY_WINDOW_BARS: 6 (30 minutes after announcement)
- SURPRISE_ATR_THRESH: 1.0 (move must exceed 1.0x ATR to qualify as surprise)
- ATR_LEN: 20
- SL_ATR_MULT: 1.0
- TP_ATR_MULT: 1.5
- MAX_HOLD_BARS: 18
- FLATTEN_HOUR: 13

## Source
- Registry notes: "Wednesday 10:30 ET is highest-volatility recurring event for crude. ~20-25 trades/yr"
- EIA Weekly Petroleum Status Report is a US government release with fixed schedule
- Post-announcement momentum in commodities is documented in event-study literature

## Diversification Role
- **Asset class:** Energy (MCL — adds crude exposure)
- **Family:** Event-driven (completely new family for FQL — no existing event-driven strategies active)
- **Session:** Single 90-minute window per week (zero overlap with any other strategy's trading time)
- **Expected contribution:** Genuinely uncorrelated to all existing strategies. Fires on a fixed calendar, driven by inventory fundamentals, not technical patterns. ~48 potential events per year, expect ~20-25 to qualify as "surprise" after ATR filter.
