"""Golden Gun — Spot Gold ALGO Number Reclaim Strategy on MGC.

Standalone research project. NOT part of the FQL registry pipeline.
Tests whether ALGO number reclaims on micro gold futures produce
a tradeable edge.

Setup:
  - ALGO numbers are price levels ending in 00, 10, 25, 50, 75, 90
  - A signal fires when a candle interacts with an ALGO number
    (wick pierces or touches the level) and closes back on the
    "correct" side (reclaim)
  - Long: candle low touches/pierces ALGO, closes ABOVE it
  - Short: candle high touches/pierces ALGO, closes BELOW it

Entry/exit:
  - Entry: head of signal candle (high for long, low for short)
  - Stop: opposite extreme (low for long, high for short)
  - TP1: 2R (take 50% off)
  - Runner: trail with EMA on higher timeframe

Session: 08:00-11:30 ET only

Risk: fixed fractional (% of equity per trade)
"""

import pandas as pd
import numpy as np
from pathlib import Path

# ── Parameters ──

# ALGO number endings (last 2 digits of price)
ALGO_ENDINGS = [0, 10, 25, 50, 75, 90]

# Session filter (ET)
SESSION_START_HOUR = 8
SESSION_START_MINUTE = 0
SESSION_END_HOUR = 11
SESSION_END_MINUTE = 30

# Exit parameters
TP1_R = 2.0           # Take 50% at 2R
TP1_PCT = 0.50        # Portion to close at TP1
TRAIL_EMA_LEN = 8     # EMA period for trailing the runner

# Minimum candle size (avoid dust trades)
MIN_CANDLE_TICKS = 2  # Minimum candle range in ticks (MGC tick = $0.10)
TICK_SIZE = 0.10      # MGC tick size

# Risk sizing
RISK_PCT = 0.01       # 1% of equity per trade
STARTING_EQUITY = 10_000.0
POINT_VALUE = 1.0     # MGC = $1 per $1 move (10 oz * $0.10/oz)

# Actually MGC is 10 troy oz, so $1/oz move = $10/contract
# But price is quoted per oz, so point_value should reflect contract multiplier
CONTRACT_MULTIPLIER = 10.0  # 10 troy oz per MGC contract


# ── ALGO Number Logic ──

def get_algo_levels(price, search_range=15):
    """Get all ALGO levels within search_range of price."""
    levels = []
    base = int(price) - int(price) % 100
    for offset in range(-200, 300, 100):
        for ending in ALGO_ENDINGS:
            level = base + offset + ending
            if abs(level - price) <= search_range:
                levels.append(level)
    return sorted(set(levels))


def find_interaction(bar_low, bar_high, bar_close, levels):
    """Check if a bar interacts with any ALGO level and classify the reclaim.

    Returns (direction, level, candle_risk) or (None, None, None).

    Long reclaim: bar low touches/pierces level, bar closes ABOVE level
    Short reclaim: bar high touches/pierces level, bar closes BELOW level
    """
    for level in levels:
        # Long: low pierced the level, close is above
        if bar_low <= level and bar_close > level:
            return 1, level, None  # Direction, level (risk computed later)

        # Short: high pierced the level, close is below
        if bar_high >= level and bar_close < level:
            return -1, level, None

    return None, None, None


# ── Backtest Engine ──

