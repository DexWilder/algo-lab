#!/usr/bin/env python3
"""FQL Forge Batch Runner — pre-Phase-0 Lane B automation (dry-run / report-only).

Goal: reduce operator friction in producing continuous Forge evidence without
touching Lane A. Operator-driven CLI tool. NEVER mutates protected state.

Allowed:
    - Read candidate pool (hybrid_candidates_*.md), donor pool (registry +
      proven_donors), harvest triage (research/data/harvest_triage/*.md)
    - Generate candidate batches (top N by leverage)
    - Run cheap screens via known harnesses (crossbreeding engine swaps,
      A/B comparisons on existing strategy code)
    - Classify PASS / WATCH / KILL / RETEST per the verdict standard
    - Write result artifacts (markdown + JSON)
    - Surface next-batch recommendation

NOT allowed (no operator approval, no apply mode):
    - Live registry status changes
    - Strategy promotion
    - Portfolio composition changes
    - Runtime / scheduler / checkpoint / hold-state changes
    - Live trading logic changes

Usage:
    python3 research/fql_forge_batch_runner.py --top 5 --dry-run
    python3 research/fql_forge_batch_runner.py --top 3
    python3 research/fql_forge_batch_runner.py --list-only
    python3 research/fql_forge_batch_runner.py --candidate XB-PB-EMA-Ladder-MNQ
"""

import argparse
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

# ── Candidate registry ────────────────────────────────────────────────────────
# Each candidate: callable that returns dict(label, n, net, pf, median, max_dd,
# max_single_pct, win_rate, sharpe). Only candidates with known harnesses are
# listed here. Others are surfaced as NEEDS_HARNESS.

REPORTS_DIR = ROOT / "docs" / "fql_forge"
DATA_DIR = ROOT / "data" / "processed"
PARAMS_DEFAULT = {"stop_mult": 2.0, "target_mult": 4.0, "trail_mult": 2.5}


def _load(asset: str) -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / f"{asset}_5m.csv")


def _metrics(trades_df, label) -> dict:
    if trades_df is None or trades_df.empty:
        return {"label": label, "n": 0, "net": 0.0, "pf": float("nan"),
                "median": 0.0, "max_dd": 0.0, "max_single_pct": 0.0,
                "win_rate": 0.0, "sharpe": float("nan")}
    pnl = trades_df["pnl"].values
    n = len(pnl); net = float(pnl.sum())
    gp = pnl[pnl > 0].sum(); gl = abs(pnl[pnl < 0].sum())
    pf = float(gp / gl) if gl > 0 else float("inf")
    eq = np.cumsum(pnl)
    max_dd = float((eq - np.maximum.accumulate(eq)).min())
    abs_total = abs(pnl).sum()
    max_single_pct = float(abs(pnl).max() / abs_total * 100) if abs_total > 0 else 0
    std = float(np.std(pnl))
    sharpe = float(pnl.mean() / std * np.sqrt(n / 6)) if std > 0 else float("nan")
    return {"label": label, "n": n, "net": net, "pf": pf,
            "median": float(np.median(pnl)), "max_dd": max_dd,
            "max_single_pct": max_single_pct,
            "win_rate": float((pnl > 0).mean()), "sharpe": sharpe}


def _verdict(m: dict, archetype: str = "auto") -> str:
    """Classify per operator's standard: PASS / WATCH / KILL / RETEST."""
    n, pf = m["n"], m["pf"]
    if n == 0:
        return "RETEST"
    arche = archetype
    if arche == "auto":
        arche = "workhorse" if n >= 500 else "tail"
    if arche == "workhorse":
        if pf >= 1.20: return "PASS"
        if pf >= 1.05: return "WATCH"
        return "KILL"
    else:
        if n < 30:
            return "RETEST" if pf > 1.0 else "KILL"
        if pf >= 1.30: return "PASS"
        if pf >= 1.15: return "PASS"  # tail-engine VIABLE
        if pf >= 1.0: return "WATCH"
        return "KILL"


