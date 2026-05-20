"""Data loading and results CSV I/O.

Per FQL evidence law (`feedback_evidence_integrity_failsafe.md`): any missing
assumption that can change a trading decision must fail closed. _make_row
raises InvalidMetrics if a required metric is absent or None — silent zero
substitution is forbidden.
"""

import csv
from pathlib import Path

import pandas as pd


class InvalidMetrics(ValueError):
    """Raised when a decision-grade metrics dict is missing required fields.

    Replaces the prior silent `.get(field, 0)` substitution path. A strategy
    result that lacks roi / max_drawdown / sharpe / expected_value / trades
    cannot be recorded — the result was either not computed or computed
    incorrectly, and a zero substitution would make broken evidence look
    clean (the failure mode locked out by Item #3.5 Site 1).
    """


RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
MASTER_CSV = RESULTS_DIR / "master.csv"
RANKED_CSV = RESULTS_DIR / "ranked.csv"

REQUIRED_COLUMNS = {"datetime", "open", "high", "low", "close", "volume"}

MASTER_FIELDS = ["name", "mode", "roi", "max_drawdown", "sharpe", "expected_value", "trades"]
RANKED_FIELDS = MASTER_FIELDS + ["score"]
REQUIRED_METRIC_FIELDS = ("roi", "max_drawdown", "sharpe", "expected_value", "trades")


def load_data(path: str | Path) -> pd.DataFrame:
    """Load and validate OHLCV data from a CSV file.

    Parameters
    ----------
    path : str or Path
        Path to the CSV file.

    Returns
    -------
    pd.DataFrame
        Validated OHLCV DataFrame with datetime column parsed.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.
    ValueError
        If the data fails validation checks.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")

    df = pd.read_csv(path)

    # Check required columns
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"Data file missing required columns: {missing}. "
            f"Expected: {REQUIRED_COLUMNS}. Got: {list(df.columns)}"
        )

    # Parse datetime
    df["datetime"] = pd.to_datetime(df["datetime"])

    # Check for NaN in OHLC
    ohlc = ["open", "high", "low", "close"]
    nan_counts = df[ohlc].isna().sum()
    if nan_counts.any():
        bad = nan_counts[nan_counts > 0].to_dict()
        raise ValueError(f"NaN values found in OHLC columns: {bad}")

    # Ensure sorted ascending
    if not df["datetime"].is_monotonic_increasing:
        df = df.sort_values("datetime").reset_index(drop=True)

    return df


def append_results(name: str, mode: str, metrics: dict) -> None:
    """Append or upsert a strategy result row to master.csv.

    Upserts by (name, mode) key so reruns are safe.
    """
    rows = []
    found = False

    if MASTER_CSV.exists() and MASTER_CSV.stat().st_size > 0:
        with open(MASTER_CSV, "r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["name"] == name and row["mode"] == mode:
                    # Upsert — replace with new metrics
                    row = _make_row(name, mode, metrics)
                    found = True
                rows.append(row)

    if not found:
        rows.append(_make_row(name, mode, metrics))

    with open(MASTER_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=MASTER_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def rebuild_ranked() -> None:
    """Rebuild ranked.csv from master.csv with computed scores."""
    from engine.scoring import compute_score

    if not MASTER_CSV.exists() or MASTER_CSV.stat().st_size == 0:
        return

    df = pd.read_csv(MASTER_CSV)
    if df.empty:
        return

    df["score"] = df.apply(
        lambda row: compute_score({
            "roi": float(row["roi"]),
            "max_drawdown": float(row["max_drawdown"]),
            "sharpe": float(row["sharpe"]),
            "expected_value": float(row["expected_value"]),
        }),
        axis=1,
    )

    df = df.sort_values("score", ascending=False).reset_index(drop=True)
    df.to_csv(RANKED_CSV, index=False, columns=RANKED_FIELDS)


def _make_row(name: str, mode: str, metrics: dict) -> dict:
    """Build a master.csv row from a metrics dict. Fail-closed on missing fields."""
    missing = [k for k in REQUIRED_METRIC_FIELDS if k not in metrics or metrics[k] is None]
    if missing:
        raise InvalidMetrics(
            f"Cannot record result for {name!r} (mode={mode!r}): missing "
            f"required metrics {missing}. All decision-grade metrics must be "
            f"explicitly present — silent zero substitution is forbidden per "
            f"FQL evidence law (CLAUDE.md)."
        )
    return {
        "name": name,
        "mode": mode,
        "roi": metrics["roi"],
        "max_drawdown": metrics["max_drawdown"],
        "sharpe": metrics["sharpe"],
        "expected_value": metrics["expected_value"],
        "trades": metrics["trades"],
    }
