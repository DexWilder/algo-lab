"""TradingView CSV Loader — normalizes TV chart exports to internal format.

Handles common TradingView export formats:
  - "time,open,high,low,close,Volume" (standard chart export)
  - "time,open,high,low,close" (no volume)
  - ISO timestamps, Unix timestamps, or "YYYY-MM-DD HH:MM" formats
  - BOM markers (UTF-8 BOM from Excel/TV exports)

Usage:
    python3 data/load_tv.py data/raw/MES_5m_TV.csv --symbol MES --timeframe 5m
    python3 data/load_tv.py --all   (processes all CSVs in data/raw/)

Output:
    data/processed/<SYMBOL>_5m.csv    (normalized OHLCV)
    data/processed/<SYMBOL>_5m.json   (dataset metadata)
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# Column name mapping — handles various TV export naming
COLUMN_MAP = {
    "time": "datetime",
    "date": "datetime",
    "datetime": "datetime",
    "date/time": "datetime",
    "timestamp": "datetime",
    "open": "open",
    "high": "high",
    "low": "low",
    "close": "close",
    "volume": "volume",
    "vol": "volume",
    "vol.": "volume",
}


def load_and_normalize(csv_path: Path, symbol: str, timeframe: str = "5m") -> pd.DataFrame:
    """Load a TradingView CSV and normalize to internal format.

    Returns DataFrame with columns: datetime, open, high, low, close, volume
    Sorted ascending by datetime, default integer index.
    """
    # Read with flexible encoding (TV sometimes adds BOM)
    df = pd.read_csv(csv_path, encoding="utf-8-sig")

    # Normalize column names
    df.columns = [c.strip().lower() for c in df.columns]
    rename = {}
    for col in df.columns:
        mapped = COLUMN_MAP.get(col)
        if mapped:
            rename[col] = mapped
    df.rename(columns=rename, inplace=True)

    # Validate required columns
    required = {"datetime", "open", "high", "low", "close"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}. Found: {list(df.columns)}")

    # Add volume if missing
    if "volume" not in df.columns:
        df["volume"] = 0

    # Parse datetime
    df["datetime"] = pd.to_datetime(df["datetime"])

    # Remove timezone info if present (store as naive — assumed US/Eastern from TV)
    if df["datetime"].dt.tz is not None:
        df["datetime"] = df["datetime"].dt.tz_localize(None)

    # Select and order columns
    df = df[["datetime", "open", "high", "low", "close", "volume"]].copy()

    # Sort ascending
    df.sort_values("datetime", inplace=True)
    df.reset_index(drop=True, inplace=True)

    # Drop exact duplicate timestamps (keep last)
    df.drop_duplicates(subset=["datetime"], keep="last", inplace=True)
    df.reset_index(drop=True, inplace=True)

    # Validate no NaN in OHLC
    nan_count = df[["open", "high", "low", "close"]].isna().sum().sum()
    if nan_count > 0:
        print(f"  WARNING: {nan_count} NaN values in OHLC — forward-filling")
        df[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]].ffill()

    return df


def save_processed(df: pd.DataFrame, symbol: str, timeframe: str = "5m") -> tuple[Path, Path]:
    """Save normalized DataFrame and metadata to processed directory."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    csv_path = PROCESSED_DIR / f"{symbol}_{timeframe}.csv"
    meta_path = PROCESSED_DIR / f"{symbol}_{timeframe}.json"

    # Save CSV
    df.to_csv(csv_path, index=False)

    # Save metadata
    meta = {
        "dataset_id": f"{symbol}_{timeframe}",
        "symbol": symbol,
        "timeframe": timeframe,
        "start_date": str(df["datetime"].iloc[0]),
        "end_date": str(df["datetime"].iloc[-1]),
        "bar_count": len(df),
        "trading_days": df["datetime"].dt.date.nunique(),
        "source": "tradingview",
        "source_file": csv_path.name,
        "processed_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)

    return csv_path, meta_path


def process_file(csv_path: Path, symbol: str, timeframe: str = "5m"):
    """Load, normalize, save, and report on a single TV CSV."""
    print(f"\n=== Processing {csv_path.name} → {symbol} {timeframe} ===")

    df = load_and_normalize(csv_path, symbol, timeframe)
    csv_out, meta_out = save_processed(df, symbol, timeframe)

    print(f"  Bars:    {len(df):,}")
    print(f"  Days:    {df['datetime'].dt.date.nunique()}")
    print(f"  Range:   {df['datetime'].iloc[0]} → {df['datetime'].iloc[-1]}")
    print(f"  Output:  {csv_out}")
    print(f"  Meta:    {meta_out}")

    return df


def process_all():
    """Process all CSV files in data/raw/."""
    raw_files = sorted(RAW_DIR.glob("*.csv"))
    if not raw_files:
        print(f"No CSV files found in {RAW_DIR}")
        print("Drop your TradingView exports there:")
        print("  MES_5m_TV.csv")
        print("  MNQ_5m_TV.csv")
        print("  MGC_5m_TV.csv")
        return

    # Auto-detect symbol from filename
    for f in raw_files:
        name = f.stem.upper()
        if "MES" in name:
            symbol = "MES"
        elif "MNQ" in name:
            symbol = "MNQ"
        elif "MGC" in name:
            symbol = "MGC"
        elif "ES" in name:
            symbol = "MES"
        elif "NQ" in name:
            symbol = "MNQ"
        elif "GC" in name:
            symbol = "MGC"
        elif "YM" in name:
            symbol = "YM"
        else:
            print(f"  SKIP: Can't detect symbol from filename '{f.name}'")
            continue

        process_file(f, symbol)


def main():
    parser = argparse.ArgumentParser(description="TradingView CSV Loader")
    parser.add_argument("csv_path", nargs="?", help="Path to TV CSV file")
    parser.add_argument("--symbol", default=None, help="Symbol (MES, MNQ, MGC)")
    parser.add_argument("--timeframe", default="5m", help="Timeframe (default: 5m)")
    parser.add_argument("--all", action="store_true", help="Process all CSVs in data/raw/")
    args = parser.parse_args()

    if args.all:
        process_all()
    elif args.csv_path:
        csv_path = Path(args.csv_path)
        if not csv_path.exists():
            print(f"ERROR: File not found: {csv_path}")
            sys.exit(1)
        symbol = args.symbol or csv_path.stem.split("_")[0].upper()
        process_file(csv_path, symbol, args.timeframe)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
