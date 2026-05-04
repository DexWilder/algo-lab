#!/usr/bin/env python3
"""Treasury-Rolldown-Carry-Spread — Monthly out-of-band execution.

Runs the 3-tenor ZN/ZF/ZB carry spread on its natural monthly cadence.
This strategy cannot run through the intraday forward runner because
that runner loads one asset per strategy; the spread needs all three
tenors simultaneously. See docs/PROBATION_REVIEW_CRITERIA.md §6 for
full context on the re-probation decision.

Invocation:
    python3 research/run_treasury_rolldown_spread.py             # live run
    python3 research/run_treasury_rolldown_spread.py --seed      # seed 2026-03 + 2026-04
    python3 research/run_treasury_rolldown_spread.py --dry-run   # compute but do not write
    python3 research/run_treasury_rolldown_spread.py --self-test # convention/year-wrap assertions

Convention (per docs/treasury_rolldown_date_mismatch_lane.md, 2026-05-04):
    spread_id = TRS-YYYY-MM where YYYY-MM is the HOLD month — the calendar
    month in which the position is held. The strategy rebalances on the
    last business day of the prior calendar month; this wrapper translates
    a rebalance_date in calendar month N into a spread_id for calendar
    month N+1, with explicit year-wrap (December → January).

Live run is idempotent:
    - Looks back to the prior calendar month for the latest unlogged
      strategy signal (the rebalance_date)
    - Skips if no eligible prior-month signal exists yet (data not refreshed
      OR strategy has not yet rebalanced for the prior month)
    - Skips by spread_id if this hold month's rebalance is already logged
    - Writes exactly one row per hold-month rebalance to
      logs/spread_rebalance_log.csv
"""

import argparse
import csv
import sys
from datetime import date, datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Reuse the strategy module — no duplication of the carry calculation.
from strategies.treasury_rolldown_carry.strategy import (  # noqa: E402
    generate_spread_signals,
)

STRATEGY_NAME = "Treasury-Rolldown-Carry-Spread"
SPREAD_LOG_PATH = ROOT / "logs" / "spread_rebalance_log.csv"

SCHEMA = [
    "rebalance_date",
    "strategy",
    "spread_id",
    "long_leg_asset",
    "long_leg_entry_price",
    "short_leg_asset",
    "short_leg_entry_price",
    "size_long",
    "size_short",
    "previous_long_leg_asset",
    "previous_short_leg_asset",
    "realized_pnl_prior_spread",
    "days_held_prior_spread",
    "notes",
]


# ── Date / id helpers ────────────────────────────────────────────────────────


def _spread_id(rebalance_date: date) -> str:
    """TRS-YYYY-MM where YYYY-MM is the HOLD month — the calendar month
    AFTER the rebalance opens. Explicit year-wrap: December → January.

    See docs/treasury_rolldown_date_mismatch_lane.md for convention.
    """
    if rebalance_date.month == 12:
        hold_year, hold_month = rebalance_date.year + 1, 1
    else:
        hold_year, hold_month = rebalance_date.year, rebalance_date.month + 1
    return f"TRS-{hold_year:04d}-{hold_month:02d}"


def _prior_calendar_month(execution_date: date) -> tuple[int, int]:
    """Return (year, month) of the calendar month before execution_date.
    Explicit year-wrap: January → previous-year December.
    """
    if execution_date.month == 1:
        return execution_date.year - 1, 12
    return execution_date.year, execution_date.month - 1


# ── Log I/O ──────────────────────────────────────────────────────────────────


def _ensure_log_header():
    if not SPREAD_LOG_PATH.exists():
        SPREAD_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(SPREAD_LOG_PATH, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=SCHEMA)
            writer.writeheader()


def _read_log() -> pd.DataFrame:
    _ensure_log_header()
    df = pd.read_csv(SPREAD_LOG_PATH)
    if not df.empty:
        df["rebalance_date"] = pd.to_datetime(df["rebalance_date"]).dt.date
    return df


def _already_logged(spread_id_value: str) -> bool:
    """Idempotency check by spread_id (the hold-month identifier)."""
    df = _read_log()
    if df.empty:
        return False
    return spread_id_value in set(df["spread_id"])


def _append_row(row: dict):
    """Append one row, atomic via tmp + replace."""
    _ensure_log_header()
    tmp = SPREAD_LOG_PATH.with_suffix(".csv.tmp")
    existing = SPREAD_LOG_PATH.read_text()
    with open(tmp, "w", newline="") as f:
        f.write(existing)
        writer = csv.DictWriter(f, fieldnames=SCHEMA)
        writer.writerow(row)
    tmp.replace(SPREAD_LOG_PATH)


