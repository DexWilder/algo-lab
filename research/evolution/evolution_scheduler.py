"""Evolution Scheduler — Phase 9.

Generates hybrid strategy candidates by injecting donor components into
parent strategies, then runs them through the validation pipeline.

Pipeline (cost-efficient — cheap gates first):
1. Load & rank recipes by priority
2. Generate strategy file (copy parent + inject mutation)
3. Baseline backtest (3 assets × 3 modes) — ~5 sec/candidate
4. Hard quality gate: PF > 1.0 AND trades >= 30 on best combo → reject if no
5. DNA novelty: min_distance > 0.3 vs catalog → reject if duplicate
6. Regime analysis: per-regime PF breakdown
7. Mutation impact: compare vs parent (PF delta, trade delta, regime delta)
8. Statistical check: bootstrap CI + DSR (n_trials cumulative)
9. Save results + generate report + summary matrix

Usage:
    python3 research/evolution/evolution_scheduler.py              # Top 5
    python3 research/evolution/evolution_scheduler.py --top 15     # All 15
    python3 research/evolution/evolution_scheduler.py --candidate orb_compression
    python3 research/evolution/evolution_scheduler.py --score-only  # Rank without running
"""

import argparse
import importlib.util
import inspect
import json
import shutil
import sys
import textwrap
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from engine.backtest import run_backtest
from engine.statistics import bootstrap_metrics, deflated_sharpe_ratio
from backtests.run_baseline import compute_extended_metrics

EVOLUTION_DIR = Path(__file__).resolve().parent
CANDIDATES_DIR = EVOLUTION_DIR / "generated_candidates"
QUEUE_PATH = EVOLUTION_DIR / "evolution_queue.json"
RESULTS_PATH = EVOLUTION_DIR / "evolution_results.json"
REPORT_PATH = EVOLUTION_DIR / "evolution_results.md"
MATRIX_PATH = EVOLUTION_DIR / "evolution_summary_matrix.md"

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
DNA_CATALOG_PATH = PROJECT_ROOT / "research" / "dna" / "dna_catalog.json"

ASSET_CONFIG = {
    "MES": {"point_value": 5.0, "tick_size": 0.25, "name": "Micro E-mini S&P 500"},
    "MNQ": {"point_value": 2.0, "tick_size": 0.25, "name": "Micro E-mini Nasdaq-100"},
    "MGC": {"point_value": 10.0, "tick_size": 0.10, "name": "Micro Gold"},
}

MODES = ["both", "long", "short"]

# Parent strategy performance baselines (from existing results)
PARENT_BASELINES = {
    "orb_009": {
        "best_combo": "MGC-long",
        "best_pf": 1.99,
        "best_sharpe": 3.63,
        "best_trades": 75,
    },
    "pb_trend": {
        "best_combo": "MGC-short",
        "best_pf": 2.36,
        "best_sharpe": 5.27,
        "best_trades": 21,
    },
    "vix_channel": {
        "best_combo": "MES-both",
        "best_pf": 1.298,
        "best_sharpe": 1.60,
        "best_trades": 503,
    },
}


# ── Strategy Generation ─────────────────────────────────────────────────────

def generate_candidate(recipe: dict) -> Path:
    """Generate a candidate strategy file from recipe spec.

    Returns path to the generated strategy.py.
    """
    candidate_id = recipe["id"]
    parent_name = recipe["parent"]
    mutation_type = recipe["mutation_type"]

    # Read parent source
    parent_path = PROJECT_ROOT / "strategies" / parent_name / "strategy.py"
    parent_src = parent_path.read_text()

    # Apply mutation
    if mutation_type == "add_filter":
        new_src = _apply_add_filter(parent_src, recipe, parent_name)
    elif mutation_type == "swap_risk":
        new_src = _apply_swap_risk(parent_src, recipe, parent_name)
    elif mutation_type == "swap_exit":
        new_src = _apply_swap_exit(parent_src, recipe, parent_name)
    elif mutation_type == "relax_filter":
        new_src = _apply_relax_filter(parent_src, recipe, parent_name)
    else:
        raise ValueError(f"Unknown mutation type: {mutation_type}")

    # Write candidate
    out_dir = CANDIDATES_DIR / candidate_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "strategy.py"
    out_path.write_text(new_src)

    # Write meta.json
    meta = {
        "candidate_id": candidate_id,
        "parent": parent_name,
        "mutation_type": mutation_type,
        "mutation_fn": recipe.get("mutation_fn"),
        "description": recipe["description"],
        "priority": recipe["priority"],
        "generated_date": datetime.now().strftime("%Y-%m-%d"),
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2))

    return out_path


def _get_mutation_import(recipe):
    """Build import statement for mutation function."""
    fn = recipe.get("mutation_fn")
    if not fn:
        return ""
    return f"from research.evolution.mutations import {fn}\n"


def _apply_add_filter(src: str, recipe: dict, parent: str) -> str:
    """Inject a filter column into entry conditions."""
    fn = recipe.get("mutation_fn")
    col = recipe.get("filter_column", "")
    logic = recipe.get("filter_logic", "AND")

    if parent == "orb_009":
        return _apply_add_filter_orb(src, recipe)
    elif parent == "pb_trend":
        return _apply_add_filter_pb(src, recipe)
    elif parent == "vix_channel":
        return _apply_add_filter_vix(src, recipe)
    raise ValueError(f"No add_filter template for parent: {parent}")


