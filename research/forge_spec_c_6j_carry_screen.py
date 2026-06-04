"""Spec C — CRY-Policy-Rate-Differential-6J (Cheap-screen wire-up)

Per operator approval 2026-06-02 (build) + 2026-06-03 (wire). Uses the
monthly rebalance harness (research/monthly_rebalance_engine.py) + canonical
Fed Funds + BoJ policy rate monthly series (hardcoded minimum viable; FRED
ingest deferred).

Rule (from harvest note 2026-05-31_10_boj_policy_rate_discount_*.md):
    At each month-end, compute Fed Funds effective − BoJ policy.
    SHORT 6J for the next month IF spread > 12m trailing median
       AND month-over-month change ≥ 0.
    Else flat.
    Exit at next month-end rebalance.

Output: writes report to docs/fql_forge/reports/forge_spec_c_<date>.{md,json}
        + adds taxonomy row.

Authority: T1 / Lane B / report-only. No registry mutation.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from research.monthly_rebalance_engine import (  # noqa: E402
    build_policy_differential_signal,
    monthly_rebalance_run,
)
from research.fql_forge_batch_runner import _metrics, _verdict  # noqa: E402


# ─────────────────────────────────────────────────────────────────────────────
# Minimum viable Fed Funds + BoJ policy rate monthly history (hardcoded).
# Sources of truth:
#   Fed Funds effective: FRED series FEDFUNDS (monthly average, %)
#   BoJ policy rate:     BoJ "Basic loan rate" / IOER trajectory (%)
# Values are rounded to public knowledge; this is a *cheap-screen* surface,
# not decision-grade. FRED ingest gated on separate operator approval.
# ─────────────────────────────────────────────────────────────────────────────

FED_FUNDS = {
    # 2022 — hike cycle started
    "2022-03-31": 0.20, "2022-04-30": 0.33, "2022-05-31": 0.77, "2022-06-30": 1.21,
    "2022-07-31": 1.68, "2022-08-31": 2.33, "2022-09-30": 2.56, "2022-10-31": 3.08,
    "2022-11-30": 3.78, "2022-12-31": 4.10,
    # 2023 — terminal & plateau
    "2023-01-31": 4.33, "2023-02-28": 4.57, "2023-03-31": 4.65, "2023-04-30": 4.83,
    "2023-05-31": 5.06, "2023-06-30": 5.08, "2023-07-31": 5.12, "2023-08-31": 5.33,
    "2023-09-30": 5.33, "2023-10-31": 5.33, "2023-11-30": 5.33, "2023-12-31": 5.33,
    # 2024 — held through Sept then started cutting
    "2024-01-31": 5.33, "2024-02-29": 5.33, "2024-03-31": 5.33, "2024-04-30": 5.33,
    "2024-05-31": 5.33, "2024-06-30": 5.33, "2024-07-31": 5.33, "2024-08-31": 5.33,
    "2024-09-30": 4.83, "2024-10-31": 4.83, "2024-11-30": 4.58, "2024-12-31": 4.33,
    # 2025 — gradual cuts (approx)
    "2025-01-31": 4.33, "2025-02-28": 4.33, "2025-03-31": 4.33, "2025-04-30": 4.33,
    "2025-05-31": 4.08, "2025-06-30": 4.08, "2025-07-31": 4.08, "2025-08-31": 4.08,
    "2025-09-30": 3.83, "2025-10-31": 3.83, "2025-11-30": 3.83, "2025-12-31": 3.83,
    # 2026 — sitting around 3.83 through latest
    "2026-01-31": 3.83, "2026-02-28": 3.83, "2026-03-31": 3.83, "2026-04-30": 3.83,
    "2026-05-31": 3.83,
}

BOJ_RATE = {
    # 2022-2023 — NIRP / yield curve control era
    "2022-03-31": -0.10, "2022-04-30": -0.10, "2022-05-31": -0.10, "2022-06-30": -0.10,
    "2022-07-31": -0.10, "2022-08-31": -0.10, "2022-09-30": -0.10, "2022-10-31": -0.10,
    "2022-11-30": -0.10, "2022-12-31": -0.10,
    "2023-01-31": -0.10, "2023-02-28": -0.10, "2023-03-31": -0.10, "2023-04-30": -0.10,
    "2023-05-31": -0.10, "2023-06-30": -0.10, "2023-07-31": -0.10, "2023-08-31": -0.10,
    "2023-09-30": -0.10, "2023-10-31": -0.10, "2023-11-30": -0.10, "2023-12-31": -0.10,
    # 2024 — exited NIRP March 2024; first hike July 2024
    "2024-01-31": -0.10, "2024-02-29": -0.10, "2024-03-31": 0.00, "2024-04-30": 0.00,
    "2024-05-31": 0.00, "2024-06-30": 0.00, "2024-07-31": 0.25, "2024-08-31": 0.25,
    "2024-09-30": 0.25, "2024-10-31": 0.25, "2024-11-30": 0.25, "2024-12-31": 0.25,
    # 2025 — second hike commonly modeled to ~0.50
    "2025-01-31": 0.50, "2025-02-28": 0.50, "2025-03-31": 0.50, "2025-04-30": 0.50,
    "2025-05-31": 0.50, "2025-06-30": 0.50, "2025-07-31": 0.50, "2025-08-31": 0.50,
    "2025-09-30": 0.50, "2025-10-31": 0.50, "2025-11-30": 0.50, "2025-12-31": 0.50,
    # 2026 — held
    "2026-01-31": 0.50, "2026-02-28": 0.50, "2026-03-31": 0.50, "2026-04-30": 0.50,
    "2026-05-31": 0.50,
}


def run():
    fed = pd.Series(FED_FUNDS)
    boj = pd.Series(BOJ_RATE)
    sig = build_policy_differential_signal(fed, boj, lookback_months=12)
    print(f"Signal series: {len(sig)} months, {(sig == -1).sum()} short / {(sig == 0).sum()} flat")
    if (sig != 0).sum() == 0:
        print("WARNING: no non-zero signals — rule never fires on this data window")
        return

    res = monthly_rebalance_run(asset="6J", signal=sig, label="CRY-Policy-Rate-Differential-6J")
    m = _metrics(res["trades_df"], "CRY-Policy-Rate-Differential-6J",
                 costs=res["stats"]["costs"])
    v = _verdict(m, "tail")

    out_dir = ROOT / "research" / "data" / "fql_forge" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    date_iso = date.today().isoformat()
    json_path = out_dir / f"forge_spec_c_{date_iso}.json"
    md_path = out_dir / f"forge_spec_c_{date_iso}.md"

    # Summary fields for the report
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
        "h1_pf": m.get("h1_pf"),
        "h2_pf": m.get("h2_pf"),
        "n_years": m.get("n_years"),
        "years_positive": m.get("years_positive"),
        "archetype": m.get("archetype"),
        "gate_verdict": m.get("gate_verdict"),
        "blocker_reason": m.get("blocker_reason"),
        "cost_block": m.get("cost_block"),
        "verdict": v,
        "rule": "SHORT 6J when (Fed - BoJ) > 12m trailing median AND Δ ≥ 0; else flat",
        "data_source": "Hardcoded minimum-viable Fed Funds + BoJ policy rate monthly history; FRED ingest deferred",
        "harness": "research.monthly_rebalance_engine.monthly_rebalance_run",
        "signal_months_total": int(len(sig)),
        "signal_months_short": int((sig == -1).sum()),
        "signal_months_flat": int((sig == 0).sum()),
    }
    json_path.write_text(json.dumps(summary, indent=2, default=str))

    md = (
        f"# FQL Forge — Spec C: CRY-Policy-Rate-Differential-6J\n\n"
        f"**Date:** {date_iso}  •  **Mode:** dry-run / report-only / Lane B\n"
        f"**Authority:** T1; no registry mutation; no Lane A touch\n"
        f"**Harness:** `research/monthly_rebalance_engine.py` (built 2026-06-02; smoke-passed 2026-06-03)\n"
        f"**Data:** Hardcoded minimum-viable Fed Funds + BoJ policy rate monthly history. FRED ingest deferred per operator decision.\n\n"
        f"## Rule\n\n"
        f"At each month-end, compute `spread = Fed Funds − BoJ policy`.\n"
        f"- SHORT 6J for the next month IF `spread > 12m trailing median` AND `Δspread ≥ 0`.\n"
        f"- Else flat. Mechanical month-end exit.\n\n"
        f"## Signal series stats\n\n"
        f"- Total months: **{len(sig)}**\n"
        f"- Short months: **{int((sig == -1).sum())}**\n"
        f"- Flat months: **{int((sig == 0).sum())}**\n\n"
        f"## Result (cost-aware)\n\n"
        f"| Field | Value |\n|---|---:|\n"
        f"| n trades | {m['n']} |\n"
        f"| Net PF | {m['pf']:.3f} |\n"
        f"| Median trade | ${m['median']:.2f} |\n"
        f"| Net PnL | ${m['net']:.0f} |\n"
        f"| Max DD | ${m['max_dd']:.0f} |\n"
        f"| Win rate | {m.get('win_rate_pct', float('nan')):.1f}% |\n"
        f"| Max-year share | {m.get('max_year_share_pct', float('nan')):.1f}% |\n"
        f"| Top-3 share | {m.get('top3_share_pct', float('nan')):.1f}% |\n"
        f"| Top-10 share | {m.get('top10_share_pct', float('nan')):.1f}% |\n"
        f"| H1 PF / H2 PF | {m.get('h1_pf', float('nan')):.3f} / {m.get('h2_pf', float('nan')):.3f} |\n"
        f"| Years positive | {m.get('years_positive', '?')}/{m.get('n_years', '?')} |\n"
        f"| Archetype | {m.get('archetype')} |\n"
        f"| Gate verdict | {m.get('gate_verdict')} |\n"
        f"| Blocker reason | {m.get('blocker_reason') or '—'} |\n"
        f"| **Cheap-screen verdict** | **{v}** |\n\n"
        f"## Safety\n\n"
        f"- No registry mutation • no Lane A touch • no scheduler change\n"
        f"- Data source is hardcoded canonical history; not decision-grade until FRED ingest is approved\n"
    )
    md_path.write_text(md)
    print(f"Wrote: {json_path}")
    print(f"Wrote: {md_path}")
    print(f"\n[CRY-Policy-Rate-Differential-6J] n={m['n']} PF={m['pf']:.3f} median=${m['median']:.2f} max-yr={m.get('max_year_share_pct', float('nan')):.1f}% → {v}")
    return summary


if __name__ == "__main__":
    run()
