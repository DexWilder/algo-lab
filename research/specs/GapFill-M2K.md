# Strategy Spec: GapFill-M2K

## Hypothesis
Equity index futures frequently gap at the open relative to the prior session close. Institutional rebalancing and overnight position unwinding create a structural tendency for gaps to fill (partially or fully) within the first 2-3 hours. Russell 2000 (M2K) amplifies this effect due to thinner liquidity and wider overnight gaps.

## Entry
- Condition 1: Calculate overnight gap = RTH open (09:30 bar) minus prior session close (previous day's last bar before 16:00)
- Condition 2: Gap must exceed 0.5x ATR(20) in magnitude (filter out noise gaps)
- Condition 3: Gap must be less than 3.0x ATR(20) (avoid gap-and-go trend days)
- Condition 4: Short if gap is up (fade the gap); Long if gap is down (fade the gap)
- Direction: both (fade direction of gap)

## Exit
- Target: prior session close (full gap fill — the structural target)
- Partial target: 50% of gap distance (half-fill — take partial if available)
- Stop: 1.5x ATR(20) beyond the opening price in the gap direction (gap extending = thesis is wrong)
- Time stop: 36 bars (3 hours) — if gap hasn't filled by 12:30 ET, it's likely a trend day
- Flatten: 13:00 ET

## Session
- Gap calculation: compare 09:30 open to prior day close
- Entry: 09:35 ET (one bar after open, let first bar settle)
- Max hold: 3 hours or 13:00 ET
- One trade per day maximum

## Assets
- Primary: M2K (Micro Russell 2000)
- Test also: MES (broader S&P, compare gap-fill behavior)

## Parameters (initial)
- GAP_ATR_MIN: 0.5 (minimum gap size as ATR multiple)
- GAP_ATR_MAX: 3.0 (maximum gap size — beyond this, gap-and-go likely)
- ATR_LEN: 20
- SL_ATR_MULT: 1.5
- MAX_HOLD_BARS: 36
- ENTRY_DELAY_BARS: 1 (enter one bar after open)
- FLATTEN_HOUR: 13
- SESSION_OPEN_HOUR: 9, SESSION_OPEN_MIN: 30
- PRIOR_CLOSE_HOUR: 15, PRIOR_CLOSE_MIN: 55

## Source
- Registry notes: "1 trade/day max. Structural edge from institutional rebalancing. Tier 2 candidate."
- Gap-fill tendency on equity indices is widely documented (Bulkowski, Quantified Strategies)
- Russell 2000 has larger average gaps than S&P due to thinner overnight liquidity

## Diversification Role
- **Asset class:** Equity index (M2K — Russell 2000, correlation 0.75-0.90 to MES/MNQ)
- **Family:** Mean reversion (gap fade is a specific type of MR different from RSI/VWAP fade)
- **Session:** First 3 hours only (09:30-12:30 ET), one trade per day
- **Expected contribution:** Counter-trend entry at open vs momentum/breakout strategies that trade continuations. Profits when market opens extended and reverts — the opposite condition from when ORB/breakout strategies profit. ~150-200 potential gap days per year, expect 40-80 to qualify after ATR filter.
