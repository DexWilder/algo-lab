"""MGC-Donchian focused mutation cycle.

Per operator approval 2026-06-03 (Ask #7). Tests the only positive-median
Donchian variant (XB-DC-EMA-Ladder-MGC: n=980 PF 1.149 median +$1.76) across
three mutation axes:

  1. Vol filter overlay: ema_slope + vol_low(30) and vol_low(40)
  2. Exit alternates:    chandelier / atr_trail
  3. Tail-engine framing: time_stop (fewer exits, longer hold)

Each result captured with full Forge metric block. Temporal split applied to
any survivor (PF ≥ 1.2 + positive median + acceptable concentration).

Kill rules (operator-specified):
- PF < 1.2 AND concentration does not improve  → KILL
- Median flips negative                         → KILL
- Improvement comes from one year only          → ARCHITECTURAL_REJECT (Forge memory)
- Tail-engine PF ≥ 1.30 + median > 0 + ok conc → WATCH_FOR_DEEP_SCREEN

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

from research.crossbreeding.crossbreeding_engine import generate_crossbred_signals  # noqa: E402
from engine.backtest import run_backtest  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402
from research.fql_forge_batch_runner import _metrics, _verdict  # noqa: E402


MUTATIONS = [
    {"label": "XB-DC-EMA-Ladder-MGC-baseline", "entry": "donchian_breakout",
     "filter": "ema_slope", "exit": "profit_ladder", "params": {},
     "axis": "baseline (last cycle)"},
    {"label": "XB-DC-VolLow30-Ladder-MGC", "entry": "donchian_breakout",
     "filter": "ema_slope_vol_low", "exit": "profit_ladder",
     "params": {"vr_threshold": 30},
     "axis": "vol-overlay (low-vol regimes only)"},
    {"label": "XB-DC-VolLow40-Ladder-MGC", "entry": "donchian_breakout",
     "filter": "ema_slope_vol_low", "exit": "profit_ladder",
     "params": {"vr_threshold": 40},
     "axis": "vol-overlay (broader low-vol)"},
    {"label": "XB-DC-EMA-Chandelier-MGC", "entry": "donchian_breakout",
     "filter": "ema_slope", "exit": "chandelier", "params": {},
     "axis": "alt-exit (chandelier trailing)"},
    {"label": "XB-DC-EMA-ATRTrail-MGC", "entry": "donchian_breakout",
     "filter": "ema_slope", "exit": "atr_trail", "params": {},
     "axis": "alt-exit (ATR trail)"},
    {"label": "XB-DC-EMA-TimeStop-MGC", "entry": "donchian_breakout",
     "filter": "ema_slope", "exit": "time_stop", "params": {},
     "axis": "tail-engine framing (time_stop, fewer exits)"},
]


def _run_one(spec, df, cfg):
    sigs = generate_crossbred_signals(
        df, entry_name=spec["entry"], exit_name=spec["exit"],
        filter_name=spec["filter"], params=spec["params"],
    )
    res = run_backtest(df, sigs, mode="both",
                       point_value=cfg["point_value"], symbol="MGC")
    m = _metrics(res["trades_df"], spec["label"], costs=res["stats"]["costs"])
    archetype = "tail" if m["n"] < 500 else "workhorse"
    v = _verdict(m, archetype)
    m["_archetype_routed"] = archetype
    m["_verdict"] = v
    return m, res["trades_df"]


def _apply_kill_rules(m: dict, baseline_max_year: float) -> tuple[str, list[str]]:
    """Apply operator kill rules to one mutation's metrics."""
    notes = []
    pf = m["pf"]
    median = m["median"]
    max_yr = m.get("max_year_share_pct", 100.0)
    arch = m["_archetype_routed"]

    if pf < 1.2 and max_yr >= baseline_max_year:
        return "KILL", ["PF < 1.2 AND concentration not improved"]
    if median < 0:
        return "KILL", ["median flipped negative"]
    if arch == "tail" and pf >= 1.30 and median > 0 and max_yr < 50:
        return "WATCH_FOR_DEEP_SCREEN", [
            f"tail-engine path: PF {pf:.3f}, median ${median:.2f}, max-yr {max_yr:.1f}%"
        ]
    if arch == "workhorse" and pf >= 1.2 and median > 0 and max_yr < 40:
        return "WATCH_FOR_DEEP_SCREEN", [
            f"workhorse path: PF {pf:.3f}, median ${median:.2f}, max-yr {max_yr:.1f}%"
        ]
    if pf >= 1.2 and median > 0 and max_yr >= 40:
        notes.append("PF + median OK but concentration still high — temporal split required")
        return "TEMPORAL_SPLIT_REQUIRED", notes
    return "WATCH", [f"borderline: PF {pf:.3f}, median ${median:.2f}, max-yr {max_yr:.1f}%"]


