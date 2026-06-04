"""Pair screens 2026-06-04: PAIR-B z-sweep diagnostic + signal-class re-tests.

Per operator approval 2026-06-04 (#18 + #19 follow-on):
  Diagnostic: PAIR-B (ZN/ZB return_z) sweep across z ∈ {0.8, 1.0, 1.2}.
  Re-tests using new signal classes:
    A. ZN/ZB curve via level_z (proved 5 trades possible in smoke)
    B. MGC/MCL real-asset via level_z
    C. MES vs ZN via fundamental_z using Fed-funds / 10y real-yield differential
       as a proxy fundamentals signal (note: NOT earnings yield yet — ACM/earnings
       deferred per operator). This proves the fundamental_z plumbing end-to-end
       on a real economically-motivated signal.

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

from research.pairs_engine import pairs_backtest, pairs_metrics, _resample_close  # noqa: E402
from research.fundamentals_cache import load_series  # noqa: E402
from research.fql_forge_batch_runner import _verdict  # noqa: E402


def _load(asset):
    return pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")


def _trades_summary(trades: pd.DataFrame) -> dict:
    if trades.empty:
        return {"per_year": [], "yrs_pos": 0, "n_yrs": 0,
                "h1_pf": float("nan"), "h2_pf": float("nan")}
    trades = trades.copy()
    trades["year"] = pd.to_datetime(trades["entry_time"]).dt.year
    per_year = []
    for y, g in trades.groupby("year"):
        pnl = g["pnl"].values
        w = pnl[pnl > 0].sum()
        l = -pnl[pnl < 0].sum()
        pf = w / l if l > 0 else float("inf")
        per_year.append({"year": int(y), "n": int(len(g)), "pf": float(pf),
                         "net": float(pnl.sum())})
    mid = len(trades) // 2
    def _pf(sub):
        if sub.empty: return float("nan")
        w = sub.loc[sub["pnl"] > 0, "pnl"].sum()
        l = -sub.loc[sub["pnl"] < 0, "pnl"].sum()
        return w / l if l > 0 else float("inf")
    return {
        "per_year": per_year,
        "yrs_pos": sum(1 for r in per_year if r["net"] > 0),
        "n_yrs": len(per_year),
        "h1_pf": float(_pf(trades.iloc[:mid])),
        "h2_pf": float(_pf(trades.iloc[mid:])),
    }


def _classify(m: dict, ts: dict) -> str:
    n = m.get("n", 0)
    pf = m.get("pf", 0)
    median = m.get("median", 0)
    max_yr = m.get("max_year_share_pct", 100)
    if n < 5:
        return "KILL (insufficient-n)"
    if median < 0:
        return "KILL (median negative)"
    if pf < 1.2:
        return "KILL (PF < 1.2)"
    if ts["n_yrs"] > 0 and ts["yrs_pos"] < ts["n_yrs"] * 0.5:
        return "ARCHITECTURAL_REJECT (< 50% yrs positive)"
    if pf >= 1.30 and median > 0 and max_yr < 50 and ts["yrs_pos"] >= ts["n_yrs"] * 0.6:
        return "WATCH_FOR_DEEP_SCREEN"
    return "WATCH" if max_yr < 50 else "TEMPORAL_SPLIT_REQUIRED"


def run_pair_b_sweep():
    """PAIR-B ZN/ZB return_z z-sweep — operator-approved diagnostic."""
    df_a = _load("ZN")
    df_b = _load("ZB")
    rows = []
    print("PAIR-B z-sweep (return_z) on ZN/ZB:")
    for z in (0.8, 1.0, 1.2):
        res = pairs_backtest(df_a=df_a, df_b=df_b, asset_a="ZN", asset_b="ZB",
                             freq="M", lookback=12, z_threshold=z, exit_z=0.3,
                             hedge="vol_adjusted", label=f"PAIR-B-z{z}")
        m = pairs_metrics(res, f"PAIR-B-z{z}")
        ts = _trades_summary(res["trades_df"])
        v = _classify(m, ts)
        max_yr = m.get("max_year_share_pct", float("nan"))
        rows.append({"z": z, "n": m["n"], "pf": m["pf"], "median": m["median"],
                     "max_yr": max_yr, "verdict": v,
                     "yrs+": ts["yrs_pos"], "n_yrs": ts["n_yrs"]})
        print(f"  z={z}: n={m['n']:3d} PF={m['pf']:.3f} median=${m['median']:8.2f} max-yr={max_yr:.1f}% yrs+={ts['yrs_pos']}/{ts['n_yrs']} → {v}")
    return rows


def run_signal_class_candidates():
    """Real candidate re-tests using new signal classes."""
    out_rows = []

    # Candidate A — ZN/ZB curve via level_z (curve mean-reversion)
    df_zn, df_zb = _load("ZN"), _load("ZB")
    a_lvl = _resample_close(df_zn, "M")
    b_lvl = _resample_close(df_zb, "M")
    res = pairs_backtest(df_a=df_zn, df_b=df_zb, asset_a="ZN", asset_b="ZB",
                         freq="M", lookback=12, z_threshold=1.5, exit_z=0.5,
                         hedge="vol_adjusted", label="ZN-ZB-curve-level_z",
                         signal_class="level_z",
                         series_a_override=a_lvl, series_b_override=b_lvl)
    m = pairs_metrics(res, "ZN-ZB-curve-level_z")
    ts = _trades_summary(res["trades_df"])
    v = _classify(m, ts)
    print(f"\nReal candidate re-tests via new signal classes:")
    print(f"  [ZN-ZB-curve-level_z         ] n={m['n']:3d} PF={m['pf']:.3f} median=${m['median']:8.2f} max-yr={m.get('max_year_share_pct', float('nan')):.1f}% → {v}")
    out_rows.append({"label": "ZN-ZB-curve-level_z", "signal_class": "level_z",
                     "metrics": dict(m), "temporal": ts, "verdict": v})

    # Candidate B — MGC/MCL real-asset via level_z
    df_mgc, df_mcl = _load("MGC"), _load("MCL")
    a_lvl = _resample_close(df_mgc, "M")
    b_lvl = _resample_close(df_mcl, "M")
    res = pairs_backtest(df_a=df_mgc, df_b=df_mcl, asset_a="MGC", asset_b="MCL",
                         freq="M", lookback=12, z_threshold=1.5, exit_z=0.5,
                         hedge="vol_adjusted", label="MGC-MCL-real-level_z",
                         signal_class="level_z",
                         series_a_override=a_lvl, series_b_override=b_lvl)
    m = pairs_metrics(res, "MGC-MCL-real-level_z")
    ts = _trades_summary(res["trades_df"])
    v = _classify(m, ts)
    print(f"  [MGC-MCL-real-level_z         ] n={m['n']:3d} PF={m['pf']:.3f} median=${m['median']:8.2f} max-yr={m.get('max_year_share_pct', float('nan')):.1f}% → {v}")
    out_rows.append({"label": "MGC-MCL-real-level_z", "signal_class": "level_z",
                     "metrics": dict(m), "temporal": ts, "verdict": v})

    # Candidate C — MES/ZN macro-real-rate via fundamental_z
    # Per operator (defer earnings yield): use what's available in the cache.
    # Reasonable substitute: 10y real yield as a single-leg fundamental signal,
    # paired against USD-broad as the macro counter-leg. PnL still on MES/ZN.
    # Note: this is a PLUMBING DEMO of fundamental_z — not the V2 earnings spec.
    df_mes, df_zn = _load("MES"), _load("ZN")
    real_yield = load_series("real_yield_10y")
    dxy = load_series("usd_broad")
    res = pairs_backtest(df_a=df_mes, df_b=df_zn, asset_a="MES", asset_b="ZN",
                         freq="M", lookback=12, z_threshold=1.5, exit_z=0.5,
                         hedge="vol_adjusted",
                         label="MES-ZN-macro-fundamental_z",
                         signal_class="fundamental_z",
                         series_a_override=real_yield,
                         series_b_override=dxy)
    m = pairs_metrics(res, "MES-ZN-macro-fundamental_z")
    ts = _trades_summary(res["trades_df"])
    v = _classify(m, ts)
    print(f"  [MES-ZN-macro-fundamental_z   ] n={m['n']:3d} PF={m['pf']:.3f} median=${m['median']:8.2f} max-yr={m.get('max_year_share_pct', float('nan')):.1f}% → {v}")
    out_rows.append({"label": "MES-ZN-macro-fundamental_z",
                     "signal_class": "fundamental_z",
                     "metrics": dict(m), "temporal": ts, "verdict": v})

    return out_rows


def run():
    out_dir = ROOT / "research" / "data" / "fql_forge" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    date_iso = date.today().isoformat()

    sweep_rows = run_pair_b_sweep()
    cand_rows = run_signal_class_candidates()

    payload = {
        "date": date_iso,
        "operator_approvals": ["#18 PAIR-B z-sweep", "#19 signal-class adapter"],
        "pair_b_zsweep": sweep_rows,
        "signal_class_candidates": cand_rows,
    }
    json_path = out_dir / f"forge_pair_screens_2026-06-04.json"
    md_path = out_dir / f"forge_pair_screens_2026-06-04.md"
    json_path.write_text(json.dumps(payload, indent=2, default=str))

    md_lines = [
        f"# Pair Screens — {date_iso}",
        "\nAuthority T1 / Lane B / report-only.\n",
        "## PAIR-B z-sweep (return_z)\n",
        "| z | n | PF | Median | Max-Yr | Yrs+ | Verdict |",
        "|---:|---:|---:|---:|---:|---|---|",
    ]
    for r in sweep_rows:
        md_lines.append(f"| {r['z']} | {r['n']} | {r['pf']:.3f} | ${r['median']:.2f} | {r['max_yr']:.1f}% | {r['yrs+']}/{r['n_yrs']} | {r['verdict']} |")
    md_lines.append("\n## Signal-class candidates\n")
    md_lines.append("| Candidate | Class | n | PF | Median | Max-Yr | Yrs+ | H1/H2 | Verdict |")
    md_lines.append("|---|---|---:|---:|---:|---:|---|---|---|")
    for r in cand_rows:
        m = r["metrics"]; ts = r["temporal"]
        md_lines.append(
            f"| {r['label']} | {r['signal_class']} | {m['n']} | {m['pf']:.3f} | "
            f"${m['median']:.2f} | {m.get('max_year_share_pct', float('nan')):.1f}% | "
            f"{ts['yrs_pos']}/{ts['n_yrs']} | {ts['h1_pf']:.2f}/{ts['h2_pf']:.2f} | {r['verdict']} |"
        )
    md_path.write_text("\n".join(md_lines))
    print(f"\nWrote: {md_path}")
    print(f"Wrote: {json_path}")


if __name__ == "__main__":
    run()