# ── Rebalance construction ──────────────────────────────────────────────────


def _build_row(
    signals_row: pd.Series,
    prior_row: pd.Series | None,
    notes: str,
) -> dict:
    """Produce a log row from a signals_row (row of generate_spread_signals())
    and optionally a prior_row for realized PnL on the closed spread.

    signals_row.entry_date is the rebalance date we are opening on.
    prior_row.exit PnL = signals_row.entry prices for the prior spread's legs.

    The strategy module already computes long_pnl / short_pnl / spread_pnl
    from entry_date to exit_date. For realized_pnl_prior_spread we use
    the prior row's spread_pnl if available (since exit_date of row N is
    entry_date of row N+1).
    """
    rebal_date = pd.to_datetime(signals_row["entry_date"]).date()
    long_asset = signals_row["long_tenor"]
    short_asset = signals_row["short_tenor"]

    # Entry prices: pull from the strategy's aligned close frame.
    # We reconstruct quickly: generate_spread_signals doesn't expose the
    # close DataFrame directly, but it stored the entry prices implicitly
    # in the PnL calc. Re-derive by pulling the tenor's daily close at
    # entry_date.
    from strategies.treasury_rolldown_carry.strategy import _load_tenor_data

    long_daily = _load_tenor_data(long_asset).set_index("date")
    short_daily = _load_tenor_data(short_asset).set_index("date")
    long_entry_px = float(long_daily.loc[rebal_date, "close"])
    short_entry_px = float(short_daily.loc[rebal_date, "close"])

    if prior_row is not None:
        realized = float(prior_row["spread_pnl"])
        prior_long = str(prior_row["long_tenor"])
        prior_short = str(prior_row["short_tenor"])
        prior_entry = pd.to_datetime(prior_row["entry_date"]).date()
        days_held = (rebal_date - prior_entry).days
    else:
        realized = 0.0
        prior_long = ""
        prior_short = ""
        days_held = 0

    return {
        "rebalance_date": rebal_date.isoformat(),
        "strategy": STRATEGY_NAME,
        "spread_id": _spread_id(rebal_date),
        "long_leg_asset": long_asset,
        "long_leg_entry_price": round(long_entry_px, 6),
        "short_leg_asset": short_asset,
        "short_leg_entry_price": round(short_entry_px, 6),
        "size_long": 1,   # equal-notional, 1 contract per leg (validated baseline)
        "size_short": 1,
        "previous_long_leg_asset": prior_long,
        "previous_short_leg_asset": prior_short,
        "realized_pnl_prior_spread": round(realized, 2),
        "days_held_prior_spread": days_held,
        "notes": notes,
    }


# ── Main entry points ────────────────────────────────────────────────────────


def run_monthly_rebalance(execution_date: date | None = None, dry_run: bool = False) -> dict | None:
    """Compute and (optionally) log this hold month's rebalance if conditions are met.

    Per the Option-2 convention (docs/treasury_rolldown_date_mismatch_lane.md):
    spread_id = TRS-YYYY-MM is the HOLD month. The wrapper looks back to the
    PRIOR calendar month for the latest unlogged strategy signal (the
    rebalance_date) and writes one row per hold-month under that spread_id.

    Idempotency is by spread_id, not by rebalance_date month. Skip conditions:
        - No prior-month signal yet (data not refreshed OR strategy hasn't
          rebalanced for the prior month)
        - This hold month's spread_id already logged

    Returns the row written (or computed, if dry_run) or None if skipped.
    """
    if execution_date is None:
        execution_date = date.today()

    signals = generate_spread_signals()
    if signals.empty:
        print(f"[{execution_date}] No signals produced — strategy returned empty frame.")
        return None

    signals["entry_date"] = pd.to_datetime(signals["entry_date"]).dt.date

    prior_year, prior_month = _prior_calendar_month(execution_date)
    prior_month_signals = signals[
        signals["entry_date"].apply(
            lambda d: d.year == prior_year and d.month == prior_month
        )
    ]
    if prior_month_signals.empty:
        print(
            f"[{execution_date}] No prior-month signal "
            f"(looked for {prior_year}-{prior_month:02d}) — skip."
        )
        return None

    # Use the latest prior-month signal (typically the last business day of
    # that month — the strategy's natural rebalance point).
    signals_row = prior_month_signals.iloc[-1]
    rebalance_date = signals_row["entry_date"]
    spread_id_value = _spread_id(rebalance_date)

    if _already_logged(spread_id_value):
        print(
            f"[{execution_date}] {spread_id_value} already logged "
            f"(rebalance_date {rebalance_date}) — skip."
        )
        return None

    # Prior signal for realized PnL — the signal immediately before this one
    prior_signals = signals[signals["entry_date"] < rebalance_date]
    prior_row = prior_signals.iloc[-1] if not prior_signals.empty else None

    row = _build_row(signals_row, prior_row, notes="live_monthly_rebalance")

    if dry_run:
        print(f"[{execution_date}] DRY RUN — would write {spread_id_value}:")
        for k, v in row.items():
            print(f"  {k}: {v}")
        return row

    _append_row(row)
    print(
        f"[{execution_date}] Wrote {spread_id_value}: "
        f"long {row['long_leg_asset']} @ {row['long_leg_entry_price']}, "
        f"short {row['short_leg_asset']} @ {row['short_leg_entry_price']}"
    )
    return row