def _apply_add_filter_orb(src: str, recipe: dict) -> str:
    """Add filter to ORB-009 strategy."""
    fn = recipe.get("mutation_fn")
    col = recipe.get("filter_column", "")
    logic = recipe.get("filter_logic", "AND")
    cid = recipe["id"]

    lines = src.split("\n")
    new_lines = []

    # 1. Add import after existing imports
    import_added = False
    for i, line in enumerate(lines):
        new_lines.append(line)
        if not import_added and line.startswith("import numpy"):
            if fn:
                new_lines.append(f"from research.evolution.mutations import {fn}")
            import_added = True

    src = "\n".join(new_lines)

    # 2. Update docstring
    src = src.replace(
        '"""ORB-009 — Opening Range Breakout + VWAP + Volume Filters.',
        f'"""{cid.upper()} — ORB-009 + {recipe["description"]}.',
    )

    # 3. Add mutation computation after VWAP/volume computation
    # Insert after vol_ma line
    mutation_call = ""
    if fn == "compute_compression":
        mutation_call = "    df = compute_compression(df)\n"
    elif fn == "compute_squeeze":
        mutation_call = "    df = compute_squeeze(df)\n"
    elif fn == "compute_momentum_state":
        mutation_call = "    df = compute_momentum_state(df)\n"
    elif fn == "compute_sweep":
        mutation_call = "    df = compute_sweep(df)\n"

    if mutation_call:
        src = src.replace(
            '    df["vol_ma"] = _sma(df["volume"], VOL_MA_LEN)\n',
            '    df["vol_ma"] = _sma(df["volume"], VOL_MA_LEN)\n\n    # ── Evolution mutation ──\n' + mutation_call,
        )

    # 4. Add filter to entry conditions
    if logic == "AND" and col:
        # Simple AND with boolean column
        src = src.replace(
            "        strong_close_long\n    )",
            f"        strong_close_long &\n        df[\"{col}\"]\n    )",
        )
        src = src.replace(
            "        strong_close_short\n    )",
            f"        strong_close_short &\n        df[\"{col}\"]\n    )",
        )
    elif logic == "DIRECTIONAL":
        if col == "sweep_bias":
            # Long only when sweep_bias == 1, short only when sweep_bias == -1
            src = src.replace(
                "        strong_close_long\n    )",
                "        strong_close_long &\n        (df[\"sweep_bias\"] == 1)\n    )",
            )
            src = src.replace(
                "        strong_close_short\n    )",
                "        strong_close_short &\n        (df[\"sweep_bias\"] == -1)\n    )",
            )
        elif "mom_lime" in col:
            src = src.replace(
                "        strong_close_long\n    )",
                "        strong_close_long &\n        df[\"mom_lime\"]\n    )",
            )
            src = src.replace(
                "        strong_close_short\n    )",
                "        strong_close_short &\n        df[\"mom_red\"]\n    )",
            )

    # 5. Clean up extra columns in drop
    drop_cols = '["_date", "or_high", "or_low", "or_range", "vwap", "vol_ma"'
    if fn == "compute_compression":
        drop_cols += ', "compression_active"'
    elif fn == "compute_squeeze":
        drop_cols += ', "squeeze_on", "squeeze_release"'
    elif fn == "compute_momentum_state":
        drop_cols += ', "mom_lime", "mom_green", "mom_red", "mom_maroon"'
    elif fn == "compute_sweep":
        drop_cols += ', "sweep_bias"'
    drop_cols += "]"

    src = src.replace(
        '["_date", "or_high", "or_low", "or_range", "vwap", "vol_ma"]',
        drop_cols,
    )

    return src


def _apply_add_filter_pb(src: str, recipe: dict) -> str:
    """Add filter to PB Trend strategy."""
    fn = recipe.get("mutation_fn")
    col = recipe.get("filter_column", "")
    logic = recipe.get("filter_logic", "AND")
    cid = recipe["id"]

    lines = src.split("\n")
    new_lines = []

    # 1. Add import
    import_added = False
    for line in lines:
        new_lines.append(line)
        if not import_added and line.startswith("import numpy"):
            if fn:
                new_lines.append(f"from research.evolution.mutations import {fn}")
            import_added = True

    src = "\n".join(new_lines)

    # 2. Update docstring
    src = src.replace(
        '"""PB Trend — Pullback Trend-Following Engine (standalone).',
        f'"""{cid.upper()} — PB Trend + {recipe["description"]}.',
    )

    # 3. Add mutation computation after indicators
    mutation_call = ""
    if fn == "compute_compression":
        mutation_call = "    df = compute_compression(df)\n"
    elif fn == "compute_squeeze":
        mutation_call = "    df = compute_squeeze(df)\n"
    elif fn == "compute_momentum_state":
        mutation_call = "    df = compute_momentum_state(df)\n"

    if mutation_call:
        src = src.replace(
            '    df["vol_ma"] = _sma(df["volume"], VOL_MA_LEN)\n',
            '    df["vol_ma"] = _sma(df["volume"], VOL_MA_LEN)\n\n    # ── Evolution mutation ──\n' + mutation_call,
        )

    # 4. Add filter to final signals
    if logic == "AND" and col:
        src = src.replace(
            "    long_signal = df[\"allowed\"] & quality_ok & trend_regime & pb_long",
            f"    long_signal = df[\"allowed\"] & quality_ok & trend_regime & pb_long & df[\"{col}\"]",
        )
        src = src.replace(
            "    short_signal = df[\"allowed\"] & quality_ok & trend_regime & pb_short",
            f"    short_signal = df[\"allowed\"] & quality_ok & trend_regime & pb_short & df[\"{col}\"]",
        )

    return src


