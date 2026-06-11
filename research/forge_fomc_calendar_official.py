"""FOMC scheduled meeting calendar, sourced from federalreserve.gov.

OFFICIAL Federal Reserve calendar (operator-verifiable). Verification fetched
2026-06-11 from:
  - https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm (2021-2026)
  - https://www.federalreserve.gov/monetarypolicy/fomchistorical2019.htm
  - https://www.federalreserve.gov/monetarypolicy/fomchistorical2020.htm

Statement release time: 2:00pm ET (14:00) on the second day of two-day meetings.

EXCLUDES emergency/unscheduled meetings (2019-10-04, 2020-03-03, 2020-03-15)
and 2025-08-22 notation vote for clean event-window analysis.

Each event is a (date_str, time_et_str, "scheduled") tuple, suitable for
event_window_engine.generate_event_window_signals.

This module is OFFICIAL_FED_GOV grade per the calendar verification doctrine
(unlike Forge-recall CPI calendar which is DATA_REQUIRED).
"""
from __future__ import annotations

from typing import List, Dict


def build_official_fomc_calendar() -> List[Dict]:
    """Return list of scheduled FOMC events 2019-01-30 through 2026-06-11.

    Each entry: {"actual_date": "YYYY-MM-DD", "actual_time_et": "14:00:00",
                 "type": "scheduled", "source": "federalreserve.gov"}
    """
    scheduled_dates = [
        # 2019 (8 scheduled; excludes 2019-10-04 emergency)
        "2019-01-30", "2019-03-20", "2019-05-01", "2019-06-19",
        "2019-07-31", "2019-09-18", "2019-10-30", "2019-12-11",
        # 2020 (7 scheduled; excludes 2020-03-03 and 2020-03-15 emergency)
        "2020-01-29", "2020-04-29", "2020-06-10", "2020-07-29",
        "2020-09-16", "2020-11-05", "2020-12-16",
        # 2021 (8 scheduled)
        "2021-01-27", "2021-03-17", "2021-04-28", "2021-06-16",
        "2021-07-28", "2021-09-22", "2021-11-03", "2021-12-15",
        # 2022 (8 scheduled)
        "2022-01-26", "2022-03-16", "2022-05-04", "2022-06-15",
        "2022-07-27", "2022-09-21", "2022-11-02", "2022-12-14",
        # 2023 (8 scheduled)
        "2023-02-01", "2023-03-22", "2023-05-03", "2023-06-14",
        "2023-07-26", "2023-09-20", "2023-11-01", "2023-12-13",
        # 2024 (8 scheduled)
        "2024-01-31", "2024-03-20", "2024-05-01", "2024-06-12",
        "2024-07-31", "2024-09-18", "2024-11-07", "2024-12-18",
        # 2025 (8 scheduled; excludes 2025-08-22 notation vote)
        "2025-01-29", "2025-03-19", "2025-05-07", "2025-06-18",
        "2025-07-30", "2025-09-17", "2025-10-29", "2025-12-10",
        # 2026 (3 scheduled before data cutoff 2026-06-08; Jun 17 just after)
        "2026-01-28", "2026-03-18", "2026-04-29",
    ]
    return [
        {
            "actual_date": d,
            "actual_time_et": "14:00:00",
            "type": "scheduled",
            "source": "federalreserve.gov",
        }
        for d in scheduled_dates
    ]


if __name__ == "__main__":
    cal = build_official_fomc_calendar()
    print(f"Total scheduled FOMC events (2019-2026 pre-2026-06-08): {len(cal)}")
    for c in cal:
        print(f"  {c['actual_date']} {c['actual_time_et']} ET")