def run_backtest(df, mode="both", risk_pct=RISK_PCT, starting_equity=STARTING_EQUITY):
    """Run the Golden Gun backtest on MGC 5m data.

    Returns dict with:
        trades_df: DataFrame of all trades
        equity_curve: Series of equity over time
        r_stats: R-multiple statistics
        equity_stats: Compounding statistics
    """
    df = df.copy()
    df["datetime"] = pd.to_datetime(df["datetime"])
    df["hour"] = df["datetime"].dt.hour
    df["minute"] = df["datetime"].dt.minute

    # Session filter
    df["in_session"] = (
        ((df["hour"] > SESSION_START_HOUR) |
         ((df["hour"] == SESSION_START_HOUR) & (df["minute"] >= SESSION_START_MINUTE))) &
        ((df["hour"] < SESSION_END_HOUR) |
         ((df["hour"] == SESSION_END_HOUR) & (df["minute"] <= SESSION_END_MINUTE - 5)))
    )

    # Compute EMA for trailing (on all bars, not just session)
    df["ema"] = df["close"].ewm(span=TRAIL_EMA_LEN, adjust=False).mean()

    trades = []
    equity = starting_equity
    position = None  # {direction, entry, stop, tp1, level, entry_time, risk_dollars, size, tp1_hit}

    for i in range(1, len(df)):
        bar = df.iloc[i]
        prev = df.iloc[i - 1]

        # ── Manage open position ──
        if position is not None:
            direction = position["direction"]
            stop = position["stop"]
            entry = position["entry"]
            tp1 = position["tp1"]
            size = position["size"]

            # Check stop hit
            stopped = False
            if direction == 1 and bar["low"] <= stop:
                stopped = True
                exit_price = stop
            elif direction == -1 and bar["high"] >= stop:
                stopped = True
                exit_price = stop

            if stopped:
                pnl = (exit_price - entry) * direction * CONTRACT_MULTIPLIER * size
                r_multiple = (exit_price - entry) * direction / abs(entry - position["original_stop"])
                trades.append({
                    "entry_time": position["entry_time"],
                    "exit_time": bar["datetime"],
                    "direction": "long" if direction == 1 else "short",
                    "entry": entry,
                    "exit": exit_price,
                    "stop": position["original_stop"],
                    "level": position["level"],
                    "pnl": round(pnl, 2),
                    "r_multiple": round(r_multiple, 2),
                    "tp1_hit": position["tp1_hit"],
                    "exit_reason": "stop",
                    "size": size,
                })
                equity += pnl
                position = None
                continue

            # Check TP1 hit (if not already hit)
            if not position["tp1_hit"]:
                tp1_hit = False
                if direction == 1 and bar["high"] >= tp1:
                    tp1_hit = True
                elif direction == -1 and bar["low"] <= tp1:
                    tp1_hit = True

                if tp1_hit:
                    # Close TP1_PCT of position at TP1
                    tp1_size = size * TP1_PCT
                    tp1_pnl = (tp1 - entry) * direction * CONTRACT_MULTIPLIER * tp1_size
                    position["tp1_hit"] = True
                    position["size"] = size - tp1_size

                    # Move stop to break-even for runner
                    position["stop"] = entry

                    trades.append({
                        "entry_time": position["entry_time"],
                        "exit_time": bar["datetime"],
                        "direction": "long" if direction == 1 else "short",
                        "entry": entry,
                        "exit": tp1,
                        "stop": position["original_stop"],
                        "level": position["level"],
                        "pnl": round(tp1_pnl, 2),
                        "r_multiple": round(TP1_R, 2),
                        "tp1_hit": True,
                        "exit_reason": "tp1",
                        "size": tp1_size,
                    })
                    equity += tp1_pnl

            # Trail with EMA (only after TP1 hit)
            if position is not None and position["tp1_hit"]:
                if direction == 1 and bar["close"] < bar["ema"]:
                    # Exit runner
                    exit_price = bar["close"]
                    pnl = (exit_price - entry) * direction * CONTRACT_MULTIPLIER * position["size"]
                    r_multiple = (exit_price - entry) * direction / abs(entry - position["original_stop"])
                    trades.append({
                        "entry_time": position["entry_time"],
                        "exit_time": bar["datetime"],
                        "direction": "long",
                        "entry": entry,
                        "exit": exit_price,
                        "stop": position["original_stop"],
                        "level": position["level"],
                        "pnl": round(pnl, 2),
                        "r_multiple": round(r_multiple, 2),
                        "tp1_hit": True,
                        "exit_reason": "ema_trail",
                        "size": position["size"],
                    })
                    equity += pnl
                    position = None

                elif direction == -1 and bar["close"] > bar["ema"]:
                    exit_price = bar["close"]
                    pnl = (exit_price - entry) * direction * CONTRACT_MULTIPLIER * position["size"]
                    r_multiple = (exit_price - entry) * direction / abs(entry - position["original_stop"])
                    trades.append({
                        "entry_time": position["entry_time"],
                        "exit_time": bar["datetime"],
                        "direction": "short",
                        "entry": entry,
                        "exit": exit_price,
                        "stop": position["original_stop"],
                        "level": position["level"],
                        "pnl": round(pnl, 2),
                        "r_multiple": round(r_multiple, 2),
                        "tp1_hit": True,
                        "exit_reason": "ema_trail",
                        "size": position["size"],
                    })
                    equity += pnl
                    position = None

            # End of session — close any open position
            if position is not None and not bar["in_session"]:
                exit_price = bar["close"]
                pnl = (exit_price - entry) * direction * CONTRACT_MULTIPLIER * position["size"]
                r_multiple = (exit_price - entry) * direction / abs(entry - position["original_stop"])
                trades.append({
                    "entry_time": position["entry_time"],
                    "exit_time": bar["datetime"],
                    "direction": "long" if direction == 1 else "short",
                    "entry": entry,
                    "exit": exit_price,
                    "stop": position["original_stop"],
                    "level": position["level"],
                    "pnl": round(pnl, 2),
                    "r_multiple": round(r_multiple, 2),
                    "tp1_hit": position["tp1_hit"],
                    "exit_reason": "session_end",
                    "size": position["size"],
                })
                equity += pnl
                position = None

            continue  # Don't enter new position while one is open

        # ── Look for new setup (only in session, no open position) ──
        if not bar["in_session"]:
            continue

        levels = get_algo_levels(bar["close"])
        direction, level, _ = find_interaction(bar["low"], bar["high"], bar["close"], levels)

        if direction is None:
            continue

        # Direction filter
        if mode == "long" and direction != 1:
            continue
        if mode == "short" and direction != -1:
            continue

        # Define risk from signal candle
        candle_range = bar["high"] - bar["low"]
        if candle_range < MIN_CANDLE_TICKS * TICK_SIZE:
            continue  # Candle too small

        if direction == 1:
            entry_price = bar["high"]
            stop_price = bar["low"]
        else:
            entry_price = bar["low"]
            stop_price = bar["high"]

        risk_per_unit = abs(entry_price - stop_price)
        if risk_per_unit <= 0:
            continue

        # Fixed fractional sizing
        risk_dollars = equity * risk_pct
        size = risk_dollars / (risk_per_unit * CONTRACT_MULTIPLIER)
        size = max(1, round(size))  # At least 1 contract

        # TP1 level
        if direction == 1:
            tp1_price = entry_price + risk_per_unit * TP1_R
        else:
            tp1_price = entry_price - risk_per_unit * TP1_R

        position = {
            "direction": direction,
            "entry": entry_price,
            "stop": stop_price,
            "original_stop": stop_price,
            "tp1": tp1_price,
            "level": level,
            "entry_time": bar["datetime"],
            "risk_dollars": risk_dollars,
            "size": size,
            "tp1_hit": False,
        }

    # Build results
    trades_df = pd.DataFrame(trades)
    if trades_df.empty:
        return {"trades_df": trades_df, "equity_curve": pd.Series(), "r_stats": {}, "equity_stats": {}}

    # R-multiple statistics
    r_vals = trades_df["r_multiple"]
    r_stats = {
        "total_trades": len(trades_df),
        "expectancy_r": round(r_vals.mean(), 3),
        "avg_winner_r": round(r_vals[r_vals > 0].mean(), 3) if (r_vals > 0).any() else 0,
        "avg_loser_r": round(r_vals[r_vals < 0].mean(), 3) if (r_vals < 0).any() else 0,
        "win_rate": round((r_vals > 0).sum() / len(r_vals) * 100, 1),
        "profit_factor": round(
            r_vals[r_vals > 0].sum() / abs(r_vals[r_vals < 0].sum()), 3
        ) if (r_vals < 0).any() and r_vals[r_vals < 0].sum() != 0 else 99.0,
        "tp1_hit_rate": round(trades_df["tp1_hit"].mean() * 100, 1),
        "exit_reasons": dict(trades_df["exit_reason"].value_counts()),
    }

    # Equity statistics
    equity_curve = trades_df["pnl"].cumsum() + starting_equity
    max_dd = (equity_curve.cummax() - equity_curve).max()
    equity_stats = {
        "starting_equity": starting_equity,
        "ending_equity": round(equity_curve.iloc[-1], 2),
        "total_return_pct": round((equity_curve.iloc[-1] / starting_equity - 1) * 100, 1),
        "max_drawdown": round(max_dd, 2),
        "risk_pct": risk_pct,
    }

    return {
        "trades_df": trades_df,
        "equity_curve": equity_curve,
        "r_stats": r_stats,
        "equity_stats": equity_stats,
    }