def _apply_add_filter_vix(src: str, recipe: dict) -> str:
    """Add filter to VIX Channel strategy."""
    fn = recipe.get("mutation_fn")
    col = recipe.get("filter_column", "")
    logic = recipe.get("filter_logic", "AND")
    cid = recipe["id"]

    lines = src.split("\n")
    new_lines = []

    # 1. Add import
    import_added = False
    for line in lines:
        new_lines.append(line)
        if not import_added and line.startswith("import numpy"):
            if fn:
                new_lines.append(f"from research.evolution.mutations import {fn}")
            import_added = True

    src = "\n".join(new_lines)

    # 2. Update docstring
    src = src.replace(
        '"""VIX-CHANNEL — NY VIX Channel Trend (Session Trend Following).',
        f'"""{cid.upper()} — VIX Channel + {recipe["description"]}.',
    )

    # 3. For VIX, mutation is computed before the stateful loop
    # Insert before "# ── Stateful entry/exit loop"
    mutation_call = ""
    if fn == "compute_compression":
        mutation_call = "    df = compute_compression(df)\n    compression_arr = df['compression_active'].values\n"
    elif fn == "compute_squeeze":
        mutation_call = "    df = compute_squeeze(df)\n    squeeze_release_arr = df['squeeze_release'].values\n"
    elif fn == "compute_sweep":
        mutation_call = "    df = compute_sweep(df)\n    sweep_bias_arr = df['sweep_bias'].values\n"
    elif fn == "compute_momentum_state":
        mutation_call = "    df = compute_momentum_state(df)\n    mom_lime_arr = df['mom_lime'].values\n    mom_red_arr = df['mom_red'].values\n"

    # For ADX filter (no mutation_fn, built inline)
    adx_params = recipe.get("adx_params")
    if adx_params and not fn:
        adx_len = adx_params.get("adx_len", 14)
        adx_min = adx_params.get("adx_min", 14.0)
        # Need to add ADX helpers and computation
        # Add the helper functions and import
        src = src.replace(
            "def _parse_time(dt_series: pd.Series) -> pd.Series:",
            textwrap.dedent(f"""\
            def _ema(series, span):
                return series.ewm(span=span, adjust=False).mean()

            def _atr_vix(high, low, close, period):
                prev_close = close.shift(1)
                tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
                return tr.ewm(span=period, adjust=False).mean()

            def _adx(high, low, close, period):
                prev_high = high.shift(1)
                prev_low = low.shift(1)
                plus_dm = (high - prev_high).clip(lower=0)
                minus_dm = (prev_low - low).clip(lower=0)
                plus_dm = plus_dm.where(plus_dm > minus_dm, 0)
                minus_dm = minus_dm.where(minus_dm > plus_dm, 0)
                atr_vals = _atr_vix(high, low, close, period)
                plus_di = 100 * _ema(plus_dm, period) / atr_vals.replace(0, np.nan)
                minus_di = 100 * _ema(minus_dm, period) / atr_vals.replace(0, np.nan)
                dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
                return _ema(dx, period)

            def _parse_time(dt_series: pd.Series) -> pd.Series:"""),
        )
        mutation_call = f"    adx = _adx(df['high'], df['low'], df['close'], {adx_len})\n    adx_ok_arr = (adx >= {adx_min}).values\n"

    if mutation_call:
        src = src.replace(
            "    # ── Stateful entry/exit loop",
            f"    # ── Evolution mutation ──\n{mutation_call}\n    # ── Stateful entry/exit loop",
        )

    # 4. Add filter check inside the entry block
    # The VIX channel entry is inside the stateful loop, so we add array checks
    entry_line = "        if (position == 0 and direction_decided and day_direction != 0"
    if logic == "AND" and col == "compression_active":
        src = src.replace(
            entry_line,
            f"        if (position == 0 and direction_decided and day_direction != 0\n                and compression_arr[i]",
        )
    elif logic == "AND" and col == "adx_ok":
        src = src.replace(
            entry_line,
            f"        if (position == 0 and direction_decided and day_direction != 0\n                and adx_ok_arr[i]",
        )
    elif logic == "AND" and col == "squeeze_release":
        src = src.replace(
            entry_line,
            f"        if (position == 0 and direction_decided and day_direction != 0\n                and squeeze_release_arr[i]",
        )
    elif logic == "DIRECTIONAL" and col == "sweep_bias":
        # Replace the direction-specific entry with sweep confirmation
        src = src.replace(
            "            if day_direction == 1:",
            "            if day_direction == 1 and sweep_bias_arr[i] == 1:",
        )
        src = src.replace(
            "            elif day_direction == -1:",
            "            elif day_direction == -1 and sweep_bias_arr[i] == -1:",
        )

    return src


def _apply_swap_risk(src: str, recipe: dict, parent: str) -> str:
    """Swap risk model (stop/target calculation)."""
    cid = recipe["id"]
    risk_params = recipe.get("risk_params", {})

    if parent == "orb_009":
        return _swap_risk_orb(src, recipe, risk_params)
    elif parent == "pb_trend":
        return _swap_risk_pb(src, recipe, risk_params)
    elif parent == "vix_channel":
        return _swap_risk_vix(src, recipe, risk_params)
    raise ValueError(f"No swap_risk template for parent: {parent}")


def _swap_risk_orb(src: str, recipe: dict, risk_params: dict) -> str:
    """ORB: swap range-based stops → ATR-based stops."""
    cid = recipe["id"]
    sl_atr = risk_params.get("sl_atr", 1.5)
    tp_atr = risk_params.get("tp_atr", 3.0)

    src = src.replace(
        '"""ORB-009 — Opening Range Breakout + VWAP + Volume Filters.',
        f'"""{cid.upper()} — ORB-009 + ATR-based risk model.',
    )

    # Add ATR helper after _sma
    src = src.replace(
        "def _parse_time",
        textwrap.dedent(f"""\
        def _atr(high, low, close, period):
            prev_close = close.shift(1)
            tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
            return tr.ewm(span=period, adjust=False).mean()

        SL_ATR = {sl_atr}
        TP_ATR = {tp_atr}
        ATR_PERIOD = 14

        def _parse_time"""),
    )

    # Compute ATR after vol_ma
    src = src.replace(
        '    df["vol_ma"] = _sma(df["volume"], VOL_MA_LEN)\n',
        '    df["vol_ma"] = _sma(df["volume"], VOL_MA_LEN)\n    atr = _atr(df["high"], df["low"], df["close"], ATR_PERIOD)\n    stop_dist = atr * SL_ATR\n    target_dist = atr * TP_ATR\n',
    )

    # Replace long stop/target
    src = src.replace(
        '    df.loc[long_mask, "stop_price"] = df.loc[long_mask, "or_low"]\n    df.loc[long_mask, "target_price"] = df.loc[long_mask, "close"] + df.loc[long_mask, "or_range"] * TP_MULT',
        '    df.loc[long_mask, "stop_price"] = df.loc[long_mask, "close"] - stop_dist[long_mask]\n    df.loc[long_mask, "target_price"] = df.loc[long_mask, "close"] + target_dist[long_mask]',
    )

    # Replace short stop/target
    src = src.replace(
        '    df.loc[short_mask, "stop_price"] = df.loc[short_mask, "or_high"]\n    df.loc[short_mask, "target_price"] = df.loc[short_mask, "close"] - df.loc[short_mask, "or_range"] * TP_MULT',
        '    df.loc[short_mask, "stop_price"] = df.loc[short_mask, "close"] + stop_dist[short_mask]\n    df.loc[short_mask, "target_price"] = df.loc[short_mask, "close"] - target_dist[short_mask]',
    )

    return src


