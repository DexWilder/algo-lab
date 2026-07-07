"""Forge class-E gate: Deflated Sharpe Ratio + multiple-testing correction (López de Prado).

MANDATORY survivor gate (locked 2026-06-24): any sweep/screen survivor must clear DSR before being called
more than a screen pass. Corrects the observed Sharpe for (a) the NUMBER of trials run in the sweep and
(b) non-normality (skew/kurtosis). A survivor that can't beat its own sweep's multiple-testing-adjusted
benchmark is noise.

Pure numpy/math (no scipy): normal CDF via erf, inverse-normal via Acklam's approximation.
Usage:
    dsr = deflated_sharpe(returns_per_period, n_trials, sr_trials_std=None)
    -> {'sr','sr0_benchmark','dsr','passes'}  (passes = dsr >= 0.95)
"""
from __future__ import annotations

import math

import numpy as np

GAMMA = 0.5772156649015329  # Euler-Mascheroni


def _norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _norm_ppf(p):
    """Inverse normal CDF — Acklam's algorithm (accuracy ~1e-9)."""
    if p <= 0.0:
        return -math.inf
    if p >= 1.0:
        return math.inf
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02, 1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02, 6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00, -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    q = p - 0.5; r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)


def expected_max_sharpe(n_trials, sr_trials_std):
    """E[max SR] under null of N independent trials with Sharpe-dispersion sr_trials_std (per-period)."""
    if n_trials < 2 or sr_trials_std <= 0:
        return 0.0
    return sr_trials_std * ((1 - GAMMA) * _norm_ppf(1 - 1.0 / n_trials) + GAMMA * _norm_ppf(1 - 1.0 / (n_trials * math.e)))


def deflated_sharpe(returns, n_trials, sr_trials_std=None):
    """returns: per-period return array of the SELECTED (best) strategy. n_trials: # configs in the sweep.
    sr_trials_std: std of per-period Sharpe across all trials (deflation dispersion); if None, estimated
    conservatively from the selected strategy's own SR sampling (less ideal — pass it when available)."""
    r = np.asarray(returns, float); r = r[~np.isnan(r)]
    n = len(r)
    if n < 30:
        return {"sr": None, "dsr": None, "passes": False, "note": "n<30"}
    mu, sd = float(r.mean()), float(r.std(ddof=1))
    if sd == 0:
        return {"sr": None, "dsr": None, "passes": False, "note": "zero std"}
    sr = mu / sd                                    # per-period Sharpe
    g3 = float(((r - mu) ** 3).mean() / sd ** 3)    # skew
    g4 = float(((r - mu) ** 4).mean() / sd ** 4)    # kurtosis (normal=3)
    se_sr = math.sqrt(max(1e-12, (1 - g3 * sr + (g4 - 1) / 4 * sr ** 2) / (n - 1)))
    # FIX (2026-06-24): the old fallback (se_sr*sqrt(n-1)*0.5) mis-scales the deflation benchmark for
    # per-period/daily Sharpes -> spurious DSR~0 (bit L3 + VX-carry). Proper deflation REQUIRES the
    # cross-trial Sharpe dispersion. If not provided, do NOT fabricate a benchmark: report PSR (Probabilistic
    # Sharpe Ratio = P(true SR > 0)), and flag deflation as not-applied so callers know to pass sr_trials_std.
    deflated = sr_trials_std is not None
    sr0 = expected_max_sharpe(n_trials, sr_trials_std) if deflated else 0.0
    val = _norm_cdf((sr - sr0) / se_sr)   # deflated => DSR; else => PSR(>0)
    label = "dsr" if deflated else "psr"
    passes = val >= 0.95
    return {"sr_per_period": round(sr, 4), "sr_annualized_252": round(sr * math.sqrt(252), 3),
            "skew": round(g3, 3), "kurtosis": round(g4, 3), "se_sr": round(se_sr, 5),
            "n_trials": int(n_trials), "sr0_benchmark": round(sr0, 4), "deflation_applied": deflated,
            label: round(val, 4), "dsr": round(val, 4), "passes": bool(passes),
            "verdict": (("DSR_PASS" if deflated else "PSR_PASS_SR>0_significant") if passes else
                        ("DSR_MARGINAL" if val >= 0.90 else ("DSR_FAIL_likely_overfit" if deflated else "PSR_FAIL_SR_not_sig"))),
            "note": None if deflated else "PSR only (no trial dispersion passed); pass sr_trials_std (std of Sharpe across sweep trials) for true multiple-testing deflation"}


def dsr_verdict(returns, n_trials, sr_trials_std=0.05):
    """CANONICAL DSR GATE — ALWAYS deflates (defaults sr_trials_std=0.05). Use THIS, never the raw deflated_sharpe
    without sr_trials_std, so a PSR can never be misread as a DSR pass (M53 gap trap, 2026-07-07). Returns the full
    dict with deflation_applied=True guaranteed. sr_trials_std=0.05 is the conservative default cross-trial Sharpe
    dispersion for daily per-period returns; pass a measured value when the sweep provides one."""
    res = deflated_sharpe(returns, n_trials, sr_trials_std=sr_trials_std)
    if res.get("deflation_applied") is not True and res.get("dsr") is not None:
        res["_WARN"] = "deflation unexpectedly not applied — treat as PSR, do NOT call a pass"
    return res


if __name__ == "__main__":
    rng = np.random.default_rng(42)
    # self-test: a genuinely good strategy (SR~1.5 ann) selected from 50 trials
    good = rng.normal(0.0006, 0.006, 1500)          # ~1.6 ann Sharpe
    print("strong single strategy, 50 trials:", deflated_sharpe(good, 50, sr_trials_std=0.02))
    # noise strategy that happens to look good, selected from 200 trials
    noise = rng.normal(0.00015, 0.006, 1500)        # ~0.4 ann Sharpe but best-of-200
    print("weak best-of-200:", deflated_sharpe(noise, 200, sr_trials_std=0.03))
    print("(class-E gate installed; apply to every sweep survivor)")
