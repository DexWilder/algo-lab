"""BB-EQUILIBRIUM — Bollinger Band Mean Reversion (Trend-Aware).

Gold-specific mean reversion exploiting intraday BB snapback behavior.
Fills the structural gap: PB/ORB/VWAP are all momentum/trend systems.
This trades the opposite regime: price overextension that reverts to equilibrium.

Structurally distinct from all existing parents:
- PB  → pullback scalper (momentum)
- ORB → volatility breakout (momentum)
- VWAP → trend continuation (momentum)
- BB  → mean reversion (counter-trend)

Logic:
- Indicator: BB(20, 2) — standard Bollinger Bands
- Entry: price touches/crosses outer band, then bounces back inside
  - Long: prior bar low <= lower band, current close > lower band (bounce off floor)
  - Short: prior bar high >= upper band, current close < upper band (reject from ceiling)
- Filters:
  - BB bandwidth below rolling median (ranging/compressed market)
  - RSI confirmation (oversold for long, overbought for short)
  - Daily EMA(20) trend alignment (longs in uptrend, shorts in downtrend)
  - No trades during first 15min (let indicators stabilize)
- Exit: price reaches BB midline (SMA20) — the equilibrium target
- Stop: ATR-based (tight — MR targets are close, stops must be proportional)
- ATR trailing stop as backup
- Pre-close session flatten
- Max 1 trade per direction per day

Phase 11.6 evolution: EMA20 trend filter solved walk-forward instability
(2024 PF 0.88→1.00, 2025 PF 2.02→1.21). Mechanism: gold MR works best
within a macro trend — trends create the overextensions that revert.

Expected behavior:
- Win rate 55-65% (mean reversion has higher win rate, smaller avg win)
- Median hold time 5-30 bars (quick reversion trades)
- Profits when gold has macro trend + intraday overextension
- Should have LOW correlation with existing trend/momentum portfolio

PLATFORM-AGNOSTIC: Pure signal logic only.
No prop rules, no phase sizing, no guardrails.
"""

import pandas as pd
import numpy as np


# ── Parameters ───────────────────────────────────────────────────────────

BB_LENGTH = 20            # Bollinger Band SMA period
BB_MULT = 2.0             # BB standard deviation multiplier
RSI_PERIOD = 14           # RSI period for confirmation
RSI_OVERSOLD = 35         # RSI threshold for long entry
RSI_OVERBOUGHT = 65       # RSI threshold for short entry
ATR_PERIOD = 14           # ATR period for stop calculation
ATR_STOP_MULT = 1.5       # Initial stop = entry ± ATR × mult (tight for MR)
ATR_TRAIL_MULT = 2.0      # Trailing stop distance = ATR × mult
BW_LOOKBACK = 100         # Bandwidth percentile ranking lookback
BW_MAX_PCT = 50           # Max bandwidth percentile (only trade in low-vol squeeze)
MIN_HOLD_BARS = 3         # Min bars before midline exit activates
TREND_EMA_PERIOD = 20     # Daily EMA for macro trend filter

SESSION_START = "09:30"
SESSION_END = "15:45"
ENTRY_START = "09:45"     # 15min warmup for BB/RSI
ENTRY_CUTOFF = "14:45"    # MR trades are quick, later cutoff OK
FLATTEN_TIME = "15:30"    # Pre-close flatten

TICK_SIZE = 0.25           # Patched per asset by runner


# ── Helpers ──────────────────────────────────────────────────────────────

def _parse_time(dt_series: pd.Series) -> pd.Series:
    return pd.to_datetime(dt_series).dt.strftime("%H:%M")


