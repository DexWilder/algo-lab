"""FQL Forge — Half-Life Filter (v1)

Discriminating filter for pairs / MR candidates: estimates the rolling half-life
of a series (or a spread series) via AR(1) regression and returns both the
half-life estimate and a pass/fail flag based on configurable bounds.

Use cases:
  - Pairs gate: only fire pair signals when the spread is statistically
    mean-reverting in the current window (half-life finite + within bounds).
  - MR candidate gate: only allow MR entries when the underlying series is
    currently in an MR regime.

Math (v1 — minimum viable):
  - AR(1): x_t = α + β * x_{t-1} + ε
  - Half-life = -ln(2) / ln(β)  if 0 < β < 1
  - β ≥ 1 → not mean-reverting → no half-life
  - β ≤ 0 → AR(1) doesn't apply → no half-life
  - Stable flag: 0 < β < 1 AND half_life_min ≤ HL ≤ half_life_max

Authority: T1 / Lane B / report-only. No registry mutation.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class InsufficientSampleError(ValueError):
    """Raised when input sample is too small to estimate AR(1)."""


def estimate_half_life_ar1(series: pd.Series,
                            min_sample: int = 30) -> tuple[float, float, dict]:
    """Estimate AR(1) half-life on a single series.

    Returns
    -------
    (half_life, beta, diagnostics)
      - half_life: estimated half-life in periods, or np.nan if not finite / MR
      - beta: AR(1) coefficient
      - diagnostics: dict with n, residual std, t-stat (rough)
    """
    s = pd.Series(series).dropna()
    if len(s) < min_sample:
        raise InsufficientSampleError(
            f"AR(1) needs >= {min_sample} obs; got {len(s)}"
        )
    y = s.iloc[1:].values
    x = s.iloc[:-1].values
    # OLS: y = alpha + beta * x
    X = np.column_stack([np.ones(len(x)), x])
    beta_hat, *_ = np.linalg.lstsq(X, y, rcond=None)
    alpha, beta = float(beta_hat[0]), float(beta_hat[1])
    resid = y - (alpha + beta * x)
    resid_std = float(resid.std(ddof=2))
    # Half-life only defined for 0 < beta < 1
    if 0.0 < beta < 1.0:
        half_life = -np.log(2.0) / np.log(beta)
    else:
        half_life = float("nan")
    # Rough t-stat for beta (assume X.T @ X close to diagonal w/o checks)
    try:
        XtX_inv = np.linalg.inv(X.T @ X)
        se_beta = float(np.sqrt(XtX_inv[1, 1]) * resid_std)
        t_beta = (beta - 1.0) / se_beta if se_beta > 0 else float("nan")
    except Exception:
        se_beta = float("nan")
        t_beta = float("nan")
    return half_life, beta, {
        "n": int(len(s)), "alpha": alpha, "resid_std": resid_std,
        "se_beta": se_beta, "t_beta_minus_1": t_beta,
    }


def estimate_half_life_spread(series_a: pd.Series, series_b: pd.Series,
                               min_sample: int = 30) -> tuple[float, float, dict]:
    """Half-life of the (A − B) level spread."""
    idx = series_a.index.intersection(series_b.index)
    a = pd.Series(series_a).reindex(idx).sort_index()
    b = pd.Series(series_b).reindex(idx).sort_index()
    return estimate_half_life_ar1(a - b, min_sample=min_sample)


def is_stable_half_life(half_life: float,
                        half_life_min: float = 1.0,
                        half_life_max: float = 24.0) -> bool:
    """Check whether the estimated half-life is in the 'stable MR' band.
    Defaults (1–24 periods) match monthly spread expectations; tune via params."""
    if half_life is None or not np.isfinite(half_life):
        return False
    return half_life_min <= half_life <= half_life_max


def rolling_half_life(series: pd.Series, window: int = 60,
                      min_sample: int = 30) -> pd.Series:
    """Rolling half-life estimate (one value per bar, NaN for bars in warmup)."""
    s = pd.Series(series)
    out = pd.Series(np.nan, index=s.index)
    for i in range(window, len(s)):
        sub = s.iloc[i - window:i]
        try:
            hl, _, _ = estimate_half_life_ar1(sub, min_sample=min_sample)
            out.iloc[i] = hl
        except InsufficientSampleError:
            continue
    return out


# ─────────────────────────────────────────────────────────────────────────────
# pairs_engine integration helpers
# ─────────────────────────────────────────────────────────────────────────────

def gate_pair_signal_by_half_life(
    sig: pd.Series,
    series_a: pd.Series,
    series_b: pd.Series,
    window: int = 60,
    half_life_min: float = 1.0,
    half_life_max: float = 24.0,
    min_sample: int = 30,
) -> tuple[pd.Series, pd.Series]:
    """Zero out signals on bars where rolling spread half-life is not in band.

    Returns
    -------
    (gated_signal, hl_series): the filtered signal aligned to `sig.index`,
    and the rolling half-life series (for reporting).
    """
    idx = series_a.index.intersection(series_b.index)
    a = pd.Series(series_a).reindex(idx).sort_index()
    b = pd.Series(series_b).reindex(idx).sort_index()
    spread = a - b
    hl = rolling_half_life(spread, window=window, min_sample=min_sample)
    hl_aligned = hl.reindex(sig.index)
    stable = hl_aligned.apply(lambda v: is_stable_half_life(v, half_life_min, half_life_max))
    gated = sig.where(stable, 0).fillna(0).astype(int)
    return gated, hl_aligned
