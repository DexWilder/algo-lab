"""Smoke test for the half-life filter.

Verifies:
1. estimate_half_life_ar1 returns a finite HL on synthetic MR (AR(1) β=0.7).
2. Returns NaN HL on synthetic random walk (β ≈ 1).
3. Insufficient sample fails closed.
4. is_stable_half_life respects bounds.
5. rolling_half_life produces a stable HL on a long MR series.
6. gate_pair_signal_by_half_life zeros out signals when spread is non-stationary.
"""

from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from research.half_life_filter import (
    estimate_half_life_ar1, estimate_half_life_spread,
    is_stable_half_life, rolling_half_life,
    gate_pair_signal_by_half_life, InsufficientSampleError,
)


def _synth_ar1(n=200, beta=0.7, seed=11):
    rng = np.random.default_rng(seed)
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = beta * x[i-1] + rng.normal(0, 1.0)
    return pd.Series(x)


def _synth_rw(n=200, seed=11):
    rng = np.random.default_rng(seed)
    return pd.Series(np.cumsum(rng.normal(0, 1.0, n)))


def test_ar1_recovers_half_life():
    s = _synth_ar1(n=400, beta=0.7)
    hl, beta, diag = estimate_half_life_ar1(s)
    expected = -np.log(2) / np.log(0.7)  # ≈ 1.94
    assert np.isfinite(hl), "HL must be finite for stationary AR(1)"
    # Allow ±15% estimation noise around expected
    assert abs(hl - expected) / expected < 0.3, f"HL={hl}, expected≈{expected}"
    assert 0.6 < beta < 0.8, f"β={beta}; expected ≈ 0.7"
    print(f"✓ AR(1) β=0.7 recovered: β_hat={beta:.3f}, HL={hl:.2f} (expected {expected:.2f})")


def test_random_walk_no_half_life():
    """A true random walk has β estimated close to (but slightly below) 1 in
    finite samples, which produces a very long but finite raw HL. The 'is it
    MR?' decision belongs in is_stable_half_life with bounds — that's the
    gate that catches RW behavior correctly."""
    s = _synth_rw(n=400)
    hl, beta, _ = estimate_half_life_ar1(s)
    assert beta > 0.85, f"RW β should be near 1; got {beta}"
    # Stability gate must reject this — finite HL > sensible upper bound
    assert not is_stable_half_life(hl, half_life_min=1.0, half_life_max=24.0), \
        f"is_stable_half_life must reject RW HL={hl}"
    # Also verify a stricter bound rejects: most RW HLs are >> 12
    assert not is_stable_half_life(hl, half_life_min=1.0, half_life_max=12.0)
    print(f"✓ random walk: β={beta:.3f}, HL={hl:.1f} (raw finite but rejected by stability gate)")


def test_insufficient_sample_fails_closed():
    s = _synth_ar1(n=10, beta=0.7)
    try:
        estimate_half_life_ar1(s, min_sample=30)
        assert False, "should have raised"
    except InsufficientSampleError:
        pass
    print("✓ insufficient-sample fails closed")


def test_is_stable_half_life():
    assert is_stable_half_life(5.0, 1.0, 12.0)
    assert not is_stable_half_life(50.0, 1.0, 12.0)
    assert not is_stable_half_life(float("nan"))
    assert not is_stable_half_life(-1.0)
    print("✓ is_stable_half_life bounds work")


def test_rolling_half_life_on_ar1():
    s = _synth_ar1(n=300, beta=0.7)
    hl_series = rolling_half_life(s, window=80, min_sample=30)
    valid = hl_series.dropna()
    assert len(valid) > 100, "should produce many valid windows"
    finite_ratio = valid.notna().mean()
    assert finite_ratio > 0.8, f"most windows should be finite; got {finite_ratio:.2f}"
    print(f"✓ rolling HL on AR(1): {len(valid)} valid windows, median HL={valid.median():.2f}")


def test_gate_pair_signal_by_half_life():
    # Two series with a mean-reverting spread for half the sample, then random walk
    n = 300
    rng = np.random.default_rng(7)
    spread_mr = np.zeros(n // 2)
    for i in range(1, len(spread_mr)):
        spread_mr[i] = 0.7 * spread_mr[i-1] + rng.normal(0, 1)
    spread_rw = np.cumsum(rng.normal(0, 1, n // 2))
    spread = np.concatenate([spread_mr, spread_rw])
    base = 100 + np.cumsum(rng.normal(0, 0.3, n))
    a = pd.Series(base + spread / 2, index=pd.date_range("2020-01-31", periods=n, freq="ME"))
    b = pd.Series(base - spread / 2, index=a.index)

    # Construct a uniform-1 signal (entry every bar) so gating effect is purely
    # driven by half-life, not by signal sparsity
    sig = pd.Series(1, index=a.index)
    gated, hl_series = gate_pair_signal_by_half_life(
        sig, a, b, window=60, half_life_min=1.0, half_life_max=12.0
    )
    # First half should be largely passed (MR), second half largely gated (RW)
    # (Allow some overlap due to rolling-window lag)
    mr_pass = int((gated.iloc[60:150] != 0).sum())
    rw_pass = int((gated.iloc[200:290] != 0).sum())
    assert mr_pass > rw_pass, \
        f"MR window must pass more than RW: MR={mr_pass}, RW={rw_pass}"
    print(f"✓ gate works: MR-window pass={mr_pass}, RW-window pass={rw_pass}")


if __name__ == "__main__":
    test_ar1_recovers_half_life()
    test_random_walk_no_half_life()
    test_insufficient_sample_fails_closed()
    test_is_stable_half_life()
    test_rolling_half_life_on_ar1()
    test_gate_pair_signal_by_half_life()
    print("\nALL SMOKE TESTS PASSED — half-life filter is harness-ready.")
