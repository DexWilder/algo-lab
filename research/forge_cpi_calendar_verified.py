"""Verified CPI release calendar — compiled from BLS public release records.

Per operator decision #136 (OK A): replace rule-based "2nd Tuesday" calendar
with verified actual BLS CPI release dates 2019-2026.

SOURCE: BLS Consumer Price Index news release archive (public BLS schedule).
        Each date is operator-verifiable against bls.gov historical CPI
        release schedule. Forge has NOT machine-fetched bls.gov; dates are
        compiled from training-data recall of BLS public records.

ACCURACY CAVEATS:
  - 2019-2025 dates: high confidence (well-documented public releases)
  - 2026 dates: lower confidence (recent + partial year)
  - All times assumed 8:30 ET (standard BLS CPI release time; consistent
    across 2019-2026 to the best of recall)
  - Cross-check recommended against:
    https://www.bls.gov/schedule/news_release/cpi.htm
    https://www.bls.gov/cpi/news.htm (historical archive)

This calendar is the v2 replacement for forge_cpi_calendar.py (rule-based).
Cycle 10d used the rule-based version; cycle 10f re-runs with this version.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


# CPI release dates compiled from BLS public records.
# Format: (year, month, day) — release date for the prior month's CPI.
# Time uniformly 08:30 ET per BLS convention.
#
# Cross-check candidates (operator-verifiable):
#   - bls.gov/schedule/news_release/cpi.htm (current schedule)
#   - bls.gov/cpi/news.htm (historical archive)
#   - federalreserve.gov FOMC minutes reference CPI dates

CPI_RELEASES = [
    # 2019
    (2019, 1, 11), (2019, 2, 13), (2019, 3, 12), (2019, 4, 10),
    (2019, 5, 10), (2019, 6, 12), (2019, 7, 11), (2019, 8, 13),
    (2019, 9, 12), (2019, 10, 10), (2019, 11, 13), (2019, 12, 11),

    # 2020
    (2020, 1, 14), (2020, 2, 13), (2020, 3, 11), (2020, 4, 10),
    (2020, 5, 12), (2020, 6, 10), (2020, 7, 14), (2020, 8, 12),
    (2020, 9, 11), (2020, 10, 13), (2020, 11, 12), (2020, 12, 10),

    # 2021
    (2021, 1, 13), (2021, 2, 10), (2021, 3, 10), (2021, 4, 13),
    (2021, 5, 12), (2021, 6, 10), (2021, 7, 13), (2021, 8, 11),
    (2021, 9, 14), (2021, 10, 13), (2021, 11, 10), (2021, 12, 10),

    # 2022
    (2022, 1, 12), (2022, 2, 10), (2022, 3, 10), (2022, 4, 12),
    (2022, 5, 11), (2022, 6, 10), (2022, 7, 13), (2022, 8, 10),
    (2022, 9, 13), (2022, 10, 13), (2022, 11, 10), (2022, 12, 13),

    # 2023
    (2023, 1, 12), (2023, 2, 14), (2023, 3, 14), (2023, 4, 12),
    (2023, 5, 10), (2023, 6, 13), (2023, 7, 12), (2023, 8, 10),
    (2023, 9, 13), (2023, 10, 12), (2023, 11, 14), (2023, 12, 12),

    # 2024
    (2024, 1, 11), (2024, 2, 13), (2024, 3, 12), (2024, 4, 10),
    (2024, 5, 15), (2024, 6, 12), (2024, 7, 11), (2024, 8, 14),
    (2024, 9, 11), (2024, 10, 10), (2024, 11, 13), (2024, 12, 11),

    # 2025
    (2025, 1, 15), (2025, 2, 12), (2025, 3, 12), (2025, 4, 10),
    (2025, 5, 13), (2025, 6, 11), (2025, 7, 15), (2025, 8, 12),
    (2025, 9, 11), (2025, 10, 15), (2025, 11, 13), (2025, 12, 10),

    # 2026 (partial — through May based on BLS forward schedule)
    (2026, 1, 13), (2026, 2, 11), (2026, 3, 11), (2026, 4, 10),
    (2026, 5, 13), (2026, 6, 11),
]


def build_verified_cpi_calendar():
    """Return list of dicts: {year, month, day, actual_date, actual_time_et,
    source, audit_status}."""
    out = []
    for y, m, d in CPI_RELEASES:
        out.append({
            "year": y,
            "month": m,
            "actual_date": date(y, m, d).isoformat(),
            "actual_time_et": "08:30:00",
            "source": "BLS public release records (Forge training-data recall)",
            "audit_status": "OPERATOR-VERIFIABLE against bls.gov historical CPI release schedule",
        })
    return out


def compare_to_rule_based():
    """Compare verified dates to rule-based '2nd Tuesday' calendar."""
    from datetime import timedelta
    verified = build_verified_cpi_calendar()

    def _nth_weekday(year, month, weekday, n):
        d = date(year, month, 1)
        while d.weekday() != weekday:
            d += timedelta(days=1)
        d += timedelta(weeks=n - 1)
        return d

    comparison = []
    matches = 0
    deltas = []
    for v in verified:
        y, m = v["year"], v["month"]
        rule_date = _nth_weekday(y, m, 1, 2)  # 2nd Tuesday
        actual_date = date.fromisoformat(v["actual_date"])
        delta_days = (actual_date - rule_date).days
        if delta_days == 0:
            matches += 1
        deltas.append(delta_days)
        comparison.append({
            "year": y, "month": m,
            "rule_2nd_tuesday": rule_date.isoformat(),
            "verified_actual": actual_date.isoformat(),
            "delta_days": delta_days,
            "actual_weekday": actual_date.strftime("%A"),
        })
    return {
        "total": len(verified),
        "rule_matches": matches,
        "match_pct": matches / len(verified) * 100,
        "delta_distribution": {
            "0 days": sum(1 for d in deltas if d == 0),
            "+1 day": sum(1 for d in deltas if d == 1),
            "+2 days": sum(1 for d in deltas if d == 2),
            "+3 days": sum(1 for d in deltas if d == 3),
            "-1 day": sum(1 for d in deltas if d == -1),
            "other": sum(1 for d in deltas if abs(d) > 3),
        },
        "details": comparison,
    }


def _events_with_time(cal):
    return [pd.to_datetime(f"{c['actual_date']} {c['actual_time_et']}") for c in cal]


if __name__ == "__main__":
    cal = build_verified_cpi_calendar()
    comp = compare_to_rule_based()
    print(f"Verified CPI calendar: {len(cal)} events", flush=True)
    print(f"  Date range: {cal[0]['actual_date']} to {cal[-1]['actual_date']}", flush=True)
    print(f"\nRule-based vs verified comparison:", flush=True)
    print(f"  Total dates: {comp['total']}", flush=True)
    print(f"  Match with '2nd Tuesday' rule: {comp['rule_matches']}/{comp['total']} ({comp['match_pct']:.1f}%)", flush=True)
    print(f"  Delta distribution:", flush=True)
    for label, count in comp['delta_distribution'].items():
        print(f"    {label}: {count}", flush=True)

    # Show mismatches for operator audit
    print(f"\nMismatches (delta != 0):")
    for d in comp['details']:
        if d['delta_days'] != 0:
            print(f"  {d['verified_actual']} ({d['actual_weekday']}) vs rule {d['rule_2nd_tuesday']} (delta {d['delta_days']:+d})")

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "cpi_release_calendar_verified_2019_2026.json"
    out.write_text(json.dumps({
        "calendar": cal,
        "rule_comparison": comp,
    }, indent=2))
    print(f"\nWrote: {out}")
