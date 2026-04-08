#!/usr/bin/env python3
"""FQL Mass Screen — run batch_first_pass across all untested strategies.

Finds every strategy with code but no first_pass result and runs them
through the factory. Produces a consolidated ranking of all results.

Usage:
    python3 research/mass_screen.py                    # Run all untested
    python3 research/mass_screen.py --dry-run           # Show what would be tested
    python3 research/mass_screen.py --strategy foo      # Run one specific strategy
    python3 research/mass_screen.py --report            # Show results from prior run
"""

import argparse
import importlib
import json
import sys
import traceback
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

STRAT_DIR = ROOT / "strategies"
FIRST_PASS_DIR = ROOT / "research" / "data" / "first_pass"
SCREEN_RESULTS = ROOT / "research" / "data" / "mass_screen_results.json"

from engine.asset_config import get_asset, get_assets_by_status


def _is_broken(strategy_dir):
    """Check if a strategy has the BROKEN module flag."""
    path = strategy_dir / "strategy.py"
    try:
        with open(path) as f:
            content = f.read()
        # Simple static check — avoids importing broken modules
        return "\nBROKEN = True" in content or "^BROKEN = True" in content
    except Exception:
        return False


def find_untested():
    """Find strategies with code but no first_pass result.

    Skips strategies with the module-level BROKEN = True flag. These are
    known-broken and intentionally excluded from auto-testing until fixed.
    """
    has_first_pass = set()
    for f in FIRST_PASS_DIR.glob("*.json"):
        name = f.stem.split("_2026")[0].split("_2025")[0].split("_2024")[0]
        has_first_pass.add(name)

    untested = []
    skipped_broken = []
    for d in sorted(STRAT_DIR.iterdir()):
        if d.is_dir() and (d / "strategy.py").exists():
            if d.name in has_first_pass:
                continue
            if _is_broken(d):
                skipped_broken.append(d.name)
                continue
            untested.append(d.name)

    if skipped_broken:
        print(f"  Skipping {len(skipped_broken)} known-broken strategies: {skipped_broken}")

    return untested


def get_compatible_assets(strategy_name):
    """Determine which assets to test a strategy on based on its code."""
    strat_path = STRAT_DIR / strategy_name / "strategy.py"
    try:
        code = strat_path.read_text()
    except Exception:
        return []

    # Check for asset hints in the code
    code_lower = code.lower()

    # If strategy mentions specific assets, use those
    specific = []
    asset_hints = {
        "MCL": ["mcl", "crude", "oil", "cl_"],
        "MGC": ["mgc", "gold", "gc_"],
        "MES": ["mes", "spx", "spy", "s&p", "sp500"],
        "MNQ": ["mnq", "nasdaq", "nq_"],
        "M2K": ["m2k", "russell", "rut"],
        "ZN": ["zn_", " zn ", "treasury", "10y", "10-year"],
        "ZB": ["zb_", " zb ", "30y", "30-year", "bond"],
        "ZF": ["zf_", " zf ", "5y", "5-year"],
        "6J": ["6j", "yen", "jpy", "usdjpy"],
        "6E": ["6e", "euro", "eur", "eurusd"],
        "6B": ["6b", "pound", "gbp", "gbpusd"],
    }

    for asset, hints in asset_hints.items():
        if any(h in code_lower for h in hints):
            specific.append(asset)

    if specific:
        return specific

    # Generic strategy — test on core liquid assets
    return ["MES", "MNQ", "MGC", "M2K", "MCL", "ZN"]


def run_screen(strategies, dry_run=False):
    """Run batch_first_pass on each strategy."""
    from research.batch_first_pass import run_first_pass, load_data, get_asset
    from research.utils.atomic_io import atomic_write_json

    results = []
    total = len(strategies)

    for i, strat_name in enumerate(strategies, 1):
        assets = get_compatible_assets(strat_name)
        if not assets:
            print(f"  [{i}/{total}] {strat_name}: no compatible assets, skipping")
            continue

        if dry_run:
            print(f"  [{i}/{total}] {strat_name} -> {', '.join(assets)}")
            continue

        print(f"  [{i}/{total}] {strat_name} on {', '.join(assets)}...", end=" ", flush=True)

        try:
            report = run_first_pass(strat_name, assets)

            # Save individual first_pass result
            ts = datetime.now().strftime("%Y%m%d_%H%M")
            out_path = FIRST_PASS_DIR / f"{strat_name}_{ts}.json"
            atomic_write_json(out_path, report)

            classification = report.get("overall_classification", "ERROR")
            best = report.get("best_result", {})
            pf = best.get("pf", 0)
            trades = best.get("trades", 0)
            asset = best.get("asset", "?")

            print(f"{classification} (PF {pf:.2f}, {trades} trades on {asset})")

            results.append({
                "strategy": strat_name,
                "classification": classification,
                "best_pf": pf,
                "best_trades": trades,
                "best_asset": asset,
                "assets_tested": assets,
                "reasons": report.get("overall_reasons", []),
                "timestamp": ts,
            })

        except Exception as e:
            print(f"ERROR: {e}")
            results.append({
                "strategy": strat_name,
                "classification": "ERROR",
                "error": str(e),
                "best_pf": 0,
                "best_trades": 0,
                "best_asset": "?",
                "assets_tested": assets,
                "timestamp": datetime.now().strftime("%Y%m%d_%H%M"),
            })

    return results


