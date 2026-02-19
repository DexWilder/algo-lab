"""Data loading and results CSV I/O."""

import csv
from pathlib import Path

import pandas as pd


RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
MASTER_CSV = RESULTS_DIR / "master.csv"
RANKED_CSV = RESULTS_DIR / "ranked.csv"

REQUIRED_COLUMNS = {"datetime", "open", "high", "low", "close", "volume"}

MASTER_FIELDS = ["name", "mode", "roi", "max_drawdown", "sharpe", "expected_value", "trades"]
RANKED_FIELDS = MASTER_FIELDS + ["score"]


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
    return {
        "name": name,
        "mode": mode,
        "roi": metrics.get("roi", 0),
        "max_drawdown": metrics.get("max_drawdown", 0),
        "sharpe": metrics.get("sharpe", 0),
        "expected_value": metrics.get("expected_value", 0),
        "trades": metrics.get("trades", 0),
    }
