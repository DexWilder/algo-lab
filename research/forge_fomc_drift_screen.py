"""FOMC drift event-window candidate (Lane B pivot per operator 2026-06-04).

Tests post-FOMC drift on MES and ZN using the event-window primitive.

Calendar fidelity: hardcoded FOMC scheduled meeting dates, 2019–2026. These are
well-known canonical FOMC release dates, ~6-week cadence, 8 meetings/year
(plus occasional emergency meetings — excluded for consistency). All times
set to 14:00 ET as the canonical statement-release timestamp. Marked as
"canonical-rule-based" — high confidence vs the prior 2nd-Wed proxy used
for Treasury auctions.

Two legs tested:
  - **Drift LONG (MES)**: enter +1 bar after statement, exit +24 bars (~2h).
    Hypothesis: equity drifts in initial post-release direction; we trade
    long-only as base case to see if positive drift dominates.
  - **Drift LONG (ZN)**: same window on 10y Treasury. Hypothesis: post-FOMC
    rate-curve drift.

Authority: T1 / Lane B / report-only. No registry mutation.
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from research.event_window_engine import generate_event_window_signals  # noqa: E402
from research.fql_forge_batch_runner import _metrics, _verdict  # noqa: E402


# ─────────────────────────────────────────────────────────────────────────────
# FOMC calendar (canonical rule-based, 14:00 ET statement release time)
# Scheduled regular meetings only. Emergency / intermeeting moves excluded.
# Source: FOMC scheduled-meeting calendar (Federal Reserve press releases).
# ─────────────────────────────────────────────────────────────────────────────

FOMC_MEETINGS = [
    # 2019
    "2019-01-30", "2019-03-20", "2019-05-01", "2019-06-19",
    "2019-07-31", "2019-09-18", "2019-10-30", "2019-12-11",
    # 2020
    "2020-01-29", "2020-04-29", "2020-06-10", "2020-07-29",
    "2020-09-16", "2020-11-05", "2020-12-16",
    # 2021
    "2021-01-27", "2021-03-17", "2021-04-28", "2021-06-16",
    "2021-07-28", "2021-09-22", "2021-11-03", "2021-12-15",
    # 2022
    "2022-01-26", "2022-03-16", "2022-05-04", "2022-06-15",
    "2022-07-27", "2022-09-21", "2022-11-02", "2022-12-14",
    # 2023
    "2023-02-01", "2023-03-22", "2023-05-03", "2023-06-14",
    "2023-07-26", "2023-09-20", "2023-11-01", "2023-12-13",
    # 2024
    "2024-01-31", "2024-03-20", "2024-05-01", "2024-06-12",
    "2024-07-31", "2024-09-18", "2024-11-07", "2024-12-18",
    # 2025 (canonical 6-week cadence; published Fed calendar)
    "2025-01-29", "2025-03-19", "2025-05-07", "2025-06-18",
    "2025-07-30", "2025-09-17", "2025-10-29", "2025-12-10",
    # 2026 (canonical 6-week cadence forward-projection)
    "2026-01-28", "2026-03-18", "2026-04-29",
]

FOMC_RELEASE_TIME = "14:00:00"  # ET, canonical statement release


def _events_with_time(dates: list[str], time_str: str) -> list[pd.Timestamp]:
    return [pd.to_datetime(f"{d} {time_str}") for d in dates]


def _classify(m: dict, tag_prefix: str = "") -> str:
    """Apply standard cheap-screen kill rules."""
    n = m.get("n", 0)
    pf = m.get("pf", 0)
    median = m.get("median", 0)
    max_yr = m.get("max_year_share_pct", 100)
    if n < 10:
        return f"KILL (insufficient-n, n={n})"
    if median < 0:
        return "KILL (median negative)"
    if pf < 1.15:  # tail-engine VIABLE threshold
        return "KILL (PF < 1.15)"
    if pf >= 1.30 and median > 0 and max_yr < 50:
        return "WATCH_FOR_DEEP_SCREEN"
    if max_yr >= 50:
        return "TEMPORAL_SPLIT_REQUIRED"
    return "WATCH"


def run_one(asset: str, events: list, label: str,
            entry_offset_bars: int = 1, exit_offset_bars: int = 24,
            direction: str = "long"):
    from engine.asset_config import ASSETS
    from engine.backtest import run_backtest
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    cfg = ASSETS[asset]
    sigs = generate_event_window_signals(
        df, events=events,
        entry_offset_bars=entry_offset_bars, exit_offset_bars=exit_offset_bars,
        direction=direction,
    )
    res = run_backtest(df, sigs, mode="both",
                       point_value=cfg["point_value"], symbol=asset)
    m = _metrics(res["trades_df"], label, costs=res["stats"]["costs"])
    v = _classify(m)
    return m, v


def per_year_summary(trades_df):
    if trades_df.empty:
        return []
    df = trades_df.copy()
    df["entry_dt"] = pd.to_datetime(df["entry_time"])
    df["year"] = df["entry_dt"].dt.year
    rows = []
    for y, g in df.groupby("year"):
        pnl = g["pnl"].values
        w = pnl[pnl > 0].sum()
        l = -pnl[pnl < 0].sum()
        pf = w / l if l > 0 else float("inf")
        rows.append({"year": int(y), "n": int(len(g)), "pf": float(pf),
                     "net": float(pnl.sum())})
    return rows


def run():
    events = _events_with_time(FOMC_MEETINGS, FOMC_RELEASE_TIME)
    print(f"FOMC meetings in calendar: {len(events)} (2019-01-30 → {FOMC_MEETINGS[-1]})\n")
    print("FOMC drift screens (post-statement +24 bars ≈ 2h hold):\n")

    candidates = [
        {"asset": "MES", "label": "EVT-FOMC-Drift-MES-Long",
         "direction": "long", "entry_offset_bars": 1, "exit_offset_bars": 24},
        {"asset": "MES", "label": "EVT-FOMC-Drift-MES-Short",
         "direction": "short", "entry_offset_bars": 1, "exit_offset_bars": 24},
        {"asset": "ZN", "label": "EVT-FOMC-Drift-ZN-Long",
         "direction": "long", "entry_offset_bars": 1, "exit_offset_bars": 24},
        {"asset": "ZN", "label": "EVT-FOMC-Drift-ZN-Short",
         "direction": "short", "entry_offset_bars": 1, "exit_offset_bars": 24},
        # Longer hold version: 6 bars (~30min) post-release — captures very-short drift
        {"asset": "MES", "label": "EVT-FOMC-Drift-MES-Long-30min",
         "direction": "long", "entry_offset_bars": 1, "exit_offset_bars": 6},
    ]

    results = []
    for spec in candidates:
        from engine.asset_config import ASSETS
        from engine.backtest import run_backtest
        df = pd.read_csv(ROOT / "data" / "processed" / f"{spec['asset']}_5m.csv")
        cfg = ASSETS[spec["asset"]]
        sigs = generate_event_window_signals(
            df, events=events,
            entry_offset_bars=spec["entry_offset_bars"],
            exit_offset_bars=spec["exit_offset_bars"],
            direction=spec["direction"],
        )
        res = run_backtest(df, sigs, mode="both",
                           point_value=cfg["point_value"], symbol=spec["asset"])
        m = _metrics(res["trades_df"], spec["label"], costs=res["stats"]["costs"])
        v = _classify(m)
        per_yr = per_year_summary(res["trades_df"])
        n_yrs = len(per_yr)
        yrs_pos = sum(1 for r in per_yr if r["net"] > 0)
        max_yr = m.get("max_year_share_pct", float("nan"))
        print(
            f"  [{spec['label']:32s}] n={m['n']:3d} PF={m['pf']:.3f} "
            f"median=${m['median']:8.2f} max-yr={max_yr:.1f}% yrs+={yrs_pos}/{n_yrs} "
            f"H1/H2={m.get('h1_pf', float('nan')):.2f}/{m.get('h2_pf', float('nan')):.2f} "
            f"→ {v}"
        )
        results.append({
            "spec": spec,
            "metrics": {k: m.get(k) for k in (
                "n", "pf", "median", "net", "max_dd",
                "max_year_share_pct", "top3_share_pct", "top10_share_pct",
                "h1_pf", "h2_pf", "win_rate_pct", "n_years", "years_positive",
                "archetype", "gate_verdict", "cost_block",
            )},
            "per_year": per_yr,
            "verdict": v,
        })

    out_dir = ROOT / "research" / "data" / "fql_forge" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    date_iso = date.today().isoformat()
    json_path = out_dir / f"forge_fomc_drift_{date_iso}.json"
    md_path = out_dir / f"forge_fomc_drift_{date_iso}.md"
    json_path.write_text(json.dumps({
        "date": date_iso,
        "calendar_fidelity": "canonical-rule-based (FOMC scheduled meeting dates 2019-2026)",
        "operator_approval": "OK pivot to event-window (2026-06-04)",
        "candidates": results,
    }, indent=2, default=str))

    md_lines = [
        f"# FQL Forge — FOMC Drift Event-Window Screens — {date_iso}",
        "\nAuthority T1 / Lane B / report-only.",
        f"Calendar: {len(FOMC_MEETINGS)} canonical FOMC meeting dates (2019-2026), 14:00 ET release.\n",
        "## Result table\n",
        "| Candidate | n | PF | Median | Max-Yr | Top-3 | Yrs+ | H1/H2 | Verdict |",
        "|---|---:|---:|---:|---:|---:|---|---|---|",
    ]
    for r in results:
        m = r["metrics"]
        n_yrs = len(r["per_year"])
        yrs_pos = sum(1 for y in r["per_year"] if y["net"] > 0)
        md_lines.append(
            f"| {r['spec']['label']} | {m['n']} | {m['pf']:.3f} | "
            f"${m['median']:.2f} | {m.get('max_year_share_pct', float('nan')):.1f}% | "
            f"{m.get('top3_share_pct', float('nan')):.1f}% | "
            f"{yrs_pos}/{n_yrs} | "
            f"{m.get('h1_pf', float('nan')):.2f}/{m.get('h2_pf', float('nan')):.2f} | "
            f"**{r['verdict']}** |"
        )
    md_path.write_text("\n".join(md_lines))
    print(f"\nWrote: {md_path}")
    print(f"Wrote: {json_path}")
    return results


if __name__ == "__main__":
    run()
