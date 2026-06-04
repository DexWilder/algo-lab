"""Spec A — EVT-Treasury-Auction-Drift-Snap-ZN (Cheap-screen wire-up)

Per operator approval 2026-06-02 (build) + 2026-06-03 (wire). Uses the
event-window primitive (research/event_window_engine.py) + a minimum viable
Treasury 10-year-note auction calendar (2nd Wednesday of each month at
13:00 — a reasonable proxy for actual 10y/reopen auction timing without
overbuilding manual data ingestion).

Rule (simplified single-leg from harvest note 2026-05-29_15):
    LONG ZN at +1 bar after auction-result timestamp, exit 24 bars later
    (~2 hours). Tests the post-auction unwind / mean-reversion leg.

Output: writes report to docs/fql_forge/reports/forge_spec_a_<date>.{md,json}.

Authority: T1 / Lane B / report-only. No registry mutation.
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime, time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from research.event_window_engine import (  # noqa: E402
    generate_event_window_signals,
)
from research.fql_forge_batch_runner import _metrics, _verdict  # noqa: E402


def _second_wednesday(year: int, month: int) -> datetime:
    """Return the 2nd Wednesday of a given year/month at 13:00."""
    first = datetime(year, month, 1)
    # Day-of-week: Mon=0, Tue=1, Wed=2, ...
    days_to_first_wed = (2 - first.weekday()) % 7
    first_wed = first.replace(day=1 + days_to_first_wed)
    second_wed = first_wed.replace(day=first_wed.day + 7)
    return second_wed.replace(hour=13, minute=0)


def _build_auction_calendar(start_year=2019, end_year=2026):
    """Minimum-viable Treasury auction proxy: 2nd Wed/month at 13:00.

    Real auction calendar is a mix of original-issue (Feb/May/Aug/Nov) +
    reopenings (other months), typically on Tue or Wed. The 2nd-Wed proxy
    is consistent and produces ~12 events/year — sufficient for cheap-screen.
    """
    events = []
    for y in range(start_year, end_year + 1):
        for m in range(1, 13):
            events.append(_second_wednesday(y, m))
    return events


def run():
    df = pd.read_csv(ROOT / "data" / "processed" / "ZN_5m.csv")
    from engine.asset_config import ASSETS
    from engine.backtest import run_backtest
    cfg = ASSETS["ZN"]

    events = _build_auction_calendar(2019, 2026)
    print(f"Auction events: {len(events)} (2019-2026, 2nd Wed/month @ 13:00)")

    # Single-leg LONG post-auction reversion: +1 bar entry, +24 bars exit (~2h)
    sigs_long = generate_event_window_signals(
        df, events=events,
        entry_offset_bars=1, exit_offset_bars=24,
        direction="long",
    )
    res_long = run_backtest(df, sigs_long, mode="both",
                            point_value=cfg["point_value"], symbol="ZN")
    m_long = _metrics(res_long["trades_df"], "EVT-Treasury-Auction-LONG-ZN",
                      costs=res_long["stats"]["costs"])
    v_long = _verdict(m_long, "tail")

    # Single-leg SHORT pre-auction concession: -12 bar entry (1h before),
    # +12 bar exit (at the auction itself)
    sigs_short = generate_event_window_signals(
        df, events=events,
        entry_offset_bars=-12, exit_offset_bars=12,
        direction="short",
    )
    res_short = run_backtest(df, sigs_short, mode="both",
                             point_value=cfg["point_value"], symbol="ZN")
    m_short = _metrics(res_short["trades_df"], "EVT-Treasury-Auction-SHORT-ZN",
                       costs=res_short["stats"]["costs"])
    v_short = _verdict(m_short, "tail")

    out_dir = ROOT / "research" / "data" / "fql_forge" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    date_iso = date.today().isoformat()
    json_path = out_dir / f"forge_spec_a_{date_iso}.json"
    md_path = out_dir / f"forge_spec_a_{date_iso}.md"

    summary = {
        "long_leg": {
            "label": m_long["label"], "n": m_long["n"], "pf": m_long["pf"],
            "median": m_long["median"], "net": m_long["net"], "max_dd": m_long["max_dd"],
            "win_rate_pct": m_long.get("win_rate_pct"),
            "max_year_share_pct": m_long.get("max_year_share_pct"),
            "top3_share_pct": m_long.get("top3_share_pct"),
            "top10_share_pct": m_long.get("top10_share_pct"),
            "h1_pf": m_long.get("h1_pf"), "h2_pf": m_long.get("h2_pf"),
            "n_years": m_long.get("n_years"), "years_positive": m_long.get("years_positive"),
            "archetype": m_long.get("archetype"),
            "gate_verdict": m_long.get("gate_verdict"),
            "blocker_reason": m_long.get("blocker_reason"),
            "verdict": v_long,
        },
        "short_leg": {
            "label": m_short["label"], "n": m_short["n"], "pf": m_short["pf"],
            "median": m_short["median"], "net": m_short["net"], "max_dd": m_short["max_dd"],
            "win_rate_pct": m_short.get("win_rate_pct"),
            "max_year_share_pct": m_short.get("max_year_share_pct"),
            "top3_share_pct": m_short.get("top3_share_pct"),
            "top10_share_pct": m_short.get("top10_share_pct"),
            "h1_pf": m_short.get("h1_pf"), "h2_pf": m_short.get("h2_pf"),
            "n_years": m_short.get("n_years"), "years_positive": m_short.get("years_positive"),
            "archetype": m_short.get("archetype"),
            "gate_verdict": m_short.get("gate_verdict"),
            "blocker_reason": m_short.get("blocker_reason"),
            "verdict": v_short,
        },
        "calendar": "2nd Wednesday/month @ 13:00 (minimum viable Treasury 10y proxy)",
        "n_events_total": len(events),
        "cost_block": m_long.get("cost_block"),
    }
    json_path.write_text(json.dumps(summary, indent=2, default=str))

    md = (
        f"# FQL Forge — Spec A: EVT-Treasury-Auction-Drift-Snap-ZN\n\n"
        f"**Date:** {date_iso} • Mode: dry-run / report-only / Lane B\n"
        f"**Authority:** T1; no registry mutation; no Lane A touch\n"
        f"**Harness:** `research/event_window_engine.py` (built 2026-06-02; smoke-passed 2026-06-03)\n"
        f"**Calendar:** Minimum viable — 2nd Wednesday/month @ 13:00 ({len(events)} events 2019-2026).\n\n"
        f"## Rules tested\n\n"
        f"- **LONG leg** (post-auction reversion): entry +1 bar after event, exit +24 bars later (~2h hold)\n"
        f"- **SHORT leg** (pre-auction concession): entry -12 bars before event (~1h before), exit at event\n\n"
        f"## LONG leg result\n\n"
        f"| Field | Value |\n|---|---:|\n"
        f"| n | {m_long['n']} |\n| Net PF | {m_long['pf']:.3f} |\n"
        f"| Median | ${m_long['median']:.2f} |\n| Net PnL | ${m_long['net']:.0f} |\n"
        f"| Max DD | ${m_long['max_dd']:.0f} |\n"
        f"| Win rate | {m_long.get('win_rate_pct', float('nan')):.1f}% |\n"
        f"| Max-year share | {m_long.get('max_year_share_pct', float('nan')):.1f}% |\n"
        f"| Top-3 | {m_long.get('top3_share_pct', float('nan')):.1f}% |\n"
        f"| Top-10 | {m_long.get('top10_share_pct', float('nan')):.1f}% |\n"
        f"| H1 / H2 PF | {m_long.get('h1_pf', float('nan')):.3f} / {m_long.get('h2_pf', float('nan')):.3f} |\n"
        f"| Years+ | {m_long.get('years_positive', '?')}/{m_long.get('n_years', '?')} |\n"
        f"| Archetype | {m_long.get('archetype')} | gate | {m_long.get('gate_verdict')} |\n"
        f"| **Verdict** | **{v_long}** |\n\n"
        f"## SHORT leg result\n\n"
        f"| Field | Value |\n|---|---:|\n"
        f"| n | {m_short['n']} |\n| Net PF | {m_short['pf']:.3f} |\n"
        f"| Median | ${m_short['median']:.2f} |\n| Net PnL | ${m_short['net']:.0f} |\n"
        f"| Max DD | ${m_short['max_dd']:.0f} |\n"
        f"| Win rate | {m_short.get('win_rate_pct', float('nan')):.1f}% |\n"
        f"| Max-year share | {m_short.get('max_year_share_pct', float('nan')):.1f}% |\n"
        f"| Top-3 | {m_short.get('top3_share_pct', float('nan')):.1f}% |\n"
        f"| Top-10 | {m_short.get('top10_share_pct', float('nan')):.1f}% |\n"
        f"| H1 / H2 PF | {m_short.get('h1_pf', float('nan')):.3f} / {m_short.get('h2_pf', float('nan')):.3f} |\n"
        f"| Years+ | {m_short.get('years_positive', '?')}/{m_short.get('n_years', '?')} |\n"
        f"| Archetype | {m_short.get('archetype')} | gate | {m_short.get('gate_verdict')} |\n"
        f"| **Verdict** | **{v_short}** |\n\n"
        f"## Safety\n\n"
        f"- No registry mutation • no Lane A touch • no scheduler change\n"
        f"- Calendar is a 2nd-Wed proxy; not a real auction calendar. Refine to actual auction\n"
        f"  dates (treasurydirect.gov) only if cheap-screen verdict warrants deeper screen.\n"
    )
    md_path.write_text(md)
    print(f"Wrote: {json_path}")
    print(f"Wrote: {md_path}")
    print(f"\n[LONG]  n={m_long['n']:3d} PF={m_long['pf']:.3f} median=${m_long['median']:.2f} max-yr={m_long.get('max_year_share_pct', float('nan')):.1f}% → {v_long}")
    print(f"[SHORT] n={m_short['n']:3d} PF={m_short['pf']:.3f} median=${m_short['median']:.2f} max-yr={m_short.get('max_year_share_pct', float('nan')):.1f}% → {v_short}")
    return summary


if __name__ == "__main__":
    run()
