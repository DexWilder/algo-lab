"""
algo-lab pipeline runner.

Discovers strategies, runs generate_signals(), backtests, and ranks results.

Usage:
    python run_all.py                          # run all strategies
    python run_all.py --strategy sma-crossover # run one strategy
    python run_all.py --data_path data/MES_5m.csv --mode long
    python run_all.py --help
"""

import argparse
import importlib.util
import json
import sys
from pathlib import Path

# Ensure project root is on sys.path so `from engine.xxx import ...` works
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.io import load_data, append_results, rebuild_ranked
from engine.backtest import run_backtest
from engine.metrics import compute_metrics
from engine.scoring import compute_score

STRATEGIES_DIR = PROJECT_ROOT / "strategies"


def discover_strategies() -> list[dict]:
    """Scan strategies/ for directories containing meta.json."""
    strategies = []
    if not STRATEGIES_DIR.exists():
        return strategies

    for meta_path in sorted(STRATEGIES_DIR.glob("*/meta.json")):
        with open(meta_path) as f:
            meta = json.load(f)
        meta["_dir"] = meta_path.parent
        strategies.append(meta)

    return strategies


def load_strategy_module(strategy_dir: Path):
    """Dynamically import strategy.py from a strategy directory."""
    module_path = strategy_dir / "strategy.py"
    if not module_path.exists():
        return None

    spec = importlib.util.spec_from_file_location(
        f"strategy_{strategy_dir.name}", module_path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_pipeline(args: argparse.Namespace) -> None:
    """Main pipeline: discover -> signals -> backtest -> metrics -> rank."""
    strategies = discover_strategies()

    if not strategies:
        print("No strategies found in strategies/")
        return

    # Filter to single strategy if specified
    if args.strategy:
        strategies = [s for s in strategies if s["name"] == args.strategy]
        if not strategies:
            print(f"Strategy '{args.strategy}' not found.")
            return

    print(f"=== algo-lab pipeline ===")
    print(f"  Strategies found: {len(strategies)}")
    print(f"  Data path: {args.data_path}")
    print(f"  Mode: {args.mode}")
    print()

    # Load data
    try:
        df = load_data(args.data_path)
        print(f"  Data loaded: {len(df)} bars")
        print(f"  Range: {df['datetime'].iloc[0]} -> {df['datetime'].iloc[-1]}")
    except (FileNotFoundError, ValueError) as e:
        print(f"  Data error: {e}")
        print("  Fetch data first: python data/fetch_fmp.py --symbol MES --days 30")
        return
    print()

    for meta in strategies:
        name = meta["name"]
        strategy_dir = meta["_dir"]
        print(f"--- {name} ---")

        # Load strategy module
        module = load_strategy_module(strategy_dir)
        if module is None:
            print(f"  SKIP: No strategy.py found in {strategy_dir}")
            print()
            continue

        if not hasattr(module, "generate_signals"):
            print(f"  SKIP: strategy.py missing generate_signals() function")
            print()
            continue

        # Generate signals
        try:
            signals_df = module.generate_signals(df)
            signal_counts = signals_df["signal"].value_counts()
            print(f"  Signals generated:")
            print(f"    Long entries:  {signal_counts.get(1, 0)}")
            print(f"    Short entries: {signal_counts.get(-1, 0)}")
        except Exception as e:
            print(f"  ERROR in generate_signals(): {e}")
            print()
            continue

        # Backtest (Phase 2)
        try:
            result = run_backtest(df, signals_df, mode=args.mode)
            metrics = compute_metrics(result["trades_df"])
            score = compute_score(metrics)

            append_results(name, args.mode, metrics)
            print(f"  Metrics: {metrics}")
            print(f"  Score:   {score}")
        except NotImplementedError:
            print(f"  Backtest not yet implemented (Phase 2)")
            print(f"  Signal generation OK — strategy contract validated")

        print()

    # Rebuild rankings
    rebuild_ranked()
    print("Pipeline complete.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="algo-lab: strategy discovery, backtesting, and ranking pipeline"
    )
    parser.add_argument(
        "--data_path",
        default=str(PROJECT_ROOT / "data" / "MES_5m.csv"),
        help="Path to OHLCV data CSV (default: data/MES_5m.csv)",
    )
    parser.add_argument(
        "--mode",
        default="both",
        choices=["long", "short", "both"],
        help="Trading mode (default: both)",
    )
    parser.add_argument(
        "--strategy",
        default=None,
        help="Run a single strategy by name (default: run all)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force rerun even if results exist",
    )
    args = parser.parse_args()

    run_pipeline(args)


if __name__ == "__main__":
    main()