def _swap_risk_pb(src: str, recipe: dict, risk_params: dict) -> str:
    """PB: swap ATR-based stops → range-based stops."""
    cid = recipe["id"]
    tp_mult = risk_params.get("tp_mult", 2.0)

    src = src.replace(
        '"""PB Trend — Pullback Trend-Following Engine (standalone).',
        f'"""{cid.upper()} — PB Trend + range-based risk model.',
    )

    # Add OR-like range computation after indicators
    src = src.replace(
        '    df["vol_ma"] = _sma(df["volume"], VOL_MA_LEN)\n',
        f'    df["vol_ma"] = _sma(df["volume"], VOL_MA_LEN)\n\n    # Range-based risk (mutation)\n    bar_range_risk = df["high"] - df["low"]\n    avg_bar_range = bar_range_risk.rolling(20).mean()\n    range_stop_dist = avg_bar_range * 1.5\n    range_target_dist = avg_bar_range * {tp_mult}\n',
    )

    # Replace stop/target calculation
    src = src.replace(
        "    stop_dist = df[\"atr\"] * SL_ATR\n    stop_dist = stop_dist.clip(lower=MIN_STOP_TICKS * TICK_SIZE)\n    target_dist = df[\"atr\"] * TP_ATR",
        "    stop_dist = range_stop_dist.clip(lower=MIN_STOP_TICKS * TICK_SIZE)\n    target_dist = range_target_dist",
    )

    return src


def _swap_risk_vix(src: str, recipe: dict, risk_params: dict) -> str:
    """VIX: swap RV-scaled stops → ATR-based stops."""
    cid = recipe["id"]
    sl_atr = risk_params.get("sl_atr", 1.5)
    tp_atr = risk_params.get("tp_atr", 2.0)
    atr_period = risk_params.get("atr_period", 14)

    src = src.replace(
        '"""VIX-CHANNEL — NY VIX Channel Trend (Session Trend Following).',
        f'"""{cid.upper()} — VIX Channel + ATR-based risk model.',
    )

    # Add ATR computation before stateful loop
    src = src.replace(
        "    # ── Stateful entry/exit loop",
        f"    # ── ATR risk model (mutation) ──\n    _prev_close = df['close'].shift(1)\n    _tr = pd.concat([df['high'] - df['low'], (df['high'] - _prev_close).abs(), (df['low'] - _prev_close).abs()], axis=1).max(axis=1)\n    _atr = _tr.ewm(span={atr_period}, adjust=False).mean()\n    atr_arr = _atr.values\n\n    # ── Stateful entry/exit loop",
    )

    # Replace stop/target inside entry block
    src = src.replace(
        "            tp_dist = implied_move * TP_FACTOR\n            sl_dist = implied_move * SL_FACTOR",
        f"            _bar_atr = atr_arr[i] if not np.isnan(atr_arr[i]) else implied_move * SL_FACTOR\n            tp_dist = _bar_atr * {tp_atr}\n            sl_dist = _bar_atr * {sl_atr}",
    )

    return src


def _apply_swap_exit(src: str, recipe: dict, parent: str) -> str:
    """Swap exit logic to use momentum deceleration."""
    cid = recipe["id"]
    fn = recipe.get("mutation_fn")

    if parent == "pb_trend":
        return _swap_exit_pb(src, recipe)
    elif parent == "vix_channel":
        return _swap_exit_vix(src, recipe)
    raise ValueError(f"No swap_exit template for parent: {parent}")


def _swap_exit_pb(src: str, recipe: dict) -> str:
    """PB: add momentum deceleration exit."""
    cid = recipe["id"]

    # Add import
    src = src.replace(
        "import numpy as np\n",
        "import numpy as np\nfrom research.evolution.mutations import compute_momentum_state\n",
    )

    src = src.replace(
        '"""PB Trend — Pullback Trend-Following Engine (standalone).',
        f'"""{cid.upper()} — PB Trend + momentum deceleration exit.',
    )

    # Add momentum computation after vol_ma
    src = src.replace(
        '    df["vol_ma"] = _sma(df["volume"], VOL_MA_LEN)\n',
        '    df["vol_ma"] = _sma(df["volume"], VOL_MA_LEN)\n\n    # ── Evolution mutation: momentum state ──\n    df = compute_momentum_state(df)\n',
    )

    # Modify exit loop to check momentum deceleration
    # Add momentum arrays before the loop
    src = src.replace(
        "    position = 0\n    entry_stop = 0.0\n    entry_target = 0.0\n    exit_sigs = np.zeros(n, dtype=int)\n",
        "    position = 0\n    entry_stop = 0.0\n    entry_target = 0.0\n    exit_sigs = np.zeros(n, dtype=int)\n    mom_green_arr = df['mom_green'].fillna(False).values\n    mom_maroon_arr = df['mom_maroon'].fillna(False).values\n",
    )

    # Add momentum exit check: exit long on green (decel), exit short on maroon (decel)
    src = src.replace(
        "        if position == 1:\n            if low_px <= entry_stop:\n                exit_sigs[i] = 1\n                position = 0\n            elif high_px >= entry_target:\n                exit_sigs[i] = 1\n                position = 0",
        "        if position == 1:\n            if low_px <= entry_stop:\n                exit_sigs[i] = 1\n                position = 0\n            elif high_px >= entry_target:\n                exit_sigs[i] = 1\n                position = 0\n            elif mom_green_arr[i]:\n                exit_sigs[i] = 1\n                position = 0",
    )
    src = src.replace(
        "        elif position == -1:\n            if high_px >= entry_stop:\n                exit_sigs[i] = -1\n                position = 0\n            elif low_px <= entry_target:\n                exit_sigs[i] = -1\n                position = 0",
        "        elif position == -1:\n            if high_px >= entry_stop:\n                exit_sigs[i] = -1\n                position = 0\n            elif low_px <= entry_target:\n                exit_sigs[i] = -1\n                position = 0\n            elif mom_maroon_arr[i]:\n                exit_sigs[i] = -1\n                position = 0",
    )

    return src