def _xb_swap(asset: str, entry_name: str, label: str) -> dict:
    df = _load(asset)
    cfg = ASSETS[asset]
    sigs = generate_crossbred_signals(df, entry_name=entry_name,
                                       exit_name="profit_ladder",
                                       filter_name="ema_slope",
                                       params=PARAMS_DEFAULT)
    res = run_backtest(df, sigs, mode="both",
                       point_value=cfg["point_value"], symbol=asset)
    return _metrics(res["trades_df"], label)


# Candidate definitions: (id, asset, gap, runner-callable, archetype, baseline-note)
# Add new candidates here. Runner functions must return a dict per _metrics().
CANDIDATES = {
    # Cross-asset extension of today's confirmed entry-substitution PASSes
    "XB-PB-EMA-Ladder-MES": {
        "gap": "Workhorse cross-asset (PB + proven trio)",
        "asset": "MES", "archetype": "workhorse",
        "runner": lambda: _xb_swap("MES", "pb_pullback", "XB-PB-EMA-Ladder-MES"),
        "baseline": "XB-PB-MNQ baseline PF 1.403 (2026-05-05)",
    },
    "XB-PB-EMA-Ladder-MGC": {
        "gap": "Workhorse cross-asset",
        "asset": "MGC", "archetype": "workhorse",
        "runner": lambda: _xb_swap("MGC", "pb_pullback", "XB-PB-EMA-Ladder-MGC"),
        "baseline": "XB-PB-MNQ baseline PF 1.403",
    },
    "XB-PB-EMA-Ladder-MCL": {
        "gap": "Workhorse cross-asset / energy",
        "asset": "MCL", "archetype": "workhorse",
        "runner": lambda: _xb_swap("MCL", "pb_pullback", "XB-PB-EMA-Ladder-MCL"),
        "baseline": "XB-PB-MNQ baseline PF 1.403",
    },
    "XB-PB-EMA-Ladder-MYM": {
        "gap": "Workhorse cross-asset",
        "asset": "MYM", "archetype": "workhorse",
        "runner": lambda: _xb_swap("MYM", "pb_pullback", "XB-PB-EMA-Ladder-MYM"),
        "baseline": "XB-PB-MNQ baseline PF 1.403",
    },
    "XB-BB-EMA-Ladder-MES": {
        "gap": "Workhorse cross-asset (BB + proven trio)",
        "asset": "MES", "archetype": "workhorse",
        "runner": lambda: _xb_swap("MES", "bb_reversion", "XB-BB-EMA-Ladder-MES"),
        "baseline": "XB-BB-MNQ baseline PF 1.245 (2026-05-05)",
    },
    "XB-BB-EMA-Ladder-MGC": {
        "gap": "Workhorse cross-asset",
        "asset": "MGC", "archetype": "workhorse",
        "runner": lambda: _xb_swap("MGC", "bb_reversion", "XB-BB-EMA-Ladder-MGC"),
        "baseline": "XB-BB-MNQ baseline PF 1.245",
    },
    "XB-BB-EMA-Ladder-MCL": {
        "gap": "Workhorse cross-asset / energy",
        "asset": "MCL", "archetype": "workhorse",
        "runner": lambda: _xb_swap("MCL", "bb_reversion", "XB-BB-EMA-Ladder-MCL"),
        "baseline": "XB-BB-MNQ baseline PF 1.245",
    },
    "XB-BB-EMA-Ladder-MYM": {
        "gap": "Workhorse cross-asset",
        "asset": "MYM", "archetype": "workhorse",
        "runner": lambda: _xb_swap("MYM", "bb_reversion", "XB-BB-EMA-Ladder-MYM"),
        "baseline": "XB-BB-MNQ baseline PF 1.245",
    },
    # Re-validate proven trio on its native asset cross-section using PB / BB entries
    # (these complete the entry-substitution sweep across the full 4-asset universe)
}


def _select_top(n: int):
    """Stub priority ordering: returns first N from CANDIDATES (already arranged
    by leverage). Future: rank by (gap priority, novelty, source quality, etc.)."""
    return list(CANDIDATES.items())[:n]


