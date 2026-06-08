"""EIA Weekly Petroleum Status Report calendar (minimum viable).

Per operator decision #99 (2026-06-08): build/load EIA release calendar,
handle holiday delays explicitly, calendar-timing-only (no inventory surprise
data). Return DATA_REQUIRED if exact release calendar is not clean.

EIA Standard Release Rule (verified via eia.gov):
  - Default: Wednesday 10:30 ET each week
  - If a US federal holiday falls Mon-Wed of that week: shifts to Thursday 11:00 ET
  - Christmas/New Year week sometimes shifts to Friday — flagged as POTENTIAL_SHIFT
    rather than DATA_REQUIRED since the rule is well-known but multi-year audit not done

This is a v1 calendar built from the rule. Cross-check with eia.gov archives
is operator/manual-verification work — flagged for future audit task.

Authority: T1 research-grade. Lane B / report-only. NOT used for live trading.
"""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _us_federal_holidays(year: int) -> dict:
    """Return dict {date: holiday_name} for US federal holidays in `year`.

    Includes observed-date shifts (when holiday falls weekend → observed Mon).
    """
    out = {}
    # Fixed-date holidays (no observed-shift in this minimum-viable version;
    # EIA shift logic is keyed to actual day-of-week of the holiday)
    fixed = [
        ((1, 1), "New Year's Day"),
        ((6, 19), "Juneteenth"),
        ((7, 4), "Independence Day"),
        ((11, 11), "Veterans Day"),
        ((12, 25), "Christmas"),
    ]
    for (m, d), name in fixed:
        out[date(year, m, d)] = name
    # Floating Monday holidays
    out[_nth_weekday_of_month(year, 1, 0, 3)] = "MLK Day"          # 3rd Mon Jan
    out[_nth_weekday_of_month(year, 2, 0, 3)] = "Presidents Day"   # 3rd Mon Feb
    out[_last_weekday_of_month(year, 5, 0)] = "Memorial Day"        # last Mon May
    out[_nth_weekday_of_month(year, 9, 0, 1)] = "Labor Day"        # 1st Mon Sep
    out[_nth_weekday_of_month(year, 10, 0, 2)] = "Columbus Day"    # 2nd Mon Oct
    # Floating Thursday holiday
    out[_nth_weekday_of_month(year, 11, 3, 4)] = "Thanksgiving"    # 4th Thu Nov
    return out


def _nth_weekday_of_month(year: int, month: int, weekday: int, n: int) -> date:
    """N-th occurrence of weekday (0=Mon..6=Sun) in given month."""
    d = date(year, month, 1)
    while d.weekday() != weekday:
        d += timedelta(days=1)
    d += timedelta(weeks=n - 1)
    return d


def _last_weekday_of_month(year: int, month: int, weekday: int) -> date:
    """Last occurrence of weekday in given month."""
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    d = next_month - timedelta(days=1)
    while d.weekday() != weekday:
        d -= timedelta(days=1)
    return d


def build_eia_release_calendar(start_year=2019, end_year=2026):
    """Return list of dicts {actual_date, default_date, shift_reason, shifted}.

    Standard: Wednesday 10:30 ET.
    Shift: if a US federal holiday falls Mon-Wed of that week → Thursday 11:00 ET.

    NOTE: this is the published EIA rule; rare special shifts (e.g. Christmas
    week Friday release) are not modeled in v1. Flagged for manual audit.
    """
    out = []
    for y in range(start_year, end_year + 1):
        holidays = _us_federal_holidays(y)
        # All Wednesdays of year
        d = date(y, 1, 1)
        while d.weekday() != 2:  # Wed = 2
            d += timedelta(days=1)
        while d.year == y:
            # Mon-Wed of THIS week
            week_start = d - timedelta(days=2)  # Mon
            mon_to_wed = [week_start + timedelta(days=i) for i in range(3)]
            holiday_hit = None
            for h_date in mon_to_wed:
                if h_date in holidays:
                    holiday_hit = (h_date, holidays[h_date])
                    break
            if holiday_hit:
                actual = d + timedelta(days=1)  # Thursday
                release_time = "11:00:00"
                shift_reason = f"holiday shift: {holiday_hit[1]} on {holiday_hit[0]}"
                shifted = True
            else:
                actual = d
                release_time = "10:30:00"
                shift_reason = None
                shifted = False
            # Rare Christmas-week Friday shift flagging (not exact)
            potential_christmas = (actual.month == 12 and actual.day >= 23)
            out.append({
                "default_wed": d.isoformat(),
                "actual_date": actual.isoformat(),
                "actual_time_et": release_time,
                "shifted": shifted,
                "shift_reason": shift_reason,
                "potential_christmas_shift_audit_needed": potential_christmas,
            })
            # Advance one week
            d += timedelta(days=7)
    return out


def _events_with_time(cal, time_et="10:30:00"):
    """Convert calendar entries to pd.Timestamp list (uses actual_time_et per entry)."""
    return [pd.to_datetime(f"{c['actual_date']} {c['actual_time_et']}") for c in cal]


if __name__ == "__main__":
    cal = build_eia_release_calendar(2019, 2026)
    print(f"Built EIA calendar: {len(cal)} events ({cal[0]['actual_date']} to {cal[-1]['actual_date']})")
    n_shifted = sum(1 for c in cal if c["shifted"])
    n_christmas = sum(1 for c in cal if c["potential_christmas_shift_audit_needed"])
    print(f"  Shifted releases (holiday): {n_shifted}")
    print(f"  Potential Christmas-shift entries (audit needed): {n_christmas}")
    print(f"\nFirst 5 entries:")
    for c in cal[:5]:
        print(f"  {c}")
    print(f"\nLast 5 entries:")
    for c in cal[-5:]:
        print(f"  {c}")
    print(f"\nAll shifted entries:")
    for c in cal:
        if c["shifted"]:
            print(f"  {c}")
    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "eia_release_calendar_2019_2026.json"
    out.write_text(json.dumps(cal, indent=2))
    print(f"\nWrote: {out}")