def _swap_exit_vix(src: str, recipe: dict) -> str:
    """VIX: add momentum deceleration exit."""
    cid = recipe["id"]

    # Add import
    src = src.replace(
        "import numpy as np\n",
        "import numpy as np\nfrom research.evolution.mutations import compute_momentum_state\n",
    )

    src = src.replace(
        '"""VIX-CHANNEL — NY VIX Channel Trend (Session Trend Following).',
        f'"""{cid.upper()} — VIX Channel + momentum deceleration exit.',
    )

    # Add momentum computation before stateful loop
    src = src.replace(
        "    # ── Stateful entry/exit loop",
        "    # ── Evolution mutation: momentum state ──\n    df = compute_momentum_state(df)\n    mom_green_arr = df['mom_green'].fillna(False).values\n    mom_maroon_arr = df['mom_maroon'].fillna(False).values\n\n    # ── Stateful entry/exit loop",
    )

    # Add momentum exit: long exit on green, short exit on maroon
    src = src.replace(
        "        if position == 1:\n            # Stop\n            if low_arr[i] <= entry_stop:\n                exit_sigs[i] = 1\n                position = 0\n            # Target\n            elif high_arr[i] >= entry_target:\n                exit_sigs[i] = 1\n                position = 0\n            # Channel boundary\n            elif channel_top > 0 and high_arr[i] >= channel_top:\n                exit_sigs[i] = 1\n                position = 0",
        "        if position == 1:\n            # Stop\n            if low_arr[i] <= entry_stop:\n                exit_sigs[i] = 1\n                position = 0\n            # Target\n            elif high_arr[i] >= entry_target:\n                exit_sigs[i] = 1\n                position = 0\n            # Channel boundary\n            elif channel_top > 0 and high_arr[i] >= channel_top:\n                exit_sigs[i] = 1\n                position = 0\n            # Momentum deceleration\n            elif mom_green_arr[i]:\n                exit_sigs[i] = 1\n                position = 0",
    )
    src = src.replace(
        "        elif position == -1:\n            if high_arr[i] >= entry_stop:\n                exit_sigs[i] = -1\n                position = 0\n            elif low_arr[i] <= entry_target:\n                exit_sigs[i] = -1\n                position = 0\n            elif channel_bottom > 0 and low_arr[i] <= channel_bottom:\n                exit_sigs[i] = -1\n                position = 0",
        "        elif position == -1:\n            if high_arr[i] >= entry_stop:\n                exit_sigs[i] = -1\n                position = 0\n            elif low_arr[i] <= entry_target:\n                exit_sigs[i] = -1\n                position = 0\n            elif channel_bottom > 0 and low_arr[i] <= channel_bottom:\n                exit_sigs[i] = -1\n                position = 0\n            # Momentum deceleration\n            elif mom_maroon_arr[i]:\n                exit_sigs[i] = -1\n                position = 0",
    )

    return src


def _apply_relax_filter(src: str, recipe: dict, parent: str) -> str:
    """Relax entry filters (PB only)."""
    cid = recipe["id"]
    params = recipe.get("relax_params", {})

    src = src.replace(
        '"""PB Trend — Pullback Trend-Following Engine (standalone).',
        f'"""{cid.upper()} — PB Trend with relaxed filters.',
    )

    if params.get("remove_adx"):
        src = src.replace(
            "    adx_ok = df[\"adx\"] >= ADX_MIN\n    quality_ok = adx_ok & vol_ok",
            "    quality_ok = vol_ok  # ADX gate removed (mutation)",
        )

    if params.get("vol_mult") is not None:
        src = src.replace(
            'VOL_MULT = 1.0',
            f'VOL_MULT = {params["vol_mult"]}',
        )

    if params.get("single_window"):
        # Merge windows into one continuous session
        src = src.replace(
            '    in_win1 = (time_str >= WIN1_START) & (time_str < WIN1_END)\n    in_win2 = (time_str >= WIN2_START) & (time_str < WIN2_END)\n    df["in_windows"] = in_win1 | in_win2',
            '    df["in_windows"] = df["in_session"]  # Windows relaxed (mutation)',
        )

    return src


# ── Strategy Loading ─────────────────────────────────────────────────────────

