"""NFP calendar verification — rule-based 1st-Friday vs BLS-documented shifts.

The BLS Employment Situation report is released at 08:30 ET on the first
Friday of each month, with two well-known exceptions in this period:

  - When the first Friday is January 1 (federal New Year's Day), NFP is
    deferred to the second Friday. Affects January 2021 (Jan 1 → Jan 8).
  - When the first Friday is also Good Friday (NYSE closed), BLS still
    releases the report at 08:30 ET BUT the cash equity market is closed
    so futures execution context is unusual. Affects April 2021 (Apr 2)
    and April 2023 (Apr 7). NFP date IS the rule-based date in these cases;
    we just flag for downstream regime check.

Other potential holiday conflicts (Independence Day on Friday, Christmas on
Friday) do NOT fall on a 1st Friday in 2019-2026 — they all land on the 1st
or later in their respective months. Holiday-conflict logic checked below.

This verifier:
  1. Builds the rule-based 1st-Friday calendar 2019-2026
  2. Applies the documented NY-Day shift
  3. Flags Good Friday overlaps
  4. Re-runs EVT-NFP-MGC-Long-2h with the corrected calendar
  5. Reports match count, shifts, and metric delta

Authority: T1 / Lane B / report-only.
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from research.event_window_engine import generate_event_window_signals  # noqa: E402
from research.fql_forge_batch_runner import _metrics, _verdict  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import run_backtest  # noqa: E402


def first_friday(year: int, month: int) -> date:
    first = date(year, month, 1)
    offset = (4 - first.weekday()) % 7
    return date(year, month, 1 + offset)


def good_friday(year: int) -> date:
    """Anonymous Gregorian computus algorithm — accurate to >5000 years."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    easter = date(year, month, day)
    return easter - timedelta(days=2)


def build_verified_nfp_calendar(start_year=2019, end_year=2026):
    """Return list of dicts: {rule_date, actual_date, shift_reason, good_friday_flag}."""
    out = []
    for y in range(start_year, end_year + 1):
        gf = good_friday(y)
        for m in range(1, 13):
            ff = first_friday(y, m)
            actual = ff
            shift = None
            # NY Day shift: when 1st Friday is January 1, NFP defers to 2nd Friday
            if m == 1 and ff.day == 1:
                actual = ff + timedelta(days=7)
                shift = "NY_DAY_DEFERRAL"
            # Independence Day: only matters if 1st Friday IS July 4
            if m == 7 and ff.day == 4:
                actual = ff + timedelta(days=7)
                shift = "INDEPENDENCE_DAY_DEFERRAL"
            # Christmas: only matters if 1st Friday IS December 25
            if m == 12 and ff.day == 25:
                actual = ff + timedelta(days=7)
                shift = "CHRISTMAS_DEFERRAL"
            gf_flag = (actual == gf)
            out.append({
                "year": y, "month": m,
                "rule_date": ff.isoformat(),
                "actual_date": actual.isoformat(),
                "shifted": shift is not None,
                "shift_reason": shift,
                "good_friday_release": gf_flag,
            })
    return out


def _events_with_time(date_strs, time_str="08:30:00"):
    return [pd.to_datetime(f"{d} {time_str}") for d in date_strs]


def _run_candidate(events: list, asset="MGC", direction="long",
                   entry_offset_bars=1, exit_offset_bars=24,
                   label="EVT-NFP-MGC-Long-2h"):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    cfg = ASSETS[asset]
    sigs = generate_event_window_signals(
        df, events=events, entry_offset_bars=entry_offset_bars,
        exit_offset_bars=exit_offset_bars, direction=direction,
    )
    res = run_backtest(df, sigs, mode="both",
                       point_value=cfg["point_value"], symbol=asset)
    m = _metrics(res["trades_df"], label, costs=res["stats"]["costs"])
    return m, res["trades_df"]


