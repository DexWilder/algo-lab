"""Statistical validation tools — bootstrap CIs and Deflated Sharpe Ratio.

Provides confidence intervals for backtest metrics and corrects for
multiple testing bias using López de Prado's Deflated Sharpe Ratio.
"""

import math
import numpy as np
import pandas as pd


# ── Pure-numpy normal CDF (no scipy dependency) ──────────────────────────────

def _norm_cdf(x):
    """Standard normal CDF using the error function from math module."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


# ── Bootstrap Confidence Intervals ────────────────────────────────────────────

def bootstrap_metrics(
    trades_pnl: np.ndarray,
    n_resamples: int = 10_000,
    confidence: float = 0.95,
    starting_capital: float = 50_000.0,
    seed: int = 42,
) -> dict:
    """Bootstrap confidence intervals for PF, Sharpe, and MaxDD.

    Parameters
    ----------
    trades_pnl : array-like
        Array of per-trade PnL values.
    n_resamples : int
        Number of bootstrap resamples (default 10,000).
    confidence : float
        Confidence level (default 0.95 for 95% CI).
    starting_capital : float
        Starting capital for drawdown calculation.
    seed : int
        Random seed for reproducibility.

    Returns
    -------
    dict with keys: pf, sharpe, max_dd — each containing
        {mean, median, ci_low, ci_high, point_estimate}.
    """
    pnl = np.asarray(trades_pnl, dtype=float)
    n_trades = len(pnl)

    if n_trades < 5:
        return _empty_bootstrap()

    rng = np.random.default_rng(seed)
    alpha = (1 - confidence) / 2

    pf_samples = np.empty(n_resamples)
    sharpe_samples = np.empty(n_resamples)
    maxdd_samples = np.empty(n_resamples)

    for i in range(n_resamples):
        sample = rng.choice(pnl, size=n_trades, replace=True)
        pf_samples[i] = _calc_pf(sample)
        sharpe_samples[i] = _calc_trade_sharpe(sample)
        maxdd_samples[i] = _calc_maxdd(sample, starting_capital)

    def _summarize(samples, point_est):
        finite = samples[np.isfinite(samples)]
        if len(finite) == 0:
            return {"mean": 0, "median": 0, "ci_low": 0, "ci_high": 0,
                    "point_estimate": point_est}
        return {
            "mean": round(float(np.mean(finite)), 4),
            "median": round(float(np.median(finite)), 4),
            "ci_low": round(float(np.percentile(finite, alpha * 100)), 4),
            "ci_high": round(float(np.percentile(finite, (1 - alpha) * 100)), 4),
            "point_estimate": round(float(point_est), 4),
        }

    return {
        "pf": _summarize(pf_samples, _calc_pf(pnl)),
        "sharpe": _summarize(sharpe_samples, _calc_trade_sharpe(pnl)),
        "max_dd": _summarize(maxdd_samples, _calc_maxdd(pnl, starting_capital)),
        "n_trades": n_trades,
        "n_resamples": n_resamples,
        "confidence": confidence,
    }


def _calc_pf(pnl):
    """Profit factor from PnL array."""
    wins = pnl[pnl > 0].sum()
    losses = abs(pnl[pnl < 0].sum())
    if losses == 0:
        return 100.0 if wins > 0 else 0.0
    return wins / losses


def _calc_trade_sharpe(pnl):
    """Sharpe-like ratio from trade PnL (mean/std * sqrt(252/avg_trades_year))."""
    if len(pnl) < 2 or pnl.std() == 0:
        return 0.0
    # Approximate annualization: assume ~1 trade/day for scaling
    return float(pnl.mean() / pnl.std() * np.sqrt(252))


def _calc_maxdd(pnl, starting_capital):
    """Max drawdown from trade sequence."""
    equity = starting_capital + np.cumsum(pnl)
    peak = np.maximum.accumulate(equity)
    dd = peak - equity
    return float(dd.max())


def _empty_bootstrap():
    empty = {"mean": 0, "median": 0, "ci_low": 0, "ci_high": 0, "point_estimate": 0}
    return {"pf": empty.copy(), "sharpe": empty.copy(), "max_dd": empty.copy(),
            "n_trades": 0, "n_resamples": 0, "confidence": 0}


# ── Deflated Sharpe Ratio ─────────────────────────────────────────────────────
#
# Reference: Bailey & López de Prado (2014)
# "The Deflated Sharpe Ratio: Correcting for Selection Bias,
#  Backtest Overfitting, and Non-Normality"
#
# DSR answers: "Given that I tested N strategy variations, what's the
# probability that the best Sharpe I found is genuinely > 0?"

def deflated_sharpe_ratio(
    observed_sharpe: float,
    n_trials: int,
    n_observations: int,
    sharpe_std: float = None,
    skewness: float = 0.0,
    kurtosis: float = 3.0,
    returns: np.ndarray = None,
) -> dict:
    """Compute the Deflated Sharpe Ratio.

    Parameters
    ----------
    observed_sharpe : float
        The best observed Sharpe ratio (annualized).
    n_trials : int
        Number of independent strategy/parameter combinations tested.
        This is the key multiple-testing correction.
    n_observations : int
        Number of return observations (e.g., trading days).
    sharpe_std : float, optional
        Standard deviation of Sharpe ratios across trials.
        If None, estimated from expected max under i.i.d. assumption.
    skewness : float, optional
        Skewness of returns (default 0 = normal).
    kurtosis : float, optional
        Kurtosis of returns (default 3 = normal).
    returns : array-like, optional
        If provided, skewness and kurtosis are computed from the data.

    Returns
    -------
    dict with keys:
        dsr: float — probability that true Sharpe > 0 after correction (0-1)
        expected_max_sharpe: float — expected max Sharpe under null
        observed_sharpe: float
        n_trials: int
        significant: bool — True if DSR > 0.95 (strategy likely real)
    """
    if returns is not None:
        returns = np.asarray(returns, dtype=float)
        n_r = len(returns)
        if n_r > 2:
            m = returns.mean()
            s = returns.std(ddof=1)
            if s > 0:
                skewness = float(np.mean(((returns - m) / s) ** 3))
                kurtosis = float(np.mean(((returns - m) / s) ** 4))  # raw kurtosis
            else:
                skewness, kurtosis = 0.0, 3.0
        else:
            skewness, kurtosis = 0.0, 3.0

    # Expected maximum Sharpe ratio under i.i.d. null hypothesis
    # E[max(Z_1,...,Z_N)] ≈ (1 - γ) * Φ^{-1}(1 - 1/N) + γ * Φ^{-1}(1 - 1/(N*e))
    # Simplified approximation using Euler-Mascheroni constant
    if n_trials <= 1:
        expected_max_sr = 0.0
    else:
        expected_max_sr = _expected_max_sharpe(n_trials, n_observations)

    if sharpe_std is None:
        sharpe_std = max(expected_max_sr * 0.5, 0.1)

    # SR* adjusted for non-normality (Pézier & White 2006)
    sr_adjusted = observed_sharpe * _non_normality_adjustment(
        observed_sharpe, skewness, kurtosis, n_observations
    )

    # PSR: Probabilistic Sharpe Ratio
    # P[SR > SR_benchmark] using the standard error of the Sharpe ratio
    se_sr = _sharpe_standard_error(observed_sharpe, skewness, kurtosis, n_observations)

    if se_sr > 0:
        # Test against expected max (the benchmark under null)
        z_score = (sr_adjusted - expected_max_sr) / se_sr
        dsr = float(_norm_cdf(z_score))
    else:
        dsr = 0.5

    return {
        "dsr": round(dsr, 4),
        "expected_max_sharpe": round(expected_max_sr, 4),
        "observed_sharpe": round(observed_sharpe, 4),
        "n_trials": n_trials,
        "n_observations": n_observations,
        "skewness": round(skewness, 4),
        "kurtosis": round(kurtosis, 4),
        "sharpe_se": round(se_sr, 4),
        "significant": dsr > 0.95,
    }


def _expected_max_sharpe(n_trials, n_obs):
    """Expected max Sharpe under null (all strategies have zero true Sharpe).

    Uses the approximation: E[max] ≈ √(2 * ln(N)) - (ln(π) + ln(ln(N))) / (2 * √(2 * ln(N)))
    from extreme value theory for i.i.d. standard normals.
    """
    if n_trials <= 1:
        return 0.0
    log_n = np.log(n_trials)
    z = np.sqrt(2 * log_n)
    euler_correction = (np.log(np.pi) + np.log(log_n)) / (2 * z)
    # Scale to annualized: the formula gives standard normal units
    # For Sharpe, we need to account for observation count
    return z - euler_correction


def _non_normality_adjustment(sr, skew, kurt, n):
    """Adjustment factor for non-normal returns (Pézier & White 2006)."""
    # When returns are normal (skew=0, kurt=3), this returns 1.0
    adjustment = 1 - skew * sr / 6 + (kurt - 3) * sr**2 / 24
    return max(adjustment, 0.1)  # floor to prevent sign flip


def _sharpe_standard_error(sr, skew, kurt, n):
    """Standard error of the Sharpe ratio accounting for non-normality.

    From Lo (2002) and Bailey & López de Prado (2014):
    SE(SR) = sqrt((1 - γ₃·SR + (γ₄-1)/4·SR²) / n)
    where γ₃ = skewness, γ₄ = kurtosis
    """
    if n <= 1:
        return 0.0
    variance = (1 - skew * sr + (kurt - 1) / 4 * sr**2) / n
    return np.sqrt(max(variance, 0))


# ── Convenience: run full statistical report on a trade list ──────────────────

def full_statistical_report(
    trades_pnl: np.ndarray,
    n_trials: int = 1,
    daily_pnl: np.ndarray = None,
    n_resamples: int = 10_000,
    starting_capital: float = 50_000.0,
) -> dict:
    """Run bootstrap CIs + DSR on a set of trades.

    Parameters
    ----------
    trades_pnl : array-like
        Per-trade PnL values.
    n_trials : int
        Number of strategy/param combos tested (for DSR correction).
    daily_pnl : array-like, optional
        Daily aggregated PnL for Sharpe calculation. If None, uses trade PnL.
    n_resamples : int
        Bootstrap resamples.
    starting_capital : float
        For drawdown calculation.

    Returns
    -------
    dict with 'bootstrap' and 'dsr' keys.
    """
    pnl = np.asarray(trades_pnl, dtype=float)

    # Bootstrap
    boot = bootstrap_metrics(pnl, n_resamples=n_resamples,
                             starting_capital=starting_capital)

    # DSR
    if daily_pnl is not None:
        daily = np.asarray(daily_pnl, dtype=float)
    else:
        daily = pnl

    n_obs = len(daily)
    if n_obs > 1 and daily.std() > 0:
        observed_sharpe = float(daily.mean() / daily.std() * np.sqrt(252))
    else:
        observed_sharpe = 0.0

    dsr = deflated_sharpe_ratio(
        observed_sharpe=observed_sharpe,
        n_trials=n_trials,
        n_observations=n_obs,
        returns=daily,
    )

    return {"bootstrap": boot, "dsr": dsr}