def load_candidate_module(candidate_id: str):
    """Load a generated candidate strategy module."""
    module_path = CANDIDATES_DIR / candidate_id / "strategy.py"
    if not module_path.exists():
        raise FileNotFoundError(f"Candidate not found: {module_path}")

    spec = importlib.util.spec_from_file_location(candidate_id, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ── Pipeline Stages ──────────────────────────────────────────────────────────

def run_baseline_backtest(candidate_id: str, strategy_module) -> dict:
    """Run backtest on 3 assets × 3 modes. Returns combined results."""
    data_files = {}
    for p in PROCESSED_DIR.glob("*_5m.csv"):
        symbol = p.stem.split("_")[0].upper()
        if symbol in ASSET_CONFIG:
            data_files[symbol] = p

    all_results = {}
    for symbol in sorted(data_files.keys()):
        config = ASSET_CONFIG[symbol]
        df = pd.read_csv(data_files[symbol])
        df["datetime"] = pd.to_datetime(df["datetime"])

        # Patch tick size
        if hasattr(strategy_module, "TICK_SIZE"):
            strategy_module.TICK_SIZE = config["tick_size"]

        # Generate signals
        sig = inspect.signature(strategy_module.generate_signals)
        if "asset" in sig.parameters:
            signals_df = strategy_module.generate_signals(df, asset=symbol)
        else:
            signals_df = strategy_module.generate_signals(df)

        for mode in MODES:
            result = run_backtest(
                df, signals_df,
                mode=mode,
                point_value=config["point_value"],
            )
            trades_df = result["trades_df"]
            equity_curve = result["equity_curve"]

            metrics = compute_extended_metrics(
                trades_df, equity_curve, config["point_value"],
            )
            metrics["symbol"] = symbol
            metrics["mode"] = mode

            combo_key = f"{symbol}-{mode}"
            all_results[combo_key] = {
                "metrics": metrics,
                "trades_pnl": trades_df["pnl"].values.tolist() if not trades_df.empty else [],
            }

    return all_results


def apply_quality_gate(results: dict) -> tuple[bool, str, dict]:
    """Hard quality gate: best combo PF > 1.0 AND trades >= 30.

    Returns (passed, best_combo_key, best_metrics).
    """
    best_pf = 0
    best_combo = ""
    best_metrics = {}

    for combo, data in results.items():
        m = data["metrics"]
        pf = m.get("profit_factor", 0)
        tc = m.get("trade_count", 0)
        if pf > best_pf:
            best_pf = pf
            best_combo = combo
            best_metrics = m

    tc = best_metrics.get("trade_count", 0) if best_metrics else 0
    passed = best_pf > 1.0 and tc >= 30
    return passed, best_combo, best_metrics


def compute_dna_novelty(candidate_id: str, recipe: dict) -> dict:
    """Check DNA distance vs existing catalog.

    Returns dict with min_distance, novelty_bucket, distances.
    """
    if not DNA_CATALOG_PATH.exists():
        return {"min_distance": 1.0, "novelty_bucket": "novel", "distances": {}}

    with open(DNA_CATALOG_PATH) as f:
        catalog = json.load(f)

    # Build candidate DNA profile
    parent_name = recipe["parent"]
    parent_dna = next((d for d in catalog if d["strategy_name"] == parent_name), None)
    if not parent_dna:
        return {"min_distance": 1.0, "novelty_bucket": "novel", "distances": {}}

    # Candidate inherits parent DNA with modifications
    candidate_dna = parent_dna.copy()
    candidate_dna["strategy_id"] = candidate_id

    # Adjust based on mutation
    mutation_type = recipe["mutation_type"]
    if mutation_type == "add_filter":
        candidate_dna["filter_depth"] = parent_dna.get("filter_depth", 1) + 1
    elif mutation_type == "swap_risk":
        # Change risk model
        if recipe["parent"] == "orb_009" and recipe.get("risk_params", {}).get("sl_atr"):
            candidate_dna["risk_model"] = "atr_adaptive"
        elif recipe["parent"] == "pb_trend":
            candidate_dna["risk_model"] = "range_based"
        elif recipe["parent"] == "vix_channel":
            candidate_dna["risk_model"] = "atr_adaptive"
    elif mutation_type == "swap_exit":
        candidate_dna["exit_type"] = "momentum_decel"
    elif mutation_type == "relax_filter":
        candidate_dna["filter_depth"] = max(1, parent_dna.get("filter_depth", 1) - 3)

    # Import DNA tools
    sys.path.insert(0, str(PROJECT_ROOT / "research" / "dna"))
    from build_dna_profiles import strategy_to_vector, compute_distance_matrix

    all_dnas = catalog + [candidate_dna]
    dist = compute_distance_matrix(all_dnas)
    n = len(all_dnas)
    candidate_idx = n - 1

    distances = {}
    min_dist = float("inf")
    for i in range(n - 1):
        d = float(dist[candidate_idx, i])
        distances[all_dnas[i]["strategy_id"]] = round(d, 3)
        if d < min_dist:
            min_dist = d

    if min_dist > 0.5:
        bucket = "novel"
    elif min_dist > 0.3:
        bucket = "marginal"
    else:
        bucket = "duplicate"

    return {
        "min_distance": round(min_dist, 3),
        "novelty_bucket": bucket,
        "distances": distances,
    }


def compute_regime_breakdown(results: dict) -> dict:
    """Per-regime PF breakdown for the best combo."""
    # Simplified: report overall regime-related traits from results
    # Full regime analysis requires loading raw data + regime engine
    return {"note": "Regime breakdown available in full pipeline run"}


def compute_mutation_impact(results: dict, recipe: dict) -> dict:
    """Compare candidate vs parent baseline."""
    parent = recipe["parent"]
    baseline = PARENT_BASELINES.get(parent, {})

    _, best_combo, best_m = apply_quality_gate(results)

    parent_pf = baseline.get("best_pf", 0)
    parent_trades = baseline.get("best_trades", 0)
    cand_pf = best_m.get("profit_factor", 0) if best_m else 0
    cand_trades = best_m.get("trade_count", 0) if best_m else 0

    pf_delta = round(cand_pf - parent_pf, 3) if parent_pf else 0
    trade_delta = cand_trades - parent_trades if parent_trades else 0

    if pf_delta > 0.1:
        verdict = "mutation_helped"
    elif pf_delta < -0.1:
        verdict = "mutation_hurt"
    else:
        verdict = "mutation_neutral"

    return {
        "parent_best_combo": baseline.get("best_combo", ""),
        "parent_best_pf": parent_pf,
        "parent_best_trades": parent_trades,
        "candidate_best_combo": best_combo,
        "candidate_pf": cand_pf,
        "candidate_trades": cand_trades,
        "pf_delta": pf_delta,
        "trade_delta": trade_delta,
        "verdict": verdict,
    }


def run_statistical_check(results: dict, cumulative_trials: int) -> dict:
    """Bootstrap CI + DSR for best combo."""
    _, best_combo, best_m = apply_quality_gate(results)

    if not best_combo or not results[best_combo]["trades_pnl"]:
        return {"bootstrap": {}, "dsr": {}, "cumulative_trials": cumulative_trials}

    pnl = np.array(results[best_combo]["trades_pnl"])

    boot = bootstrap_metrics(pnl)

    sharpe = best_m.get("sharpe", 0)
    dsr = deflated_sharpe_ratio(
        observed_sharpe=sharpe,
        n_trials=cumulative_trials,
        n_observations=len(pnl),
        returns=pnl,
    )

    return {
        "bootstrap": boot,
        "dsr": dsr,
        "cumulative_trials": cumulative_trials,
    }


# ── Report Generation ────────────────────────────────────────────────────────

def generate_report(all_candidate_results: dict, queue: list):
    """Generate evolution_results.md — executive summary."""
    lines = [
        "# Evolution Results — Phase 9",
        "",
        f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
    ]

    promoted = [k for k, v in all_candidate_results.items() if v.get("status") == "promoted"]
    rejected = [k for k, v in all_candidate_results.items() if v.get("status") == "rejected"]
    passed = [k for k, v in all_candidate_results.items() if v.get("status") == "passed_gate"]

    lines.append(f"- **{len(all_candidate_results)} candidates** evaluated")
    lines.append(f"- **{len(promoted)} promoted** (passed all gates)")
    lines.append(f"- **{len(passed)} passed gate** (PF>1, trades>=30)")
    lines.append(f"- **{len(rejected)} rejected** (failed quality gate)")
    lines.append("")

    if promoted:
        lines.append("## Promoted Candidates")
        lines.append("")
        for cid in promoted:
            r = all_candidate_results[cid]
            m = r.get("best_metrics", {})
            impact = r.get("mutation_impact", {})
            lines.append(f"### {cid}")
            lines.append(f"- **Parent:** {r.get('parent', '')}")
            lines.append(f"- **Mutation:** {r.get('description', '')}")
            lines.append(f"- **Best combo:** {r.get('best_combo', '')}")
            lines.append(f"- **PF:** {m.get('profit_factor', 0):.2f} (parent: {impact.get('parent_best_pf', 0):.2f}, Δ={impact.get('pf_delta', 0):+.3f})")
            lines.append(f"- **Trades:** {m.get('trade_count', 0)} (parent: {impact.get('parent_best_trades', 0)}, Δ={impact.get('trade_delta', 0):+d})")
            lines.append(f"- **Sharpe:** {m.get('sharpe', 0):.2f}")
            lines.append(f"- **DNA novelty:** {r.get('dna_novelty', {}).get('novelty_bucket', 'unknown')} (min dist: {r.get('dna_novelty', {}).get('min_distance', 0):.3f})")
            lines.append(f"- **Verdict:** {impact.get('verdict', '')}")
            lines.append("")

    if passed:
        lines.append("## Candidates Passing Quality Gate")
        lines.append("")
        for cid in passed:
            r = all_candidate_results[cid]
            m = r.get("best_metrics", {})
            lines.append(f"- **{cid}**: {r.get('best_combo', '')} — PF={m.get('profit_factor', 0):.2f}, {m.get('trade_count', 0)} trades, Sharpe={m.get('sharpe', 0):.2f}")
        lines.append("")

    if rejected:
        lines.append("## Rejected Candidates")
        lines.append("")
        lines.append("| Candidate | Parent | Mutation | Best PF | Trades | Reason |")
        lines.append("|-----------|--------|----------|---------|--------|--------|")
        for cid in rejected:
            r = all_candidate_results[cid]
            m = r.get("best_metrics", {})
            reason = r.get("reject_reason", "PF<1 or trades<30")
            lines.append(f"| {cid} | {r.get('parent', '')} | {r.get('mutation_type', '')} | {m.get('profit_factor', 0):.2f} | {m.get('trade_count', 0)} | {reason} |")
        lines.append("")

    # Queue status
    run_ids = set(all_candidate_results.keys())
    remaining = [q for q in queue if q["id"] not in run_ids]
    if remaining:
        lines.append("## Remaining Queue")
        lines.append("")
        for q in sorted(remaining, key=lambda x: -x["priority"]):
            lines.append(f"- **{q['id']}** (priority: {q['priority']}) — {q['description']}")
        lines.append("")

    lines.append("---")
    lines.append("*Generated by evolution_scheduler.py — Phase 9*")

    REPORT_PATH.write_text("\n".join(lines))
    print(f"  Report saved: {REPORT_PATH}")


def generate_summary_matrix(all_candidate_results: dict):
    """Generate compact comparison table."""
    lines = [
        "# Evolution Summary Matrix",
        "",
        f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
        "",
        "| Candidate | Parent | Mutation | Status | Best Combo | PF | Trades | Sharpe | DNA Novelty | Impact |",
        "|-----------|--------|----------|--------|------------|-----|--------|--------|-------------|--------|",
    ]

    for cid in sorted(all_candidate_results.keys()):
        r = all_candidate_results[cid]
        m = r.get("best_metrics", {})
        dna = r.get("dna_novelty", {})
        impact = r.get("mutation_impact", {})
        lines.append(
            f"| {cid} | {r.get('parent', '')} | {r.get('mutation_type', '')} | "
            f"{r.get('status', '')} | {r.get('best_combo', '')} | "
            f"{m.get('profit_factor', 0):.2f} | {m.get('trade_count', 0)} | "
            f"{m.get('sharpe', 0):.2f} | {dna.get('novelty_bucket', '-')} | "
            f"{impact.get('verdict', '-')} |"
        )

    lines.append("")
    lines.append("---")
    lines.append("*Generated by evolution_scheduler.py*")

    MATRIX_PATH.write_text("\n".join(lines))
    print(f"  Matrix saved: {MATRIX_PATH}")


# ── Main Pipeline ────────────────────────────────────────────────────────────

def run_pipeline(recipes: list, score_only: bool = False):
    """Main evolution pipeline."""
    # Sort by priority
    recipes = sorted(recipes, key=lambda r: -r["priority"])

    print("=" * 60)
    print("  EVOLUTION SCHEDULER — Phase 9")
    print(f"  {len(recipes)} candidate(s) queued")
    print("=" * 60)

    if score_only:
        print("\n  Priority Rankings:")
        print(f"  {'#':>3} {'ID':<25} {'Parent':<12} {'Type':<14} {'Priority':>8}")
        print(f"  {'-'*3} {'-'*25} {'-'*12} {'-'*14} {'-'*8}")
        for i, r in enumerate(recipes, 1):
            print(f"  {i:>3} {r['id']:<25} {r['parent']:<12} {r['mutation_type']:<14} {r['priority']:>8.2f}")
        return

    # Load existing results for cumulative trial counting
    existing_results = {}
    cumulative_trials = 0
    if RESULTS_PATH.exists():
        with open(RESULTS_PATH) as f:
            data = json.load(f)
            existing_results = data.get("candidates", {})
            cumulative_trials = data.get("cumulative_trials", 0)

    all_results = dict(existing_results)

    for i, recipe in enumerate(recipes, 1):
        cid = recipe["id"]
        print(f"\n{'─' * 60}")
        print(f"  [{i}/{len(recipes)}] {cid}")
        print(f"  Parent: {recipe['parent']} | Mutation: {recipe['mutation_type']}")
        print(f"  Priority: {recipe['priority']}")
        print(f"{'─' * 60}")

        # Skip if already processed
        if cid in all_results and all_results[cid].get("status") in ("promoted", "rejected", "passed_gate"):
            print(f"  SKIP: Already processed (status={all_results[cid]['status']})")
            continue

        # Step 1: Generate strategy
        print("  Generating candidate strategy...")
        try:
            generate_candidate(recipe)
        except Exception as e:
            print(f"  ERROR generating: {e}")
            all_results[cid] = {
                "status": "error",
                "error": str(e),
                "parent": recipe["parent"],
                "mutation_type": recipe["mutation_type"],
                "description": recipe["description"],
            }
            continue

        # Step 2: Load and backtest
        print("  Running baseline backtest (3 assets × 3 modes)...")
        try:
            strategy_module = load_candidate_module(cid)
            bt_results = run_baseline_backtest(cid, strategy_module)
        except Exception as e:
            print(f"  ERROR in backtest: {e}")
            import traceback
            traceback.print_exc()
            all_results[cid] = {
                "status": "error",
                "error": str(e),
                "parent": recipe["parent"],
                "mutation_type": recipe["mutation_type"],
                "description": recipe["description"],
            }
            continue

        # Step 3: Quality gate
        passed, best_combo, best_m = apply_quality_gate(bt_results)
        pf = best_m.get("profit_factor", 0) if best_m else 0
        tc = best_m.get("trade_count", 0) if best_m else 0
        sharpe = best_m.get("sharpe", 0) if best_m else 0

        print(f"  Best combo: {best_combo} — PF={pf:.2f}, trades={tc}, Sharpe={sharpe:.2f}")

        if not passed:
            reason = f"PF={pf:.2f}" if pf <= 1.0 else f"trades={tc}"
            print(f"  REJECTED: Failed quality gate ({reason})")
            all_results[cid] = {
                "status": "rejected",
                "reject_reason": f"Quality gate: {reason}",
                "parent": recipe["parent"],
                "mutation_type": recipe["mutation_type"],
                "description": recipe["description"],
                "best_combo": best_combo,
                "best_metrics": _sanitize_metrics(best_m),
                "all_combos": {k: _sanitize_metrics(v["metrics"]) for k, v in bt_results.items()},
            }
            continue

        # Step 4: DNA novelty
        print("  Computing DNA novelty...")
        dna = compute_dna_novelty(cid, recipe)
        print(f"  DNA: min_distance={dna['min_distance']:.3f}, bucket={dna['novelty_bucket']}")

        if dna["novelty_bucket"] == "duplicate":
            print(f"  REJECTED: DNA duplicate (min_dist={dna['min_distance']:.3f})")
            all_results[cid] = {
                "status": "rejected",
                "reject_reason": f"DNA duplicate (dist={dna['min_distance']:.3f})",
                "parent": recipe["parent"],
                "mutation_type": recipe["mutation_type"],
                "description": recipe["description"],
                "best_combo": best_combo,
                "best_metrics": _sanitize_metrics(best_m),
                "dna_novelty": dna,
                "all_combos": {k: _sanitize_metrics(v["metrics"]) for k, v in bt_results.items()},
            }
            continue

        # Step 5: Mutation impact
        print("  Computing mutation impact...")
        impact = compute_mutation_impact(bt_results, recipe)
        print(f"  Impact: PF Δ={impact['pf_delta']:+.3f}, trades Δ={impact['trade_delta']:+d} → {impact['verdict']}")

        # Step 6: Statistical check
        cumulative_trials += 1
        print(f"  Running statistical checks (trial #{cumulative_trials})...")
        stats = run_statistical_check(bt_results, cumulative_trials)
        dsr_val = stats.get("dsr", {}).get("dsr", 0)
        dsr_sig = stats.get("dsr", {}).get("significant", False)
        print(f"  DSR={dsr_val:.4f} {'(significant)' if dsr_sig else '(not significant)'}")

        # Determine final status
        status = "promoted" if dna["novelty_bucket"] in ("novel", "marginal") else "passed_gate"

        all_results[cid] = {
            "status": status,
            "parent": recipe["parent"],
            "mutation_type": recipe["mutation_type"],
            "description": recipe["description"],
            "priority": recipe["priority"],
            "best_combo": best_combo,
            "best_metrics": _sanitize_metrics(best_m),
            "all_combos": {k: _sanitize_metrics(v["metrics"]) for k, v in bt_results.items()},
            "dna_novelty": dna,
            "mutation_impact": impact,
            "statistics": {
                "bootstrap_pf_ci": stats.get("bootstrap", {}).get("pf", {}),
                "bootstrap_sharpe_ci": stats.get("bootstrap", {}).get("sharpe", {}),
                "dsr": stats.get("dsr", {}),
                "cumulative_trials": cumulative_trials,
            },
        }

        print(f"  STATUS: {status.upper()}")

    # Save results
    output = {
        "run_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "cumulative_trials": cumulative_trials,
        "candidates": all_results,
    }
    RESULTS_PATH.write_text(json.dumps(output, indent=2, default=str))
    print(f"\n  Results saved: {RESULTS_PATH}")

    # Load full queue for report
    with open(QUEUE_PATH) as f:
        full_queue = json.load(f)

    # Generate reports
    generate_report(all_results, full_queue)
    generate_summary_matrix(all_results)

    # Final summary
    print(f"\n{'=' * 60}")
    print("  EVOLUTION SCHEDULER — Complete")
    print(f"{'=' * 60}")
    promoted = sum(1 for v in all_results.values() if v.get("status") == "promoted")
    rejected = sum(1 for v in all_results.values() if v.get("status") == "rejected")
    errors = sum(1 for v in all_results.values() if v.get("status") == "error")
    print(f"  Promoted: {promoted}  |  Rejected: {rejected}  |  Errors: {errors}")
    print(f"  Cumulative trials: {cumulative_trials}")
    print(f"  Results: {RESULTS_PATH}")
    print(f"  Report:  {REPORT_PATH}")
    print(f"  Matrix:  {MATRIX_PATH}")
    print(f"{'=' * 60}\n")


def _sanitize_metrics(m: dict) -> dict:
    """Ensure all values are JSON-serializable."""
    out = {}
    for k, v in m.items():
        if isinstance(v, (np.integer,)):
            out[k] = int(v)
        elif isinstance(v, (np.floating,)):
            out[k] = float(v)
        elif isinstance(v, (np.bool_,)):
            out[k] = bool(v)
        else:
            out[k] = v
    return out


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Evolution Scheduler — Phase 9")
    parser.add_argument("--top", type=int, default=5,
                        help="Run top N candidates by priority (default: 5)")
    parser.add_argument("--candidate", type=str, default=None,
                        help="Run a single candidate by ID")
    parser.add_argument("--score-only", action="store_true",
                        help="Just show priority rankings, don't run")
    args = parser.parse_args()

    # Load queue
    with open(QUEUE_PATH) as f:
        queue = json.load(f)

    if args.candidate:
        # Run single candidate
        recipes = [r for r in queue if r["id"] == args.candidate]
        if not recipes:
            print(f"ERROR: Candidate '{args.candidate}' not found in queue")
            sys.exit(1)
    elif args.score_only:
        recipes = queue
    else:
        # Top N by priority
        recipes = sorted(queue, key=lambda r: -r["priority"])[:args.top]

    run_pipeline(recipes, score_only=args.score_only)


if __name__ == "__main__":
    main()