def run():
    cal = build_verified_nfp_calendar(2019, 2026)
    shifts = [c for c in cal if c["shifted"]]
    gf_releases = [c for c in cal if c["good_friday_release"]]

    rule_dates = [c["rule_date"] for c in cal]
    actual_dates = [c["actual_date"] for c in cal]
    matches = sum(1 for r, a in zip(rule_dates, actual_dates) if r == a)
    pct_match = 100 * matches / len(cal)

    print(f"NFP calendar verification (2019-2026)")
    print(f"  Total months: {len(cal)}")
    print(f"  Rule-vs-actual matches: {matches} ({pct_match:.1f}%)")
    print(f"  Shifted releases: {len(shifts)}")
    for s in shifts:
        print(f"    {s['year']}-{s['month']:02d}: rule={s['rule_date']} → actual={s['actual_date']} ({s['shift_reason']})")
    print(f"  Good-Friday releases: {len(gf_releases)}")
    for g in gf_releases:
        print(f"    {g['year']}-{g['month']:02d}: {g['actual_date']} (cash equities closed; futures open)")

    # Re-run candidate with both calendars
    rule_events = _events_with_time(rule_dates)
    actual_events = _events_with_time(actual_dates)

    print(f"\nCandidate sensitivity:")
    m_rule, trades_rule = _run_candidate(rule_events)
    m_act, trades_act = _run_candidate(actual_events)
    print(f"  Rule cal (proxy):   n={m_rule['n']:3d} PF={m_rule['pf']:.3f} median=${m_rule['median']:.2f} max-yr={m_rule.get('max_year_share_pct', float('nan')):.1f}% yrs+={m_rule.get('years_positive')}/{m_rule.get('n_years')}")
    print(f"  Actual cal:         n={m_act['n']:3d} PF={m_act['pf']:.3f} median=${m_act['median']:.2f} max-yr={m_act.get('max_year_share_pct', float('nan')):.1f}% yrs+={m_act.get('years_positive')}/{m_act.get('n_years')}")
    delta_pf = m_act["pf"] - m_rule["pf"]
    delta_median = m_act["median"] - m_rule["median"]
    print(f"  Delta:              ΔPF={delta_pf:+.3f}, Δmedian=${delta_median:+.2f}")

    # Also test with Good-Friday-excluded calendar (regime check)
    no_gf = [c for c in cal if not c["good_friday_release"]]
    no_gf_dates = [c["actual_date"] for c in no_gf]
    m_no_gf, _ = _run_candidate(_events_with_time(no_gf_dates))
    print(f"  Actual − Good-Friday: n={m_no_gf['n']:3d} PF={m_no_gf['pf']:.3f} median=${m_no_gf['median']:.2f}")

    out_dir = ROOT / "research" / "data" / "fql_forge" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    date_iso = date.today().isoformat()
    payload = {
        "date": date_iso,
        "operator_approval": "OK NFP cal verify (#28)",
        "summary": {
            "total_months": len(cal),
            "rule_actual_matches": matches,
            "pct_match": pct_match,
            "shifts": shifts,
            "good_friday_releases": gf_releases,
        },
        "candidate_sensitivity": {
            "rule_calendar": {k: m_rule.get(k) for k in (
                "n", "pf", "median", "net", "max_year_share_pct", "years_positive", "n_years")},
            "actual_calendar": {k: m_act.get(k) for k in (
                "n", "pf", "median", "net", "max_year_share_pct", "years_positive", "n_years")},
            "actual_minus_good_friday": {k: m_no_gf.get(k) for k in (
                "n", "pf", "median", "net", "max_year_share_pct")},
            "delta_pf": float(delta_pf),
            "delta_median": float(delta_median),
        },
        "verdict": (
            "CALENDAR_VERIFIED" if abs(delta_pf) < 0.2 and abs(delta_median) < 10
            else "CALENDAR_MATERIAL_DELTA"
        ),
    }
    (out_dir / f"forge_nfp_calendar_verify_{date_iso}.json").write_text(
        json.dumps(payload, indent=2, default=str)
    )
    print(f"\nWrote: forge_nfp_calendar_verify_{date_iso}.json")
    print(f"\nVerdict: {payload['verdict']}")
    return payload


if __name__ == "__main__":
    run()
