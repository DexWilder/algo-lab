"""CPI release calendar (minimum viable).

Per operator decision #132 (proceed to CPI-MGC after bug-fix retries) and
#128 (metals-specific events permitted; clean calendar required).

CPI Standard Release Rule (BLS):
  - Default: 2nd Tuesday OR 2nd Wednesday of month, 8:30 ET
  - Historically the BLS publishes CPI for month M in the middle of month M+1
  - Day-of-week varies (Tuesday more common than Wednesday)
  - This calendar uses a simplified rule: "2nd Tuesday at 8:30 ET each month"
  - Some actual releases land on Wednesday or Thursday — flagged as AUDIT_REQUIRED

Authority: T1 research-grade. Lane B / report-only. NOT used for live trading.
Calendar is rule-based; cross-check with bls.gov for production use.
"""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _nth_weekday_of_month(year: int, month: int, weekday: int, n: int) -> date:
    """N-th occurrence of weekday (0=Mon..6=Sun) in given month."""
    d = date(year, month, 1)
    while d.weekday() != weekday:
        d += timedelta(days=1)
    d += timedelta(weeks=n - 1)
    return d


def build_cpi_release_calendar(start_year=2019, end_year=2026):
    """Return list of dicts {actual_date, rule_used, audit_required}.

    Standard: 2nd Tuesday of month, 8:30 ET.
    Audit required for: any month where actual BLS release deviated from rule.
    """
    out = []
    for y in range(start_year, end_year + 1):
        for m in range(1, 13):
            tuesday_2nd = _nth_weekday_of_month(y, m, 1, 2)  # Tuesday = 1
            out.append({
                "year": y,
                "month": m,
                "actual_date": tuesday_2nd.isoformat(),
                "actual_time_et": "08:30:00",
                "rule_used": "2nd Tuesday of month at 8:30 ET",
                "audit_required": True,
                "notes": "Rule-based; cross-check with bls.gov for production use",
            })
    return out


def _events_with_time(cal):
    """Convert calendar entries to pd.Timestamp list."""
    return [pd.to_datetime(f"{c['actual_date']} {c['actual_time_et']}") for c in cal]


if __name__ == "__main__":
    cal = build_cpi_release_calendar(2019, 2026)
    print(f"Built CPI calendar (rule-based): {len(cal)} events")
    print(f"  Date range: {cal[0]['actual_date']} to {cal[-1]['actual_date']}")
    print(f"  Audit required on all entries: {sum(1 for c in cal if c['audit_required'])}")
    print(f"\nFirst 6 entries:")
    for c in cal[:6]:
        print(f"  {c['actual_date']} {c['actual_time_et']} ({c['rule_used']})")
    print(f"\nLast 6 entries:")
    for c in cal[-6:]:
        print(f"  {c['actual_date']} {c['actual_time_et']}")
    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "cpi_release_calendar_2019_2026.json"
    out.write_text(json.dumps(cal, indent=2))
    print(f"\nWrote: {out}")
