"""
FMP data fetcher for MES (Micro E-mini S&P 500) 5-minute intraday data.

Fetches historical intraday candles from Financial Modeling Prep API and
saves them in the data contract format.

Usage:
    python data/fetch_fmp.py --symbol MES --days 30
    python data/fetch_fmp.py --symbol ES --days 60 --output data/ES_5m.csv
"""

import argparse
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

load_dotenv(PROJECT_ROOT / ".env")

FMP_API_KEY = os.getenv("FMP_API_KEY", "")
FMP_BASE_URL = "https://financialmodelingprep.com/stable"

MAX_RETRIES = 3
BACKOFF_BASE = 2  # seconds


# ---------------------------------------------------------------------------
# Core API fetch
# ---------------------------------------------------------------------------


def fetch_5m_candles(
    symbol: str,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """Fetch 5-minute candles from FMP.

    Parameters
    ----------
    symbol : str
        Ticker symbol, e.g. "MES" or "ES".
    start_date, end_date : str
        ISO date strings "YYYY-MM-DD".

    Returns
    -------
    pd.DataFrame
        Columns: datetime, open, high, low, close, volume. Sorted ascending.
    """
    if not FMP_API_KEY or FMP_API_KEY == "your_fmp_api_key_here":
        print("ERROR: FMP_API_KEY not set. Add a valid key to .env in the project root.")
        sys.exit(1)

    url = f"{FMP_BASE_URL}/historical-chart/5min"
    params = {
        "symbol": symbol,
        "from": start_date,
        "to": end_date,
        "apikey": FMP_API_KEY,
    }

    data = _fetch_with_retries(url, params)

    if not data:
        print(f"WARNING: No data returned for {symbol} ({start_date} to {end_date})")
        return pd.DataFrame(columns=["datetime", "open", "high", "low", "close", "volume"])

    df = pd.DataFrame(data)

    # Normalize column names
    col_map = {}
    for col in df.columns:
        lower = col.lower()
        if lower in ("date", "datetime"):
            col_map[col] = "datetime"
        elif lower == "open":
            col_map[col] = "open"
        elif lower == "high":
            col_map[col] = "high"
        elif lower == "low":
            col_map[col] = "low"
        elif lower == "close":
            col_map[col] = "close"
        elif lower == "volume":
            col_map[col] = "volume"
    df.rename(columns=col_map, inplace=True)

    required = {"datetime", "open", "high", "low", "close", "volume"}
    missing = required - set(df.columns)
    if missing:
        print(f"WARNING: Missing columns from API response: {missing}")
        for col in missing:
            df[col] = 0

    df = df[["datetime", "open", "high", "low", "close", "volume"]].copy()
    df["datetime"] = pd.to_datetime(df["datetime"])
    df.sort_values("datetime", inplace=True)
    df.reset_index(drop=True, inplace=True)

    return df


def _fetch_with_retries(url: str, params: dict) -> list:
    """GET with retries and exponential backoff."""
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            payload = resp.json()
            if isinstance(payload, list):
                return payload
            if isinstance(payload, dict) and "historical" in payload:
                return payload["historical"]
            print(f"WARNING: Unexpected API response shape: {type(payload)}")
            return []
        except (requests.RequestException, ValueError) as exc:
            last_err = exc
            wait = BACKOFF_BASE ** attempt
            print(f"  [RETRY {attempt}/{MAX_RETRIES}] {exc!r} — retrying in {wait}s ...")
            time.sleep(wait)

    raise RuntimeError(
        f"FMP API request failed after {MAX_RETRIES} attempts: {last_err}"
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch MES/ES 5-minute intraday data from FMP."
    )
    parser.add_argument(
        "--symbol",
        default="MES",
        help="Symbol to fetch (default: MES)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days of history to fetch (default: 30)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output CSV path (default: data/<SYMBOL>_5m.csv)",
    )
    args = parser.parse_args()

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")

    output_path = Path(args.output) if args.output else DATA_DIR / f"{args.symbol}_5m.csv"

    print(f"=== FMP Fetcher: {args.symbol} 5m ===")
    print(f"    Date range : {start_date} -> {end_date}")
    print(f"    Output     : {output_path}")
    print()

    df = fetch_5m_candles(args.symbol, start_date, end_date)

    if df.empty:
        print("No data fetched. Check your symbol and API key.")
        sys.exit(1)

    df.to_csv(output_path, index=False)
    print(f"Saved {len(df)} candles to {output_path}")
    print(f"  First: {df.iloc[0]['datetime']}")
    print(f"  Last:  {df.iloc[-1]['datetime']}")


if __name__ == "__main__":
    main()
