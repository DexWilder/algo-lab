# Strategy Spec: Treasury-Cash-Close-Reversion-Window

## Hypothesis

The U.S. Treasury cash market closes at 15:00 ET. In the final 15 minutes
before close (14:45-15:00), institutional fixing flows often push Treasury
futures (ZN) directionally. Once the cash close passes and fixing pressure
lifts, the impulse fades. A strategy that detects an outsized pre-close
move and fades it in the post-close window (15:01-15:30) captures this
structural reversion.

The edge is microstructural: the pre-close move is driven by non-information
flow (fixing, rebalancing, hedging), not by new information. Once the flow
stops, price reverts.

**Factor: STRUCTURAL.** The signal is driven by session microstructure
(cash close timing), not by price direction or volatility.

## Data Caveat

ZN 5m bar coverage at 15:25 ET is 80.3% of weekdays. The missing 20% are
low-volume days where Databento does not produce a bar. Results apply only
to days where the close window is tradable. This creates a
liquidity-conditioned sample — the strategy is tested on days with
sufficient afternoon volume, not all days.

## Signal Logic

### Pre-Close Impulse Measurement

- `pre_close_move` = close at 14:55 - open at 14:45 (3 bars, 15 minutes)
- `move_direction` = sign(pre_close_move)
- `move_magnitude` = abs(pre_close_move)
- `median_move` = rolling 20-day median of daily move magnitudes
- `impulse_ratio` = move_magnitude / median_move

### Entry Condition (Variant A)

ALL of:
1. 14:45 and 15:00 bars exist (data quality gate)
2. impulse_ratio > IMPULSE_THRESHOLD (default 1.5)
3. move_direction != 0

### Entry

- Time: 15:00 ET (open of the 15:00 bar — first bar after cash close)
- Direction: FADE the pre-close move (short if pre-close was up, long if down)
- Price: open of the 15:00 bar

### Exit

- **Retracement exit:** 60% of the pre-close move retraces → exit
- **Time exit:** 15:30 ET (open of 15:30 bar, or close of 15:25 bar)
- **Stop:** 1.5x ATR(20) from entry
- Whichever comes first.

## Parameters

```
IMPULSE_THRESHOLD = 1.5     # Pre-close move must exceed 1.5x 20d median
LOOKBACK = 20               # Days for median move baseline
ATR_LEN = 20                # For stop calculation
SL_ATR_MULT = 1.5           # Stop distance
RETRACE_PCT = 0.60          # Exit when 60% of impulse retraces
ENTRY_HOUR = 15             # 15:00 ET
ENTRY_MINUTE = 0
EXIT_HOUR = 15
EXIT_MINUTE = 25            # Use 15:25 bar close as final exit
PRE_CLOSE_START_HOUR = 14
PRE_CLOSE_START_MINUTE = 45
PRE_CLOSE_END_HOUR = 14
PRE_CLOSE_END_MINUTE = 55   # Close of 14:55 bar
```

## Falsification Variants

| Variant | Entry Window | Fade Window | Purpose |
|---------|-------------|-------------|---------|
| A | 14:45-15:00 impulse → fade at 15:00 | 15:00-15:25 | True close-window reversion |
| B | 13:45-14:00 impulse → fade at 14:00 | 14:00-14:25 | Generic afternoon control |
| C | No impulse filter → fade at 15:00 | 15:00-15:25 | Unconditional close fade |

Variant B uses identical logic shifted 1 hour earlier — before the cash
close. If B ≈ A, the cash close is not special.

Variant C removes the impulse threshold. If C ≈ A, the filter adds no
value.

## Asset

- **Primary:** ZN (10-Year Note) — 80% bar coverage, adequate volume
- **Deferred:** ZB (30-Year Bond) — 65% coverage, too sparse for first-pass

## Source

- Claw synthesis from public intraday market-microstructure literature
- Harvest note: `2026-03-20_04_treasury_cash_close_reversion_window.md`
