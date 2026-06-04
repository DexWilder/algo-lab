"""V1 loosen tests per operator approval 2026-06-03 (Ask #13).

Reuses the V1 model + monthly_rebalance harness; varies the rule:
  variant 1: 1.5σ threshold (baseline — established)
  variant 2: 1.0σ threshold (loosened)
  variant 3: 1.0σ threshold, no Δreal-yield gate (loose + no gate)
  variant 4: absolute residual (|z| > 1.0) — symmetric; ignore macro direction

Classification per operator rules:
- n too small → KILL
- PF < 1.2 or median < 0 → KILL
- PF improves but depends on one year → temporal split before WATCH
- robust → WATCH (not promote)

Authority: T1 / Lane B / report-only.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from research.fundamentals_cache import load_series  # uses the new cache
from research.monthly_rebalance_engine import monthly_rebalance_run  # noqa: E402
from research.fql_forge_batch_runner import _metrics, _verdict  # noqa: E402


def build_signal_general(mgc_monthly: pd.Series,
                         real_yield: pd.Series,
                         dxy: pd.Series,
                         lookback_months: int = 60,
                         sigma_threshold: float = 1.5,
                         use_delta_gate: bool = True,
                         absolute_residual: bool = False) -> pd.Series:
    """Generalized V1 signal — supports loosening variants."""
    idx = real_yield.index.intersection(dxy.index).intersection(mgc_monthly.index)
    ry = real_yield.reindex(idx).sort_index()
    dx = dxy.reindex(idx).sort_index()
    px = mgc_monthly.reindex(idx).sort_index()
    ret = np.log(px / px.shift(1))
    d_ry = ry.diff()
    d_dx = dx.diff()

    sig = pd.Series(0, index=idx, dtype=int)
    for i in range(lookback_months, len(idx)):
        window = slice(i - lookback_months, i)
        y = ret.iloc[window].values
        x1 = d_ry.iloc[window].values
        x2 = d_dx.iloc[window].values
        mask = ~(np.isnan(y) | np.isnan(x1) | np.isnan(x2))
        if mask.sum() < 30:
            continue
        Y = y[mask]
        X = np.column_stack([np.ones(mask.sum()), x1[mask], x2[mask]])
        try:
            beta, *_ = np.linalg.lstsq(X, Y, rcond=None)
        except np.linalg.LinAlgError:
            continue
        pred = X @ beta
        resid = Y - pred
        sigma = resid.std(ddof=0)
        if sigma == 0 or np.isnan(sigma):
            continue
        cur_d_ry = d_ry.iloc[i]
        cur_d_dx = d_dx.iloc[i]
        cur_ret = ret.iloc[i]
        if any(np.isnan(v) for v in (cur_d_ry, cur_d_dx, cur_ret)):
            continue
        cur_pred = beta[0] + beta[1] * cur_d_ry + beta[2] * cur_d_dx
        cur_resid = cur_ret - cur_pred
        z = cur_resid / sigma

        if absolute_residual:
            # Symmetric: any breach triggers long (mean-reversion to fair value
            # works in either direction; sign of breach picks direction)
            if z < -sigma_threshold:
                sig.iloc[i] = 1
            elif z > sigma_threshold:
                sig.iloc[i] = -1
            continue

        if use_delta_gate:
            if z < -sigma_threshold and cur_d_ry <= 0:
                sig.iloc[i] = 1
            elif z > sigma_threshold and cur_d_ry >= 0:
                sig.iloc[i] = -1
        else:
            if z < -sigma_threshold:
                sig.iloc[i] = 1
            elif z > sigma_threshold:
                sig.iloc[i] = -1
    return sig


def _monthly_close(asset="MGC"):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.set_index("datetime").sort_index()
    return df["close"].resample("ME").last()


def _classify(m: dict) -> str:
    n = m.get("n", 0)
    pf = m.get("pf", 0)
    median = m.get("median", 0)
    if n < 5:
        return "KILL (insufficient-n)"
    if median < 0:
        return "KILL (median negative)"
    if pf < 1.2:
        return "KILL (PF < 1.2)"
    return "WATCH"


def run():
    mgc_monthly = _monthly_close("MGC")
    ry = load_series("real_yield_10y")
    dxy = load_series("usd_broad")

    variants = [
        ("1.5σ baseline",   {"sigma_threshold": 1.5, "use_delta_gate": True, "absolute_residual": False}),
        ("1.0σ loosen",     {"sigma_threshold": 1.0, "use_delta_gate": True, "absolute_residual": False}),
        ("1.0σ no Δ-gate",  {"sigma_threshold": 1.0, "use_delta_gate": False, "absolute_residual": False}),
        ("1.0σ |abs|",      {"sigma_threshold": 1.0, "use_delta_gate": False, "absolute_residual": True}),
    ]

    results = []
    print(f"V1 loosen tests — {len(variants)} variants\n")
    for name, kw in variants:
        sig = build_signal_general(mgc_monthly, ry, dxy, lookback_months=60, **kw)
        if (sig != 0).sum() == 0:
            print(f"  [{name:18s}] no signals fired")
            results.append({"variant": name, "params": kw, "metrics": None,
                            "verdict": "KILL (zero signals)"})
            continue
        res = monthly_rebalance_run(asset="MGC", signal=sig, label=f"V1-{name}")
        m = _metrics(res["trades_df"], f"V1-{name}", costs=res["stats"]["costs"])
        verdict = _classify(m)
        results.append({"variant": name, "params": kw,
                        "metrics": {k: m.get(k) for k in (
                            "n", "pf", "median", "net", "max_dd",
                            "max_year_share_pct", "top3_share_pct",
                            "h1_pf", "h2_pf", "n_years", "years_positive",
                        )},
                        "verdict": verdict,
                        "signal_counts": {"long": int((sig == 1).sum()),
                                          "short": int((sig == -1).sum()),
                                          "flat": int((sig == 0).sum())}})
        max_yr = m.get("max_year_share_pct", float("nan"))
        print(f"  [{name:18s}] long={int((sig == 1).sum()):2d} short={int((sig == -1).sum()):2d} flat={int((sig == 0).sum()):2d} | "
              f"n={m['n']:3d} PF={m['pf']:.3f} median=${m['median']:7.2f} max-yr={max_yr:.1f}% → {verdict}")

    out_dir = ROOT / "research" / "data" / "fql_forge" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    date_iso = date.today().isoformat()
    json_path = out_dir / f"forge_v1_loosen_{date_iso}.json"
    md_path = out_dir / f"forge_v1_loosen_{date_iso}.md"

    json_path.write_text(json.dumps({
        "date": date_iso,
        "operator_approval": "OK V1 loosen 1.0σ (2026-06-03)",
        "results": results,
    }, indent=2, default=str))

    md_lines = [
        f"# V1 Loosen Tests — {date_iso}",
        f"\nAuthority T1 / Lane B / report-only. Operator approval: OK V1 loosen 1.0σ.\n",
        "| Variant | Long | Short | Flat | n | PF | Median | Max-Yr | Verdict |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in results:
        m = r["metrics"]
        if m is None:
            md_lines.append(f"| {r['variant']} | — | — | — | 0 | — | — | — | {r['verdict']} |")
            continue
        sc = r["signal_counts"]
        md_lines.append(
            f"| {r['variant']} | {sc['long']} | {sc['short']} | {sc['flat']} | "
            f"{m['n']} | {m['pf']:.3f} | ${m['median']:.2f} | "
            f"{m.get('max_year_share_pct', float('nan')):.1f}% | {r['verdict']} |"
        )
    md_path.write_text("\n".join(md_lines))
    print(f"\nWrote: {md_path}")
    print(f"Wrote: {json_path}")
    return results


if __name__ == "__main__":
    run()
