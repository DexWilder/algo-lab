"""First real-candidate pair screens — validates pairs_engine on three theses.

Per operator approval 2026-06-03 (#17 expanded to 3 pairs):
  A. MES/ZN yield-gap value (equity vs rates macro spread)
  B. ZN/ZB curve trade (rates curve-steepener / flattener)
  C. MGC/MCL real-asset spread (commodity relative-value)

Each runs cheap-screen via research.pairs_engine.pairs_backtest.

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

from research.pairs_engine import pairs_backtest, pairs_metrics  # noqa: E402
from research.fql_forge_batch_runner import _verdict  # noqa: E402


def _load(asset):
    return pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")


def _trades_summary(trades: pd.DataFrame) -> dict:
    """Compute per-year / era / H1-H2 split from pairs trades."""
    if trades.empty:
        return {"per_year": [], "eras": [], "h1_pf": np.nan, "h2_pf": np.nan,
                "years_positive": 0, "n_years": 0}
    trades = trades.copy()
    trades["year"] = pd.to_datetime(trades["entry_time"]).dt.year
    per_year = []
    for y, g in trades.groupby("year"):
        pnl = g["pnl"].values
        wins = pnl[pnl > 0].sum()
        losses = -pnl[pnl < 0].sum()
        pf = wins / losses if losses > 0 else float("inf")
        per_year.append({"year": int(y), "n": int(len(g)),
                         "pf": float(pf), "net": float(pnl.sum())})
    n_years = len(per_year)
    years_positive = sum(1 for r in per_year if r["net"] > 0)
    # H1 / H2 split
    mid = len(trades) // 2
    h1 = trades.iloc[:mid]
    h2 = trades.iloc[mid:]
    def _pf(sub):
        if sub.empty: return float("nan")
        w = sub.loc[sub["pnl"] > 0, "pnl"].sum()
        l = -sub.loc[sub["pnl"] < 0, "pnl"].sum()
        return w / l if l > 0 else float("inf")
    # Eras (3 thirds)
    cuts = np.linspace(0, len(trades), 4).astype(int)
    eras = []
    for i in range(3):
        sub = trades.iloc[cuts[i]:cuts[i+1]]
        if sub.empty: continue
        eras.append({"era": i+1, "n": len(sub), "pf": float(_pf(sub)),
                     "net": float(sub["pnl"].sum())})
    return {
        "per_year": per_year, "eras": eras,
        "h1_pf": float(_pf(h1)), "h2_pf": float(_pf(h2)),
        "years_positive": years_positive, "n_years": n_years,
    }


def _classify(m: dict, ts: dict) -> str:
    """Apply operator kill rules to pair screens."""
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
    # Temporal robustness
    if ts["n_years"] > 0 and ts["years_positive"] < ts["n_years"] * 0.5:
        return "ARCHITECTURAL_REJECT (< 50% yrs positive)"
    if pf >= 1.30 and median > 0 and max_yr < 50 and ts["years_positive"] >= ts["n_years"] * 0.6:
        return "WATCH_FOR_DEEP_SCREEN"
    if pf >= 1.20 and median > 0 and max_yr < 50:
        return "WATCH"
    if max_yr >= 50:
        return "TEMPORAL_SPLIT_REQUIRED"
    return "WATCH"


PAIRS = [
    {
        "label": "PAIR-A-MES-ZN-yieldgap-monthly",
        "asset_a": "MES", "asset_b": "ZN",
        "freq": "M", "lookback": 12, "z_threshold": 1.5, "exit_z": 0.5,
        "hedge": "vol_adjusted",
        "thesis": "Equity vs rates yield-gap value: long the cheaper, short the richer at monthly rebalance",
    },
    {
        "label": "PAIR-B-ZN-ZB-curve-monthly",
        "asset_a": "ZN", "asset_b": "ZB",
        "freq": "M", "lookback": 12, "z_threshold": 1.5, "exit_z": 0.5,
        "hedge": "vol_adjusted",
        "thesis": "Rates curve trade: ZN (10y) vs ZB (30y) z-spread; vol-adjusted to neutralize duration",
    },
    {
        "label": "PAIR-C-MGC-MCL-realasset-monthly",
        "asset_a": "MGC", "asset_b": "MCL",
        "freq": "M", "lookback": 12, "z_threshold": 1.5, "exit_z": 0.5,
        "hedge": "vol_adjusted",
        "thesis": "Commodity relative-value: gold vs crude as inflation-sensitive real-asset spread",
    },
]


def run():
    out_dir = ROOT / "research" / "data" / "fql_forge" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    date_iso = date.today().isoformat()

    results = []
    print(f"Pair screens — {len(PAIRS)} candidates\n")
    for spec in PAIRS:
        df_a = _load(spec["asset_a"])
        df_b = _load(spec["asset_b"])
        res = pairs_backtest(
            df_a=df_a, df_b=df_b, asset_a=spec["asset_a"], asset_b=spec["asset_b"],
            freq=spec["freq"], lookback=spec["lookback"],
            z_threshold=spec["z_threshold"], exit_z=spec["exit_z"],
            hedge=spec["hedge"], label=spec["label"],
        )
        m = pairs_metrics(res, spec["label"])
        ts = _trades_summary(res["trades_df"])
        v = _classify(m, ts)
        # Save per-pair details
        max_yr = m.get("max_year_share_pct", float("nan"))
        print(
            f"  [{spec['label']:36s}] n={m['n']:3d} PF={m['pf']:.3f} "
            f"median=${m['median']:8.2f} max-yr={max_yr:.1f}% "
            f"yrs+={ts['years_positive']}/{ts['n_years']} H1/H2={ts['h1_pf']:.2f}/{ts['h2_pf']:.2f} → {v}"
        )
        results.append({
            "spec": spec,
            "metrics": {k: m.get(k) for k in (
                "n", "pf", "median", "net", "max_dd",
                "max_year_share_pct", "top3_share_pct", "top10_share_pct",
                "archetype", "gate_verdict", "cost_block",
            )},
            "temporal": ts,
            "verdict": v,
        })

    json_path = out_dir / f"forge_pair_screens_{date_iso}.json"
    md_path = out_dir / f"forge_pair_screens_{date_iso}.md"
    json_path.write_text(json.dumps({
        "date": date_iso,
        "operator_approval": "OK wire first pair candidate (expanded to 3)",
        "harness": "research.pairs_engine.pairs_backtest",
        "results": results,
    }, indent=2, default=str))

    md_lines = [
        f"# Pair Screens — {date_iso}",
        f"\nAuthority T1 / Lane B / report-only. Harness: `research/pairs_engine.py`.",
        f"Operator approval: OK wire first pair candidate (expanded to 3 per directive).\n",
        "## Result table\n",
        "| Pair | Hedge | n | PF | Median | Max-Yr | Yrs+ | H1/H2 | Eras (PFs) | Verdict |",
        "|---|---|---:|---:|---:|---:|---|---|---|---|",
    ]
    for r in results:
        m = r["metrics"]
        ts = r["temporal"]
        eras_str = " / ".join(f"{e['pf']:.2f}" for e in ts["eras"]) if ts["eras"] else "—"
        md_lines.append(
            f"| {r['spec']['label']} | {r['spec']['hedge']} | {m['n']} | "
            f"{m['pf']:.3f} | ${m['median']:.2f} | "
            f"{m.get('max_year_share_pct', float('nan')):.1f}% | "
            f"{ts['years_positive']}/{ts['n_years']} | "
            f"{ts['h1_pf']:.2f}/{ts['h2_pf']:.2f} | {eras_str} | **{r['verdict']}** |"
        )
    md_lines.append("\n## Per-pair detail\n")
    for r in results:
        md_lines += [
            f"### {r['spec']['label']}",
            f"- Thesis: {r['spec']['thesis']}",
            f"- Verdict: **{r['verdict']}**",
            f"- Per-year:",
        ]
        for y in r["temporal"]["per_year"]:
            md_lines.append(f"  - {y['year']}: n={y['n']} PF={y['pf']:.3f} net=${y['net']:.0f}")
        md_lines.append("")
    md_path.write_text("\n".join(md_lines))
    print(f"\nWrote: {md_path}")
    print(f"Wrote: {json_path}")
    return results


if __name__ == "__main__":
    run()