def _self_test():
    """Convention + year-wrap assertions for _spread_id and _prior_calendar_month.

    Required by the date-mismatch lane scope (acceptance criterion: explicit
    year-wrap validation). Run via --self-test CLI flag.
    """
    # _spread_id: rebalance_date → next-month spread_id
    assert _spread_id(date(2026, 4, 30)) == "TRS-2026-05", "April rebalance → May spread_id"
    assert _spread_id(date(2026, 11, 28)) == "TRS-2026-12", "November → December (no wrap)"
    assert _spread_id(date(2026, 1, 30)) == "TRS-2026-02", "January → February (no wrap)"
    assert _spread_id(date(2026, 12, 31)) == "TRS-2027-01", "December → January YEAR WRAP forward"
    assert _spread_id(date(2025, 12, 30)) == "TRS-2026-01", "Dec 2025 → Jan 2026 YEAR WRAP forward"

    # _prior_calendar_month: execution_date → prior (year, month)
    assert _prior_calendar_month(date(2026, 5, 1)) == (2026, 4), "May 1 → prior month April"
    assert _prior_calendar_month(date(2026, 1, 1)) == (2025, 12), "Jan 1 → prior month Dec prior year (YEAR WRAP)"
    assert _prior_calendar_month(date(2026, 1, 15)) == (2025, 12), "Jan 15 → prior month Dec prior year"
    assert _prior_calendar_month(date(2027, 1, 4)) == (2026, 12), "Jan 4 2027 → prior month Dec 2026"
    assert _prior_calendar_month(date(2026, 12, 1)) == (2026, 11), "Dec 1 → prior month November"

    print("_self_test: PASS (5 _spread_id + 5 _prior_calendar_month assertions, including year-wrap)")


def seed_history():
    """One-time: seed log with the 2026-03 and 2026-04 rebalances.

    Uses the strategy's full signal history and picks the most recent
    two rebalances whose entry_date falls in calendar months 2026-03
    and 2026-04. Each seed row is marked in notes so future readers
    know it was not produced by a live monthly invocation.
    """
    signals = generate_spread_signals()
    if signals.empty:
        print("No signals available — cannot seed.")
        return

    signals["entry_date"] = pd.to_datetime(signals["entry_date"]).dt.date
    target_months = [(2026, 3), (2026, 4)]

    log = _read_log()
    existing_ids = set(log["spread_id"]) if not log.empty else set()

    for year, month in target_months:
        month_rows = signals[
            signals["entry_date"].apply(lambda d: d.year == year and d.month == month)
        ]
        if month_rows.empty:
            print(f"No rebalance found in {year}-{month:02d} — skip.")
            continue
        signals_row = month_rows.iloc[-1]  # month-end rebalance

        sid = _spread_id(signals_row["entry_date"])
        if sid in existing_ids:
            print(f"{sid} already in log — skip.")
            continue

        prior_signals = signals[signals["entry_date"] < signals_row["entry_date"]]
        prior_row = prior_signals.iloc[-1] if not prior_signals.empty else None

        row = _build_row(
            signals_row,
            prior_row,
            notes="seeded_historical_entry_2026-04-14; not from live monthly invocation",
        )
        _append_row(row)
        existing_ids.add(sid)
        print(f"Seeded {sid}")


def main():
    parser = argparse.ArgumentParser(description="Treasury-Rolldown monthly runner")
    parser.add_argument("--seed", action="store_true", help="One-time seed of 2026-03 + 2026-04")
    parser.add_argument("--dry-run", action="store_true", help="Compute but do not write")
    parser.add_argument("--date", type=str, default=None, help="Override execution date (YYYY-MM-DD)")
    parser.add_argument("--self-test", action="store_true", help="Run convention + year-wrap assertions and exit")
    args = parser.parse_args()

    if args.self_test:
        _self_test()
        return

    if args.seed:
        seed_history()
        return

    exec_date = date.fromisoformat(args.date) if args.date else date.today()
    run_monthly_rebalance(execution_date=exec_date, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
