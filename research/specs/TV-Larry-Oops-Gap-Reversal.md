# Strategy Spec: TV-Larry-Oops-Gap-Reversal

## Hypothesis
When a market gaps beyond the prior day's range at the open, the gap frequently reverses back into the prior range within the same session. This is the Larry Williams "Oops" pattern — a structural mean-reversion setup triggered by opening gaps that overshoot. The mechanism is that overnight gaps often reflect thin-liquidity price discovery that gets corrected once the full session's participants arrive.

This differs from generic gap-fill strategies (GapFill-M2K was rejected at PF 0.68) because the Oops pattern requires the gap to exceed the prior day's HIGH or LOW (not just the close), and the entry is a stop order that only fills if price reclaims that level — confirming the reversal has started.

## Gap Definition
- **Prior day range:** yesterday's high and yesterday's low
- **Gap down Oops:** today's open is BELOW yesterday's low (gap beyond the range floor)
- **Gap up Oops:** today's open is ABOVE yesterday's high (gap beyond the range ceiling)
- **Key distinction:** this is NOT a close-to-open gap. It's an open vs prior-day-range gap. The gap must exceed the range extreme, not just the close.

## Entry
- **Gap down (long):** today opens below yesterday's low. Enter long when price crosses BACK ABOVE yesterday's low (buy stop at yesterday's low + filter). The reclaim confirms the gap is reversing.
- **Gap up (short):** today opens above yesterday's high. Enter short when price crosses BACK BELOW yesterday's high (sell stop at yesterday's high - filter). The reclaim confirms the gap is reversing.
- **Filter:** small buffer above/below the level to avoid noise (1-2 ticks or 0.1x ATR)
- **Entry window:** first 2 hours of RTH only (09:30-11:30 ET for equities). If the reclaim doesn't happen by then, the gap is holding and the Oops is invalidated.
- Direction: both

## Exit
- **Trail:** trail stop at today's intraday low (longs) or high (shorts), updated each bar
- **Flatten:** end of session (no overnight hold)
- **No fixed target** — let the reversal run with trailing protection
- **Stop:** if price makes a new low below the gap (longs) or new high above the gap (shorts), the reversal thesis is dead — exit immediately

## Target Assets
- Primary: MES (most liquid, cleanest gap behavior)
- Secondary: MNQ (Nasdaq, may show stronger/weaker gaps)
- Tertiary: MGC (gold, different session — test portability)

## Parameters (initial)
- FILTER_ATR_MULT: 0.1 (entry filter above/below prior range level)
- ATR_LEN: 20
- ENTRY_WINDOW_HOURS: 2 (09:30-11:30 ET, or asset-specific RTH start + 2h)
- TRAIL_TYPE: "intraday_extreme" (trail at session low for longs, session high for shorts)
- FLATTEN_TIME: session close (15:55 ET for equities, 15:00 ET for CBOT)
- MIN_GAP_SIZE: 0 (any gap beyond range counts — could add ATR filter later)

## Source
- Larry Williams: "Long-Term Secrets to Short-Term Trading"
- TradingView: "Larry Williams Oops Strategy" by xtradernet (public script)
- One of the most well-known session-open structural patterns in futures trading

## Key Failure Mode to Watch
- **Gap-and-go days:** Some gaps don't reverse — they extend (trend days, major news). The 2-hour entry window mitigates this (no entry if the gap holds), but the strategy will still have losing trades on days where the initial reclaim is a fake-out before continuation.
- **GapFill-M2K precedent:** A simpler gap-fill approach was rejected at PF 0.68 on M2K. The Oops pattern is structurally different (gap beyond range, not just close; reclaim confirmation entry, not immediate fade), but the failure of generic gap-fill is a cautionary note.

## Diversification Role
- **Factor:** STRUCTURAL — the edge is in the session-open gap reversal structure, not price momentum
- **Session:** Morning open only (first 2 hours) — different from overnight, close, or all-day strategies
- **Mechanism:** Mean-reversion triggered by structural overshoot, not indicator-based
- **Correlation to existing portfolio:** Low. Existing morning strategies are breakout/momentum (ORB, VWAP pullback). This is a morning FADE strategy — profits when breakout strategies would lose (gap-and-reverse days vs gap-and-go days).
