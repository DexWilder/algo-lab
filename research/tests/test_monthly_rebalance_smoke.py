"""Smoke test for the monthly-rebalance harness.

Verifies:
1. Signal schema match (signal/exit_signal columns)
2. Single long entry → exit at next rebalance bar
3. Sign flips (long → short) close + reopen on the same bar
4. Trailing position closes at last bar
5. build_policy_differential_signal produces sensible -1/0 series
6. End-to-end monthly_rebalance_run with synthetic signals on real 6J bars
7. Output trades_df conforms to Forge `_metrics` consumption
"""

from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from research.monthly_rebalance_engine import (
    generate_monthly_rebalance_signals,
    monthly_rebalance_run,
    build_policy_differential_signal,
)


def _synth_bars_long(n_months=12, freq="1h"):
    """Synthesize n_months of continuous bars at the requested freq.
    Using hourly bars keeps the synth file small while still spanning months
    so monthly-rebalance signal dates can land inside the data range."""
    n_hours = n_months * 31 * 24  # generous upper bound
    dts = pd.date_range("2024-01-01 00:00", periods=n_hours, freq=freq)
    rng = np.random.default_rng(11)
    close = 100 + np.cumsum(rng.normal(0, 0.05, n_hours))
    df = pd.DataFrame({
        "datetime": dts,
        "open": close + rng.normal(0, 0.02, n_hours),
        "high": close + np.abs(rng.normal(0, 0.05, n_hours)),
        "low": close - np.abs(rng.normal(0, 0.05, n_hours)),
        "close": close,
        "volume": rng.integers(50, 500, n_hours),
    })
    return df


def test_single_long_then_exit():
    df = _synth_bars_long(n_months=3)
    sig = pd.Series({"2024-01-31": 1, "2024-02-29": 0})
    out = generate_monthly_rebalance_signals(df, sig)
    assert set(out.columns) >= {"signal", "exit_signal", "stop_price", "target_price"}
    n_entries = int((out["signal"] == 1).sum())
    n_exits = int((out["exit_signal"] == 1).sum())
    assert n_entries == 1, f"expected 1 long entry, got {n_entries}"
    assert n_exits == 1, f"expected 1 long exit, got {n_exits}"
    # Exit must come after entry
    entry_idx = int(np.argmax(out["signal"].values == 1))
    exit_idx = int(np.argmax(out["exit_signal"].values == 1))
    assert exit_idx > entry_idx
    print("✓ single long + exit at next rebalance ok")


def test_sign_flip():
    df = _synth_bars_long(n_months=4)
    sig = pd.Series({"2024-01-31": 1, "2024-02-29": -1, "2024-03-29": 0})
    out = generate_monthly_rebalance_signals(df, sig)
    n_long = int((out["signal"] == 1).sum())
    n_short = int((out["signal"] == -1).sum())
    n_exit_long = int((out["exit_signal"] == 1).sum())
    n_exit_short = int((out["exit_signal"] == -1).sum())
    assert n_long == 1 and n_short == 1, f"expected 1L+1S entries; got {n_long}+{n_short}"
    assert n_exit_long == 1 and n_exit_short == 1, f"expected matched exits; got {n_exit_long}+{n_exit_short}"
    print("✓ sign flip (long → short) ok")


def test_trailing_close_at_last_bar():
    df = _synth_bars_long(n_months=2)
    # Open long at Jan 31, no subsequent signal — should close at last bar
    sig = pd.Series({"2024-01-31": 1})
    out = generate_monthly_rebalance_signals(df, sig)
    assert int((out["signal"] == 1).sum()) == 1
    assert int((out["exit_signal"] == 1).sum()) == 1
    # Last exit must be at or near last bar
    exit_idx = int(np.argmax(out["exit_signal"].values == 1))
    assert exit_idx == len(out) - 1, f"trailing exit must be at last bar, got {exit_idx} of {len(out)}"
    print("✓ trailing close at last bar ok")


def test_policy_differential_builder():
    # Build a Fed/BoJ scenario where spread is steadily rising above its
    # 12-month median for the last 3 months.
    dts = pd.date_range("2023-01-31", periods=24, freq="ME")
    fed = pd.Series(np.linspace(0.5, 5.5, 24), index=dts)  # steady rise
    boj = pd.Series(np.full(24, 0.1), index=dts)  # constant
    sig = build_policy_differential_signal(fed, boj, lookback_months=12)
    # Only months where median is computable (last 12) and spread > median AND Δ>=0
    assert len(sig) >= 1, "should have at least one usable month"
    # All non-zero signals must be -1 (rule is short-only)
    nonzero = sig[sig != 0]
    assert set(nonzero.unique()).issubset({-1}), f"non-zero must be -1; got {nonzero.unique()}"
    # Late months (high spread, rising) must be -1
    assert int(sig.iloc[-1]) == -1, "final month must signal short under monotone-rising spread"
    print(f"✓ policy-differential builder ok (n_nonzero={int((sig != 0).sum())} / n_total={len(sig)})")


def test_end_to_end_6j():
    """Run a synthetic 12-month signal series against real 6J 5m bars."""
    from research.fql_forge_batch_runner import _metrics
    asset_path = ROOT / "data" / "processed" / "6J_5m.csv"
    df = pd.read_csv(asset_path)
    df["datetime"] = pd.to_datetime(df["datetime"])
    # Build month-ends inside the data range
    first_ts = df["datetime"].min()
    last_ts = df["datetime"].max()
    month_ends = pd.date_range(first_ts.normalize(), last_ts.normalize(), freq="ME")
    # Alternate -1 / 0 / -1 / 0 ... (short / flat) — canonical FX-carry pattern
    sig = pd.Series([(-1 if i % 2 == 0 else 0) for i in range(len(month_ends))], index=month_ends)
    res = monthly_rebalance_run(asset="6J", signal=sig, label="SMOKE-CRY-6J")
    assert "trades_df" in res, "missing trades_df"
    assert "stats" in res and "costs" in res["stats"], "missing cost block"
    m = _metrics(res["trades_df"], "SMOKE-CRY-6J", costs=res["stats"]["costs"])
    for k in ("label", "n", "net", "pf", "median", "max_dd", "archetype", "gate_verdict"):
        assert k in m, f"metric dict missing {k}"
    print(f"✓ end-to-end 6J smoke: n={m['n']} PF={m['pf']:.3f} net=${m['net']:.0f} median=${m['median']:.2f} archetype={m['archetype']} gate={m['gate_verdict']}")


if __name__ == "__main__":
    test_single_long_then_exit()
    test_sign_flip()
    test_trailing_close_at_last_bar()
    test_policy_differential_builder()
    test_end_to_end_6j()
    print("\nALL SMOKE TESTS PASSED — monthly rebalance harness is harness-ready.")
