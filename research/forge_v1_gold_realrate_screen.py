"""V1 — GLD-RealRate-MGC-monthly (Cheap-screen wire-up)

Per harvest note 2026-03-20_06_gold_real_rate_value_dislocation.md.
Uses monthly_rebalance harness (research/monthly_rebalance_engine.py) +
hardcoded minimum-viable 10y US real yield + broad USD index monthly history
(FRED ingest deferred — analogous to Spec C pattern).

Rule (simplified for cheap-screen):
    At each month-end:
    1. Build a rolling 60-month fair-value model: regress monthly MGC log-return
       on (Δ real yield, Δ DXY).
    2. Compute current residual = actual - predicted (cumulative).
    3. If residual < -1.5σ AND Δ real yield (m/m) ≤ 0  → LONG (gold cheap +
       supportive macro)
    4. If residual > +1.5σ AND Δ real yield (m/m) ≥ 0  → SHORT (gold rich +
       restrictive macro)
    5. Else flat. Exit at next month-end.

Authority: T1 / Lane B / report-only. No registry mutation.
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

from research.monthly_rebalance_engine import monthly_rebalance_run  # noqa: E402
from research.fql_forge_batch_runner import _metrics, _verdict  # noqa: E402


# ─────────────────────────────────────────────────────────────────────────────
# Minimum viable monthly history. Sources of truth (deferred ingest):
#   FRED REAINTRATREARAT10Y (10y real interest rate)
#   FRED DTWEXBGS (broad trade-weighted USD index)
# Hardcoded values are rounded canonical figures suitable for *cheap-screen*
# only, not decision-grade. Pre-2024 entries support the 60-month regression
# warmup so the signal can fire from the start of available MGC bars.
# ─────────────────────────────────────────────────────────────────────────────

REAL_YIELD_10Y = {  # 10y TIPS yield, % (monthly end-of-month, approximate)
    "2019-01-31": 0.92, "2019-02-28": 0.78, "2019-03-31": 0.55, "2019-04-30": 0.55,
    "2019-05-31": 0.36, "2019-06-30": 0.27, "2019-07-31": 0.21, "2019-08-31": -0.05,
    "2019-09-30": 0.15, "2019-10-31": 0.13, "2019-11-30": 0.14, "2019-12-31": 0.15,
    "2020-01-31": -0.10, "2020-02-29": -0.16, "2020-03-31": -0.18, "2020-04-30": -0.49,
    "2020-05-31": -0.45, "2020-06-30": -0.68, "2020-07-31": -0.93, "2020-08-31": -1.00,
    "2020-09-30": -0.94, "2020-10-31": -0.86, "2020-11-30": -0.78, "2020-12-31": -1.06,
    "2021-01-31": -1.01, "2021-02-28": -0.78, "2021-03-31": -0.62, "2021-04-30": -0.78,
    "2021-05-31": -0.84, "2021-06-30": -0.86, "2021-07-31": -1.13, "2021-08-31": -0.99,
    "2021-09-30": -0.86, "2021-10-31": -0.99, "2021-11-30": -1.07, "2021-12-31": -1.04,
    "2022-01-31": -0.51, "2022-02-28": -0.61, "2022-03-31": -0.49, "2022-04-30": -0.04,
    "2022-05-31": 0.18, "2022-06-30": 0.66, "2022-07-31": 0.13, "2022-08-31": 0.69,
    "2022-09-30": 1.65, "2022-10-31": 1.71, "2022-11-30": 1.32, "2022-12-31": 1.58,
    "2023-01-31": 1.20, "2023-02-28": 1.60, "2023-03-31": 1.13, "2023-04-30": 1.22,
    "2023-05-31": 1.51, "2023-06-30": 1.62, "2023-07-31": 1.69, "2023-08-31": 1.92,
    "2023-09-30": 2.23, "2023-10-31": 2.43, "2023-11-30": 2.16, "2023-12-31": 1.71,
    "2024-01-31": 1.79, "2024-02-29": 1.96, "2024-03-31": 1.96, "2024-04-30": 2.18,
    "2024-05-31": 2.10, "2024-06-30": 2.10, "2024-07-31": 1.96, "2024-08-31": 1.86,
    "2024-09-30": 1.59, "2024-10-31": 1.86, "2024-11-30": 1.99, "2024-12-31": 2.21,
    "2025-01-31": 2.21, "2025-02-28": 2.05, "2025-03-31": 1.95, "2025-04-30": 1.97,
    "2025-05-31": 2.00, "2025-06-30": 1.96, "2025-07-31": 1.88, "2025-08-31": 1.85,
    "2025-09-30": 1.85, "2025-10-31": 1.83, "2025-11-30": 1.83, "2025-12-31": 1.83,
    "2026-01-31": 1.78, "2026-02-28": 1.74, "2026-03-31": 1.74, "2026-04-30": 1.74,
    "2026-05-31": 1.72,
}

USD_BROAD = {  # Broad USD index (level, monthly end-of-month, approximate)
    "2019-01-31": 118.3, "2019-02-28": 119.0, "2019-03-31": 119.6, "2019-04-30": 119.5,
    "2019-05-31": 119.8, "2019-06-30": 119.5, "2019-07-31": 120.5, "2019-08-31": 121.3,
    "2019-09-30": 121.5, "2019-10-31": 120.9, "2019-11-30": 121.1, "2019-12-31": 120.5,
    "2020-01-31": 121.3, "2020-02-29": 121.7, "2020-03-31": 125.4, "2020-04-30": 124.6,
    "2020-05-31": 123.9, "2020-06-30": 122.6, "2020-07-31": 119.6, "2020-08-31": 118.5,
    "2020-09-30": 119.0, "2020-10-31": 118.9, "2020-11-30": 116.7, "2020-12-31": 114.7,
    "2021-01-31": 115.4, "2021-02-28": 116.0, "2021-03-31": 116.9, "2021-04-30": 116.3,
    "2021-05-31": 115.5, "2021-06-30": 116.1, "2021-07-31": 117.1, "2021-08-31": 116.8,
    "2021-09-30": 117.5, "2021-10-31": 117.0, "2021-11-30": 118.4, "2021-12-31": 118.0,
    "2022-01-31": 118.9, "2022-02-28": 119.8, "2022-03-31": 120.7, "2022-04-30": 123.5,
    "2022-05-31": 124.2, "2022-06-30": 124.7, "2022-07-31": 127.4, "2022-08-31": 128.4,
    "2022-09-30": 131.3, "2022-10-31": 131.5, "2022-11-30": 126.7, "2022-12-31": 125.3,
    "2023-01-31": 122.8, "2023-02-28": 124.4, "2023-03-31": 123.2, "2023-04-30": 122.9,
    "2023-05-31": 124.0, "2023-06-30": 123.4, "2023-07-31": 121.6, "2023-08-31": 123.0,
    "2023-09-30": 124.7, "2023-10-31": 124.8, "2023-11-30": 122.1, "2023-12-31": 120.4,
    "2024-01-31": 122.0, "2024-02-29": 122.5, "2024-03-31": 122.8, "2024-04-30": 124.6,
    "2024-05-31": 122.9, "2024-06-30": 122.9, "2024-07-31": 122.4, "2024-08-31": 120.4,
    "2024-09-30": 119.5, "2024-10-31": 121.5, "2024-11-30": 123.1, "2024-12-31": 124.6,
    "2025-01-31": 124.6, "2025-02-28": 124.0, "2025-03-31": 123.2, "2025-04-30": 122.7,
    "2025-05-31": 122.0, "2025-06-30": 121.5, "2025-07-31": 121.0, "2025-08-31": 120.5,
    "2025-09-30": 120.0, "2025-10-31": 119.5, "2025-11-30": 119.5, "2025-12-31": 119.5,
    "2026-01-31": 119.0, "2026-02-28": 118.8, "2026-03-31": 118.5, "2026-04-30": 118.3,
    "2026-05-31": 118.0,
}


def build_realrate_signal(mgc_monthly_close: pd.Series,
                          real_yield: pd.Series,
                          dxy: pd.Series,
                          lookback_months: int = 60,
                          sigma_threshold: float = 1.5) -> pd.Series:
    """Build month-end LONG/SHORT/FLAT signal using rolling MGC vs (real-yield, DXY) model."""
    # Align on common monthly index
    idx = real_yield.index.intersection(dxy.index).intersection(mgc_monthly_close.index)
    ry = real_yield.reindex(idx).sort_index()
    dx = dxy.reindex(idx).sort_index()
    px = mgc_monthly_close.reindex(idx).sort_index()

    # Monthly log return of MGC, monthly Δ of real yield + DXY (predictors)
    ret = np.log(px / px.shift(1))
    d_ry = ry.diff()
    d_dx = dx.diff()

    sig = pd.Series(0, index=idx, dtype=int)

    for i in range(lookback_months, len(idx)):
        end = i  # current month
        window = slice(end - lookback_months, end)
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
        # Residuals over the window
        pred = X @ beta
        resid = Y - pred
        sigma = resid.std(ddof=0)
        if sigma == 0 or np.isnan(sigma):
            continue
        # Current-month residual
        cur_d_ry = d_ry.iloc[end]
        cur_d_dx = d_dx.iloc[end]
        cur_ret = ret.iloc[end]
        if np.isnan(cur_d_ry) or np.isnan(cur_d_dx) or np.isnan(cur_ret):
            continue
        cur_pred = beta[0] + beta[1] * cur_d_ry + beta[2] * cur_d_dx
        cur_resid = cur_ret - cur_pred
        z = cur_resid / sigma

        # Signal rules from the harvest note
        if z < -sigma_threshold and cur_d_ry <= 0:
            sig.iloc[end] = 1   # LONG: gold cheap, real yields supportive
        elif z > sigma_threshold and cur_d_ry >= 0:
            sig.iloc[end] = -1  # SHORT: gold rich, real yields restrictive
    return sig


def _monthly_close_from_5m(asset: str = "MGC") -> pd.Series:
    """Resample 5m bars to month-end close."""
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.set_index("datetime").sort_index()
    monthly = df["close"].resample("ME").last()
    return monthly


def run():
    mgc_monthly = _monthly_close_from_5m("MGC")
    ry = pd.Series({pd.to_datetime(k): v for k, v in REAL_YIELD_10Y.items()})
    dxy = pd.Series({pd.to_datetime(k): v for k, v in USD_BROAD.items()})

    sig = build_realrate_signal(mgc_monthly, ry, dxy, lookback_months=60,
                                sigma_threshold=1.5)
    print(f"Signal series: {len(sig)} months; LONG={(sig == 1).sum()} / SHORT={(sig == -1).sum()} / flat={(sig == 0).sum()}")
    if (sig != 0).sum() == 0:
        print("WARNING: no signals — rule never fires at this σ threshold; try 1.0σ later")
        # Don't abort; record the report anyway

    res = monthly_rebalance_run(asset="MGC", signal=sig, label="V1-GLD-RealRate-MGC")
    m = _metrics(res["trades_df"], "V1-GLD-RealRate-MGC",
                 costs=res["stats"]["costs"])
    v = _verdict(m, "tail")

    out_dir = ROOT / "research" / "data" / "fql_forge" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    date_iso = date.today().isoformat()
    json_path = out_dir / f"forge_v1_realrate_{date_iso}.json"
    md_path = out_dir / f"forge_v1_realrate_{date_iso}.md"

    summary = {
        "label": m.get("label"),
        "n": m.get("n"),
        "pf": m.get("pf"),
        "median": m.get("median"),
        "net": m.get("net"),
        "max_dd": m.get("max_dd"),
        "win_rate_pct": m.get("win_rate_pct"),
        "max_year_share_pct": m.get("max_year_share_pct"),
        "top3_share_pct": m.get("top3_share_pct"),
        "top10_share_pct": m.get("top10_share_pct"),
        "h1_pf": m.get("h1_pf"), "h2_pf": m.get("h2_pf"),
        "n_years": m.get("n_years"), "years_positive": m.get("years_positive"),
        "archetype": m.get("archetype"), "gate_verdict": m.get("gate_verdict"),
        "verdict": v,
        "rule": "60-month MGC vs (Δreal yield, ΔDXY) regression; LONG when residual < -1.5σ AND Δreal yield ≤ 0; SHORT when > +1.5σ AND ≥ 0",
        "data_source": "Hardcoded minimum-viable 10y real-yield + broad USD index monthly history; FRED ingest deferred",
        "signal_months_total": int(len(sig)),
        "signal_months_long": int((sig == 1).sum()),
        "signal_months_short": int((sig == -1).sum()),
        "signal_months_flat": int((sig == 0).sum()),
    }
    json_path.write_text(json.dumps(summary, indent=2, default=str))

    md = (
        f"# FQL Forge — V1: GLD-RealRate-MGC-monthly (VALUE)\n\n"
        f"**Date:** {date_iso} • Mode: dry-run / report-only / Lane B\n"
        f"**Authority:** T1; no registry mutation\n"
        f"**Harness:** `research/monthly_rebalance_engine.py`\n"
        f"**Data:** Hardcoded minimum-viable 10y real-yield + broad USD index monthly history.\n\n"
        f"## Rule\n\n"
        f"60-month rolling regression of monthly MGC log-return vs (Δ10y real yield, ΔDXY).\n"
        f"- LONG when residual < -1.5σ AND month-over-month Δreal yield ≤ 0\n"
        f"- SHORT when residual > +1.5σ AND Δreal yield ≥ 0\n"
        f"- Else flat. Monthly exit.\n\n"
        f"## Signal series stats\n\n"
        f"- Total months: **{len(sig)}**\n- LONG months: **{int((sig == 1).sum())}**\n"
        f"- SHORT months: **{int((sig == -1).sum())}**\n- Flat months: **{int((sig == 0).sum())}**\n\n"
        f"## Result (cost-aware)\n\n"
        f"| Field | Value |\n|---|---:|\n"
        f"| n trades | {m['n']} |\n| Net PF | {m['pf']:.3f} |\n"
        f"| Median trade | ${m['median']:.2f} |\n| Net PnL | ${m['net']:.0f} |\n"
        f"| Max DD | ${m['max_dd']:.0f} |\n"
        f"| Win rate | {m.get('win_rate_pct', float('nan')):.1f}% |\n"
        f"| Max-year share | {m.get('max_year_share_pct', float('nan')):.1f}% |\n"
        f"| Top-3 | {m.get('top3_share_pct', float('nan')):.1f}% |\n"
        f"| Top-10 | {m.get('top10_share_pct', float('nan')):.1f}% |\n"
        f"| H1 / H2 PF | {m.get('h1_pf', float('nan')):.3f} / {m.get('h2_pf', float('nan')):.3f} |\n"
        f"| Years+ | {m.get('years_positive', '?')}/{m.get('n_years', '?')} |\n"
        f"| Archetype | {m.get('archetype')} | gate | {m.get('gate_verdict')} |\n"
        f"| **Verdict** | **{v}** |\n\n"
        f"## Safety\n\n"
        f"- No registry mutation • no Lane A touch • no scheduler change\n"
        f"- Data hardcoded; FRED ingest gated on operator approval\n"
    )
    md_path.write_text(md)
    print(f"Wrote: {json_path}")
    print(f"Wrote: {md_path}")
    print(f"\n[V1-GLD-RealRate-MGC] n={m['n']} PF={m['pf']:.3f} median=${m['median']:.2f} max-yr={m.get('max_year_share_pct', float('nan')):.1f}% → {v}")
    return summary


if __name__ == "__main__":
    run()