def _rsi(series: pd.Series, period: int) -> np.ndarray:
    """Compute RSI using exponential moving average."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.values


# ── Signal Generator ────────────────────────────────────────────────────

def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Generate Bollinger Band mean-reversion signals.

    Returns DataFrame with: signal, exit_signal, stop_price, target_price.
    """
    df = df.copy()
    n = len(df)

    dt = pd.to_datetime(df["datetime"])
    df["_date"] = dt.dt.date
    time_str = _parse_time(df["datetime"])

    # ── Session boundaries ────────────────────────────────────────────
    in_session = (time_str >= SESSION_START) & (time_str < SESSION_END)
    entry_ok = in_session & (time_str >= ENTRY_START) & (time_str < ENTRY_CUTOFF)

    # ── Daily EMA trend filter ─────────────────────────────────────────
    # Compute daily close, then EMA slope → map trend direction to each bar
    daily_close = df.groupby("_date")["close"].last()
    daily_ema = daily_close.ewm(span=TREND_EMA_PERIOD, adjust=False).mean()
    daily_slope = daily_ema.diff()
    date_trend_map = {}
    for d in daily_ema.index:
        slope = daily_slope.get(d, 0)
        if pd.isna(slope):
            date_trend_map[d] = 0
        elif slope > 0:
            date_trend_map[d] = 1   # uptrend → longs allowed
        else:
            date_trend_map[d] = -1  # downtrend → shorts allowed
    bar_trend = dt.dt.date.map(date_trend_map).fillna(0).astype(int).values

    # ── Bollinger Bands ──────────────────────────────────────────────
    sma = df["close"].rolling(window=BB_LENGTH, min_periods=BB_LENGTH).mean()
    std = df["close"].rolling(window=BB_LENGTH, min_periods=BB_LENGTH).std(ddof=0)
    upper_bb = sma + BB_MULT * std
    lower_bb = sma - BB_MULT * std

    # Bandwidth: (upper - lower) / midline — measures volatility squeeze
    bandwidth = ((upper_bb - lower_bb) / sma).values

    # Bandwidth percentile rank (rolling) — low = compressed = ranging
    bw_series = pd.Series(bandwidth)
    bw_pctrank = bw_series.rolling(
        window=BW_LOOKBACK, min_periods=20
    ).apply(lambda x: (x.iloc[-1] <= x).sum() / len(x) * 100, raw=False).values

    # ── RSI ──────────────────────────────────────────────────────────
    rsi = _rsi(df["close"], RSI_PERIOD)

    # ── ATR for stops ────────────────────────────────────────────────
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.ewm(span=ATR_PERIOD, adjust=False).mean().values

    # ── Pre-compute arrays ───────────────────────────────────────────
    close_arr = df["close"].values
    high_arr = df["high"].values
    low_arr = df["low"].values
    open_arr = df["open"].values
    time_arr = time_str.values
    dates_arr = df["_date"].values
    in_session_arr = in_session.values
    entry_ok_arr = entry_ok.values
    sma_arr = sma.values
    upper_arr = upper_bb.values
    lower_arr = lower_bb.values

    signals_arr = np.zeros(n, dtype=int)
    exit_sigs = np.zeros(n, dtype=int)
    stop_arr = np.full(n, np.nan)
    target_arr = np.full(n, np.nan)

    # ── Stateful loop ────────────────────────────────────────────────
    position = 0
    entry_price = 0.0
    trailing_stop = 0.0
    target_price = 0.0
    current_date = None
    long_traded_today = False
    short_traded_today = False
    highest_since_entry = 0.0
    lowest_since_entry = 0.0
    bars_in_trade = 0

    for i in range(1, n):  # Start from 1 to access prior bar
        bar_date = dates_arr[i]
        bar_time = time_arr[i]
        bar_atr = atr[i]
        bar_sma = sma_arr[i]
        bar_upper = upper_arr[i]
        bar_lower = lower_arr[i]
        bar_rsi = rsi[i]
        bar_bw_pct = bw_pctrank[i]

        # ── Day reset ────────────────────────────────────────────────
        if bar_date != current_date:
            if position != 0:
                exit_sigs[i] = 1 if position == 1 else -1
                position = 0
            current_date = bar_date
            long_traded_today = False
            short_traded_today = False

        if not in_session_arr[i]:
            continue

        if (np.isnan(bar_atr) or np.isnan(bar_sma) or np.isnan(bar_upper)
                or np.isnan(bar_lower) or np.isnan(bar_rsi)):
            continue

        # ── Pre-close flatten ────────────────────────────────────────
        if position != 0 and bar_time >= FLATTEN_TIME:
            exit_sigs[i] = 1 if position == 1 else -1
            position = 0
            continue

        # ── Check exits for open position ────────────────────────────
        if position == 1:
            bars_in_trade += 1

            # Update trailing stop
            if high_arr[i] > highest_since_entry:
                highest_since_entry = high_arr[i]
                new_trail = highest_since_entry - bar_atr * ATR_TRAIL_MULT
                if new_trail > trailing_stop:
                    trailing_stop = new_trail

            # Exit 1: Midline target reached (after min hold)
            if bars_in_trade >= MIN_HOLD_BARS and high_arr[i] >= target_price:
                exit_sigs[i] = 1
                position = 0

            # Exit 2: Stop hit
            elif low_arr[i] <= trailing_stop:
                exit_sigs[i] = 1
                position = 0

        elif position == -1:
            bars_in_trade += 1

            # Update trailing stop
            if low_arr[i] < lowest_since_entry:
                lowest_since_entry = low_arr[i]
                new_trail = lowest_since_entry + bar_atr * ATR_TRAIL_MULT
                if new_trail < trailing_stop:
                    trailing_stop = new_trail

            # Exit 1: Midline target reached
            if bars_in_trade >= MIN_HOLD_BARS and low_arr[i] <= target_price:
                exit_sigs[i] = -1
                position = 0

            # Exit 2: Stop hit
            elif high_arr[i] >= trailing_stop:
                exit_sigs[i] = -1
                position = 0

        # ── Entry: Band bounce in ranging market ─────────────────────
        if position == 0 and entry_ok_arr[i]:

            # Bandwidth filter: only trade in compressed/ranging markets
            if np.isnan(bar_bw_pct) or bar_bw_pct > BW_MAX_PCT:
                continue

            # ── Long entry (bounce off lower band) ───────────────────
            # Prior bar touched/crossed below lower band, current bar closes back above
            # Trend filter: only long in uptrend (daily EMA slope > 0)
            if (not long_traded_today
                and bar_trend[i] == 1
                and low_arr[i - 1] <= lower_arr[i - 1]
                and close_arr[i] > lower_arr[i]
                and bar_rsi < RSI_OVERSOLD):

                initial_stop = close_arr[i] - bar_atr * ATR_STOP_MULT
                target = bar_sma  # Mean reversion target = BB midline
                signals_arr[i] = 1
                stop_arr[i] = initial_stop
                target_arr[i] = target
                position = 1
                entry_price = close_arr[i]
                trailing_stop = initial_stop
                target_price = target
                highest_since_entry = high_arr[i]
                long_traded_today = True
                bars_in_trade = 0

            # ── Short entry (reject from upper band) ─────────────────
            # Trend filter: only short in downtrend (daily EMA slope < 0)
            elif (not short_traded_today
                  and bar_trend[i] == -1
                  and high_arr[i - 1] >= upper_arr[i - 1]
                  and close_arr[i] < upper_arr[i]
                  and bar_rsi > RSI_OVERBOUGHT):

                initial_stop = close_arr[i] + bar_atr * ATR_STOP_MULT
                target = bar_sma  # Mean reversion target = BB midline
                signals_arr[i] = -1
                stop_arr[i] = initial_stop
                target_arr[i] = target
                position = -1
                entry_price = close_arr[i]
                trailing_stop = initial_stop
                target_price = target
                lowest_since_entry = low_arr[i]
                short_traded_today = True
                bars_in_trade = 0

    df["signal"] = signals_arr
    df["exit_signal"] = exit_sigs
    df["stop_price"] = stop_arr
    df["target_price"] = target_arr
    df.drop(columns=["_date"], inplace=True, errors="ignore")

    return df