def _temporal_split(trades: pd.DataFrame) -> dict:
    """Per-year + era breakdown for a survivor."""
    if "entry_time" in trades.columns:
        trades = trades.copy()
        trades["entry_dt"] = pd.to_datetime(trades["entry_time"])
        trades["year"] = trades["entry_dt"].dt.year
    per_year = []
    for y, g in trades.groupby("year"):
        pnl = g["pnl"].values
        wins = pnl[pnl > 0].sum()
        losses = -pnl[pnl < 0].sum()
        pf = wins / losses if losses > 0 else float("inf")
        per_year.append({"year": int(y), "n": int(len(g)), "pf": float(pf),
                         "median": float(np.median(pnl)), "net": float(pnl.sum())})
    trades_sorted = trades.sort_values("entry_dt").reset_index(drop=True)
    cuts = np.linspace(0, len(trades_sorted), 4).astype(int)
    eras = []
    for i in range(3):
        sub = trades_sorted.iloc[cuts[i]:cuts[i+1]]
        if len(sub) == 0:
            continue
        pnl = sub["pnl"].values
        wins = pnl[pnl > 0].sum()
        losses = -pnl[pnl < 0].sum()
        pf = wins / losses if losses > 0 else float("inf")
        eras.append({
            "era": i + 1,
            "start": str(sub.iloc[0]["entry_dt"])[:10],
            "end": str(sub.iloc[-1]["entry_dt"])[:10],
            "n": int(len(sub)), "pf": float(pf),
            "median": float(np.median(pnl)), "net": float(pnl.sum()),
        })
    return {"per_year": per_year, "eras": eras}


