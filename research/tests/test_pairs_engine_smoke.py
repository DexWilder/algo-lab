"""Smoke test for the cross-asset pairs harness.

Verifies:
1. Pair signal series produces expected entries/exits.
2. Backtest runs end-to-end on real MES + ZN bars.
3. Resulting metric dict matches Forge schema (_metrics-consumable).
4. Cost-aware: total_friction is non-zero.
5. Both freq='M' (monthly rebalance) and freq='D' (daily rebalance) supported.
6. Hedge ratios: 1:1, vol_adjusted, notional all run.
"""

from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from research.pairs_engine import (
    generate_pairs_signal, pairs_backtest, pairs_metrics,
)


def _synth_pair(n=120, freq="ME"):
    """Two synthetic monthly series where A jumps relative to B at known months.
    Designed so the rolling-z of return-spread breaches ±1 a handful of times.
    """
    dts = pd.date_range("2018-01-31", periods=n, freq=freq)
    rng = np.random.default_rng(31)
    # Common drift
    common = np.cumsum(rng.normal(0, 0.5, n))
    a_arr = 100 + common.copy()
    b_arr = 100 + common.copy()
    # Inject divergence shocks: every 25 months, A jumps +3% relative to B,
    # then 12 months later it snaps back. Creates obvious mean-reversion edges.
    for k in (25, 60, 90):
        a_arr[k:k+12] += 3.0
        # B drifts in the opposite direction during the shock window
        b_arr[k:k+12] -= 0.5
    a = pd.Series(a_arr, index=dts, name="A")
    b = pd.Series(b_arr, index=dts, name="B")
    return a, b


def test_signal_generation():
    a, b = _synth_pair()
    # Lower threshold for synthetic data — real pairs may need higher
    sig = generate_pairs_signal(a, b, lookback=12, z_threshold=1.0, exit_z=0.3)
    # Must produce some non-zero signals
    assert (sig != 0).sum() > 0, "no signals fired on synthetic mean-reverting pair"
    # Signals must be -1/0/1
    assert set(sig.unique()).issubset({-1, 0, 1})
    print(f"✓ signal generation ok ({(sig == 1).sum()} long / {(sig == -1).sum()} short / {(sig == 0).sum()} flat)")


def test_end_to_end_mes_zn_monthly():
    df_a = pd.read_csv(ROOT / "data" / "processed" / "MES_5m.csv")
    df_b = pd.read_csv(ROOT / "data" / "processed" / "ZN_5m.csv")
    res = pairs_backtest(
        df_a=df_a, df_b=df_b, asset_a="MES", asset_b="ZN",
        freq="M", lookback=12, z_threshold=1.5, exit_z=0.3,
        hedge="1:1", label="SMOKE-MES-ZN-monthly",
    )
    assert "trades_df" in res and "stats" in res
    m = pairs_metrics(res, "SMOKE-MES-ZN-monthly")
    for k in ("label", "n", "net", "pf", "median", "max_dd", "archetype", "gate_verdict"):
        assert k in m, f"missing metric key {k}"
    print(f"✓ MES/ZN monthly: n={m['n']} PF={m['pf']:.3f} net=${m['net']:.0f} median=${m['median']:.2f} → archetype={m['archetype']} gate={m['gate_verdict']}")


def test_daily_freq():
    df_a = pd.read_csv(ROOT / "data" / "processed" / "MGC_5m.csv")
    df_b = pd.read_csv(ROOT / "data" / "processed" / "ZN_5m.csv")
    res = pairs_backtest(
        df_a=df_a, df_b=df_b, asset_a="MGC", asset_b="ZN",
        freq="D", lookback=20, z_threshold=2.0, exit_z=0.5,
        hedge="1:1", label="SMOKE-MGC-ZN-daily",
    )
    m = pairs_metrics(res, "SMOKE-MGC-ZN-daily")
    assert m["n"] >= 0  # may be 0 if signal never triggers; just shouldn't crash
    print(f"✓ MGC/ZN daily: n={m['n']} PF={m['pf']:.3f} median=${m['median']:.2f}")


def test_hedge_modes():
    df_a = pd.read_csv(ROOT / "data" / "processed" / "MES_5m.csv")
    df_b = pd.read_csv(ROOT / "data" / "processed" / "ZN_5m.csv")
    for h in ("1:1", "vol_adjusted", "notional"):
        res = pairs_backtest(
            df_a=df_a, df_b=df_b, asset_a="MES", asset_b="ZN",
            freq="M", lookback=12, z_threshold=1.5, exit_z=0.3,
            hedge=h, label=f"SMOKE-hedge-{h}",
        )
        m = pairs_metrics(res, f"SMOKE-hedge-{h}")
        print(f"  hedge={h:14s}: n={m['n']:3d} PF={m['pf']:.3f}")
    print("✓ hedge modes ok")


def test_cost_aware():
    df_a = pd.read_csv(ROOT / "data" / "processed" / "MES_5m.csv")
    df_b = pd.read_csv(ROOT / "data" / "processed" / "ZN_5m.csv")
    res = pairs_backtest(
        df_a=df_a, df_b=df_b, asset_a="MES", asset_b="ZN",
        freq="M", lookback=12, z_threshold=1.5, exit_z=0.3,
        hedge="1:1", label="SMOKE-cost-check",
    )
    costs = res["stats"]["costs"]
    assert costs["cost_tier"] in ("VALIDATED", "EXPLORATION_TIER")
    if len(res["trades_df"]):
        assert costs["total_friction"] > 0, "cost-aware: friction should be > 0"
    print(f"✓ cost-aware ok (tier={costs['cost_tier']}, friction=${costs['total_friction']:.0f})")


if __name__ == "__main__":
    test_signal_generation()
    test_end_to_end_mes_zn_monthly()
    test_daily_freq()
    test_hedge_modes()
    test_cost_aware()
    print("\nALL SMOKE TESTS PASSED — pairs harness is harness-ready.")