def print_report(results):
    """Print consolidated ranking."""
    if not results:
        print("No results to report.")
        return

    # Sort by classification then PF
    order = {"ADVANCE": 0, "SALVAGE": 1, "MONITOR": 2, "REJECT": 3, "ERROR": 4}
    results.sort(key=lambda r: (order.get(r["classification"], 5), -r.get("best_pf", 0)))

    print()
    print("=" * 80)
    print("  FQL MASS SCREEN RESULTS")
    print("=" * 80)
    print()

    # Summary
    from collections import Counter
    counts = Counter(r["classification"] for r in results)
    print(f"  Total: {len(results)} strategies screened")
    for cls in ["ADVANCE", "SALVAGE", "MONITOR", "REJECT", "ERROR"]:
        if counts.get(cls, 0) > 0:
            print(f"  {cls:10s} {counts[cls]}")
    print()

    # Detail table
    print(f"  {'Strategy':<35s} {'Class':10s} {'PF':>6s} {'Trades':>7s} {'Asset':>6s}")
    print(f"  {'-'*35} {'-'*10} {'-'*6} {'-'*7} {'-'*6}")

    current_class = None
    for r in results:
        cls = r["classification"]
        if cls != current_class:
            if current_class is not None:
                print()
            current_class = cls

        pf_str = f"{r['best_pf']:.2f}" if r['best_pf'] else "?"
        trades_str = str(r.get('best_trades', '?'))
        print(f"  {r['strategy']:<35s} {cls:10s} {pf_str:>6s} {trades_str:>7s} {r.get('best_asset','?'):>6s}")

    # Highlight actionable results
    advances = [r for r in results if r["classification"] == "ADVANCE"]
    salvages = [r for r in results if r["classification"] == "SALVAGE"]

    if advances:
        print()
        print("  >> ADVANCE candidates ready for validation battery:")
        for r in advances:
            print(f"     {r['strategy']} (PF {r['best_pf']:.2f} on {r['best_asset']})")

    if salvages:
        print()
        print("  >> SALVAGE candidates worth a second look:")
        for r in salvages:
            reasons = "; ".join(r.get("reasons", []))
            print(f"     {r['strategy']} (PF {r['best_pf']:.2f} on {r['best_asset']}) — {reasons}")


def main():
    parser = argparse.ArgumentParser(description="FQL Mass Screen")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be tested")
    parser.add_argument("--strategy", type=str, help="Run one specific strategy")
    parser.add_argument("--report", action="store_true", help="Show results from prior run")
    args = parser.parse_args()

    if args.report:
        if SCREEN_RESULTS.exists():
            results = json.load(open(SCREEN_RESULTS))
            print_report(results)
        else:
            print("No prior screen results found. Run: python3 research/mass_screen.py")
        return

    if args.strategy:
        strategies = [args.strategy]
    else:
        strategies = find_untested()

    if not strategies:
        print("All strategies have been screened. Run with --report to see results.")
        return

    print(f"FQL Mass Screen: {len(strategies)} strategies to test")
    print()

    if args.dry_run:
        print("DRY RUN — no backtests will execute:")
        print()

    results = run_screen(strategies, dry_run=args.dry_run)

    if not args.dry_run and results:
        # Save consolidated results
        from research.utils.atomic_io import atomic_write_json

        # Merge with any existing results
        existing = []
        if SCREEN_RESULTS.exists():
            try:
                existing = json.load(open(SCREEN_RESULTS))
            except Exception:
                pass

        existing_names = {r["strategy"] for r in existing}
        for r in results:
            if r["strategy"] not in existing_names:
                existing.append(r)
            else:
                # Update existing
                existing = [e if e["strategy"] != r["strategy"] else r for e in existing]

        atomic_write_json(SCREEN_RESULTS, existing)
        print_report(existing)


if __name__ == "__main__":
    main()