# ── Main ──

if __name__ == "__main__":
    DATA_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "processed" / "MGC_5m.csv"
    df = pd.read_csv(DATA_PATH)

    print("=" * 70)
    print("  GOLDEN GUN — MGC ALGO Number Reclaim Strategy")
    print("=" * 70)

    result = run_backtest(df)
    r = result["r_stats"]
    e = result["equity_stats"]
    trades = result["trades_df"]

    print(f"\n  R-Multiple Layer")
    print(f"  {'-'*40}")
    print(f"  Trades:          {r['total_trades']}")
    print(f"  Expectancy (R):  {r['expectancy_r']}")
    print(f"  Avg Winner (R):  {r['avg_winner_r']}")
    print(f"  Avg Loser (R):   {r['avg_loser_r']}")
    print(f"  Win Rate:        {r['win_rate']}%")
    print(f"  Profit Factor:   {r['profit_factor']}")
    print(f"  TP1 Hit Rate:    {r['tp1_hit_rate']}%")
    print(f"  Exit Reasons:    {r['exit_reasons']}")

    print(f"\n  Equity Compounding Layer ({e['risk_pct']*100:.1f}% risk)")
    print(f"  {'-'*40}")
    print(f"  Starting Equity: ${e['starting_equity']:,.0f}")
    print(f"  Ending Equity:   ${e['ending_equity']:,.0f}")
    print(f"  Total Return:    {e['total_return_pct']}%")
    print(f"  Max Drawdown:    ${e['max_drawdown']:,.0f}")

    # Direction split
    if not trades.empty:
        print(f"\n  Direction Split")
        print(f"  {'-'*40}")
        for d in ["long", "short"]:
            dt = trades[trades["direction"] == d]
            if dt.empty:
                continue
            dr = dt["r_multiple"]
            pf = dr[dr > 0].sum() / abs(dr[dr < 0].sum()) if (dr < 0).any() else 99.0
            print(f"  {d.upper():>6s}: {len(dt)} trades, WR {(dr>0).sum()/len(dr)*100:.1f}%, "
                  f"PF {pf:.2f}, Exp {dr.mean():.3f}R, PnL ${dt['pnl'].sum():+,.0f}")

    # Walk-forward
    if len(trades) >= 20:
        mid = len(trades) // 2
        h1, h2 = trades.iloc[:mid], trades.iloc[mid:]
        h1r, h2r = h1["r_multiple"], h2["r_multiple"]
        h1pf = h1r[h1r>0].sum() / abs(h1r[h1r<0].sum()) if (h1r<0).any() else 99
        h2pf = h2r[h2r>0].sum() / abs(h2r[h2r<0].sum()) if (h2r<0).any() else 99
        print(f"\n  Walk-Forward Split")
        print(f"  {'-'*40}")
        print(f"  H1: {len(h1)} trades, PF {h1pf:.2f}, Exp {h1r.mean():.3f}R")
        print(f"  H2: {len(h2)} trades, PF {h2pf:.2f}, Exp {h2r.mean():.3f}R")

    print(f"\n{'='*70}")