def run():
    df = pd.read_csv(ROOT / "data" / "processed" / "MGC_5m.csv")
    cfg = ASSETS["MGC"]

    results = []
    print(f"MGC-Donchian focused mutation cycle — {len(MUTATIONS)} variants\n")
    for spec in MUTATIONS:
        m, trades = _run_one(spec, df, cfg)
        verdict, notes = _apply_kill_rules(
            m, baseline_max_year=m.get("max_year_share_pct", 100.0) if spec["label"].endswith("baseline") else 100.0
        )
        # If verdict needs temporal split (high-conc but otherwise OK), run it
        tsplit = None
        if verdict == "TEMPORAL_SPLIT_REQUIRED" and len(trades) > 30:
            tsplit = _temporal_split(trades)
            # Apply temporal-split rule: if removing the dominant year collapses PF below 1.0
            # or flips median negative → ARCHITECTURAL_REJECT
            dominant_year = max(tsplit["per_year"], key=lambda r: r["net"])
            losers = [r for r in tsplit["per_year"] if r["pf"] < 1.0 and np.isfinite(r["pf"])]
            losing_eras = [e for e in tsplit["eras"] if e["pf"] < 1.0 and np.isfinite(e["pf"])]
            if len(losers) > len(tsplit["per_year"]) / 2 or len(losing_eras) >= 2:
                verdict = "ARCHITECTURAL_REJECT"
                notes.append(f"temporal split: {len(losers)}/{len(tsplit['per_year'])} yrs LOSING, "
                             f"{len(losing_eras)}/3 eras LOSING; dominant yr {dominant_year['year']} "
                             f"net ${dominant_year['net']:.0f}")

        results.append({"spec": spec, "metrics": m, "verdict": verdict,
                        "notes": notes, "temporal_split": tsplit})

        max_yr = m.get("max_year_share_pct", float("nan"))
        print(
            f"  [{spec['axis']:42s}] n={m['n']:5d} PF={m['pf']:.3f} median=${m['median']:7.2f} "
            f"max-yr={max_yr:.1f}% → {verdict}"
        )

    # Write outputs
    out_dir = ROOT / "research" / "data" / "fql_forge" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    date_iso = date.today().isoformat()
    json_path = out_dir / f"forge_mgc_dc_mutation_{date_iso}.json"
    md_path = out_dir / f"forge_mgc_dc_mutation_{date_iso}.md"

    payload = {
        "date": date_iso,
        "cycle": "MGC-Donchian mutation",
        "operator_approval": "OK MGC-Donchian mutation (2026-06-03)",
        "results": [
            {
                "axis": r["spec"]["axis"],
                "label": r["spec"]["label"],
                "params": r["spec"]["params"],
                "metrics": {k: r["metrics"].get(k) for k in (
                    "n", "pf", "median", "net", "max_dd", "win_rate_pct",
                    "max_year_share_pct", "top3_share_pct", "top10_share_pct",
                    "h1_pf", "h2_pf", "n_years", "years_positive", "archetype",
                    "_archetype_routed", "_verdict", "gate_verdict",
                )},
                "verdict": r["verdict"],
                "notes": r["notes"],
                "temporal_split": r["temporal_split"],
            }
            for r in results
        ],
    }
    json_path.write_text(json.dumps(payload, indent=2, default=str))

    md_lines = [
        f"# MGC-Donchian Mutation Cycle — {date_iso}",
        f"\nAuthority T1 / Lane B / report-only. Operator approval: OK MGC-Donchian mutation.\n",
        "## Result table\n",
        "| Axis | n | PF | Median | Max-Yr | Top-3 | Top-10 | H1/H2 | Yrs+ | Verdict |",
        "|---|---:|---:|---:|---:|---:|---:|---|---|---|",
    ]
    for r in results:
        m = r["metrics"]
        md_lines.append(
            f"| {r['spec']['axis']} | {m['n']} | {m['pf']:.3f} | ${m['median']:.2f} | "
            f"{m.get('max_year_share_pct', float('nan')):.1f}% | "
            f"{m.get('top3_share_pct', float('nan')):.1f}% | "
            f"{m.get('top10_share_pct', float('nan')):.1f}% | "
            f"{m.get('h1_pf', float('nan')):.2f} / {m.get('h2_pf', float('nan')):.2f} | "
            f"{m.get('years_positive', '?')}/{m.get('n_years', '?')} | **{r['verdict']}** |"
        )
    md_lines.append("\n## Notes per variant\n")
    for r in results:
        md_lines.append(f"- **{r['spec']['axis']}**: " + "; ".join(r["notes"]) if r["notes"] else f"- **{r['spec']['axis']}**: —")
        if r["temporal_split"]:
            md_lines.append("  - **Temporal split:**")
            for ye in r["temporal_split"]["per_year"]:
                md_lines.append(f"    - {ye['year']}: n={ye['n']} PF={ye['pf']:.3f} net=${ye['net']:.0f}")
            for er in r["temporal_split"]["eras"]:
                md_lines.append(f"    - Era {er['era']} ({er['start']}→{er['end']}): n={er['n']} PF={er['pf']:.3f} net=${er['net']:.0f}")
    md_path.write_text("\n".join(md_lines))
    print(f"\nWrote: {md_path}")
    print(f"Wrote: {json_path}")
    return payload


if __name__ == "__main__":
    run()