def render_table(rows):
    """Markdown result table."""
    lines = ["| Candidate | Asset | Gap | n | PF | Net PnL | Max DD | Verdict |",
             "|---|---|---|---:|---:|---:|---:|---|"]
    for cid, info, m, v in rows:
        lines.append(f"| {cid} | {info['asset']} | {info['gap']} | {m['n']} | "
                     f"{m['pf']:.3f} | {m['net']:.0f} | {m['max_dd']:.0f} | {v} |")
    return "\n".join(lines)


def render_json(rows):
    return [{"candidate": cid, "asset": info["asset"], "gap": info["gap"],
             "metrics": m, "verdict": v} for cid, info, m, v in rows]


def main():
    ap = argparse.ArgumentParser(description="FQL Forge batch runner (dry-run / report-only)")
    ap.add_argument("--top", type=int, default=3, help="Top N candidates to run")
    ap.add_argument("--candidate", help="Run a specific candidate by id")
    ap.add_argument("--list-only", action="store_true", help="List available candidates and exit")
    ap.add_argument("--dry-run", action="store_true", help="No-op safety flag (everything is dry-run by design)")
    ap.add_argument("--output", help="Write result memo to path (default: docs/fql_forge/forge_batch_<date>.md)")
    ap.add_argument("--json", help="Write JSON results to path")
    args = ap.parse_args()

    if args.list_only:
        print("Available candidates:")
        for cid, info in CANDIDATES.items():
            print(f"  {cid}: {info['gap']} (asset={info['asset']}, archetype={info['archetype']})")
        return

    # Pick candidates to run
    if args.candidate:
        if args.candidate not in CANDIDATES:
            print(f"ERROR: candidate '{args.candidate}' not in registered set. Use --list-only to see available.")
            sys.exit(1)
        selection = [(args.candidate, CANDIDATES[args.candidate])]
    else:
        selection = _select_top(args.top)

    print(f"FQL Forge Batch Runner — {len(selection)} candidate(s) — DRY-RUN / REPORT-ONLY")
    print("=" * 78)

    rows = []
    for cid, info in selection:
        print(f"\n[{cid}] gap={info['gap']} asset={info['asset']}")
        try:
            m = info["runner"]()
            v = _verdict(m, info["archetype"])
            rows.append((cid, info, m, v))
            print(f"  trades={m['n']} PF={m['pf']:.3f} netPnL=${m['net']:.0f} maxDD=${m['max_dd']:.0f} median=${m['median']:.2f} → {v}")
        except Exception as e:
            print(f"  ERROR: {e}")
            m = _metrics(None, cid)
            rows.append((cid, info, m, "RETEST"))

    # Result table
    print("\n" + "=" * 78)
    print("BATCH RESULT")
    print("=" * 78)
    print(render_table(rows))

    # Verdict summary
    counts = {"PASS": 0, "WATCH": 0, "KILL": 0, "RETEST": 0}
    for _, _, _, v in rows:
        counts[v] = counts.get(v, 0) + 1
    print(f"\nSummary: {counts}")

    # Write artifacts
    out_md_path = args.output or (REPORTS_DIR / f"forge_batch_{date.today().isoformat()}.md")
    out_md_path = Path(out_md_path)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    md = (f"# FQL Forge Batch — {date.today().isoformat()}\n\n"
          f"**Filed by:** `research/fql_forge_batch_runner.py` (dry-run/report-only)\n"
          f"**Authority:** T1, no Lane A surfaces touched, no registry mutation.\n\n"
          f"## Result table\n\n"
          f"{render_table(rows)}\n\n"
          f"## Summary\n\n"
          f"{json.dumps(counts, indent=2)}\n\n"
          f"## Next-batch recommendation\n\n"
          f"PASS candidates → operator-review eligible for registry append (manual decision).\n"
          f"WATCH candidates → consider one bounded calibration follow-up.\n"
          f"KILL candidates → retire; record learning.\n"
          f"RETEST candidates → harness/data issue; investigate before re-running.\n")
    out_md_path.write_text(md)
    print(f"\nWrote: {out_md_path}")

    if args.json:
        Path(args.json).write_text(json.dumps(render_json(rows), indent=2, default=str))
        print(f"Wrote: {args.json}")

    # Safety affirmation
    print("\n[SAFETY] No registry mutation. No Lane A surfaces touched. Operator approves any append.")


if __name__ == "__main__":
    main()
