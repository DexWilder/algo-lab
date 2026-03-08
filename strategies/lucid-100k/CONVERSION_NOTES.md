# Lucid v6.3 — Pine to Python Conversion Notes

## What Was Converted (Pure Signal Logic)

### Algo 1: Trend Pullback
- EMA 9/21/200 alignment for trend direction
- Pullback to slow EMA (21) with close above fast EMA (9)
- Strong close filter (close in top/bottom 20% of bar range)
- Prior bar break OR strong close for entry confirmation
- Range expansion filter (bar range >= 60% of 10-bar avg)

### Algo 2: VWAP Mean Reversion
- Distance from VWAP >= 1.4 ATR for overextension
- RSI <= 35 (long) or >= 65 (short) for momentum exhaustion
- Neutralish EMAs (fast/slow separation < 0.6 ATR)
- Flat VWAP slope (< 0.3 ATR over 5 bars)
- Rejection candle (wick ratio >= 40%)
- Blackout period (30 min after session open)

### Regime Gate
- Trend regime: ADX >= 14 + EMA slope + VWAP slope
- Range regime: ADX < 14 + neutralish EMAs
- Auto mode: trend algo active in trend regime, reversion in range

### Filters
- Session: 08:30-15:15 ET (RTH)
- Warmup: 15 min after session open
- Power windows: 08:45-11:00 and 13:30-15:10
- ADX >= 14
- Volume > 20-bar SMA
- Session-end flatten

### Exits
- ATR-based stop (1.5x ATR, min 20 ticks floor)
- ATR-based target (2.1x ATR)
- Stop/target checked bar-by-bar using high/low

## What Was NOT Converted (Lives in Controllers)

These are prop/account rules — they belong in `controllers/prop_controller.py`:

- Phase system (P1 Lock / P2 Payout)
- Phase-aware sizing (qty P1=2, P2=5, cooldown=1)
- Phase-aware exits (different SL/TP/BE/Trail ATR multiples per phase)
- Green-day lock (P1: stop trading at +$600/day)
- Profit lock (P2: stop at +$1200/day or cooldown)
- Daily loss limit (P1: $600, P2: $1200)
- Intraday drawdown limit (P1: $900, P2: $1800)
- Weekly loss limit ($1500)
- Max trades per day (P1: 2, P2: 4)
- Consecutive loss streak halt
- Phase 2 gate (recent PF check)
- Halted-yesterday cooldown
- Lucid EOD trailing drawdown simulation
- Learning metrics / halt counters

## Approximations & Known Gaps

### MTF Filter
- **Pine**: `request.security("15", ta.ema(close, 200))` for 15m and 60m EMA200
- **Python**: Approximated with 5m EMA600 (15m × 200 ÷ 5m = 600 bars)
- **Impact**: Slightly different responsiveness. The approximation is smoother.
- **Fix**: Resample data to 15m, compute EMA200, merge back. Will implement when engine supports multi-timeframe data.

### VWAP Calculation
- **Pine**: `ta.vwap(hlc3)` — built-in, resets daily
- **Python**: Cumulative (price × volume) / cumulative volume, grouped by date
- **Impact**: Should match closely. Minor differences possible at exact session boundaries.

### Exit Fill Prices
- **Pine**: `strategy.exit()` with stop/limit fills at exact price levels intrabar
- **Python**: Exit signal emitted when bar's high/low breaches level, filled at next open
- **Impact**: Exits will be slightly worse (slippage past the stop/target level). This is conservative.
- **Fix**: Future engine upgrade to support price-level exits with intrabar fill simulation.

### 3-Stage Exit System
- **Pine**: Bracket → Break-Even at 1R → Trailing at 1.5R
- **Python**: Simple bracket only (stop + target). No BE or trail stages.
- **Impact**: Missing the upside capture from trailing stops on runners.
- **Fix**: Add exit stage management to the signal generator or engine. Priority upgrade.

### ADX Calculation
- **Pine**: `ta.dmi(adxLen, adxLen)` returns [DI+, DI-, ADX]
- **Python**: Custom implementation using smoothed DM/ATR
- **Impact**: Minor numerical differences due to smoothing method. Functionally equivalent.

### No Position-Awareness in Signal Generation
- **Pine**: Checks `strategy.position_size == 0` before entering
- **Python**: The exit loop tracks position state for stop/target management, but the signal generation itself is stateless (marks all qualifying bars). The backtest engine handles "only enter when flat" logic.

## Validation Checklist

- [ ] Run through pipeline (`run_all.py --strategy lucid-100k`)
- [ ] Compare signal count vs Pine backtester
- [ ] Compare win rate and PF direction (don't expect exact match due to approximations)
- [ ] Verify session filter correctly blocks overnight bars
- [ ] Verify warmup period blocks first 3 bars of session
- [ ] Verify VWAP resets daily
- [ ] Spot-check 5-10 individual trade entries against Pine chart
- [ ] Document any material divergence from Pine results
