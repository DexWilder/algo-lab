"""FQL Forge — Fundamentals Cache (v1, research-layer only)

Local monthly-frequency cache for macro / fundamentals series used by VALUE,
CARRY, and event candidates. Series live as individual JSON files under
`research/data/fundamentals/`, each with a metadata header and a `values`
dict (ISO-date string → float). Helpers load series into pandas, check
coverage, and emit a missing-data report.

**Authority:** T1 — research-layer only. Never imported by execution code
(`engine/`, `run_forward_paper.py`, etc.). The runner does not call this.

**Scope (locked 2026-06-03):**
- Local file cache, not a live API client
- Monthly frequency (most macro series are monthly anyway)
- Manually refreshable; no scheduled fetch
- Supports: 10y real yield, broad USD, ACM term premium, S&P earnings yield,
  Fed Funds effective, BoJ policy rate
- Hardcoded canonical bootstrap values for cheap-screen use; live FRED/BoJ
  ingest gated on separate operator approval
- Missing-data report: lists which months are missing per series

Not in scope here:
- Live API access (FRED, BoJ, NY Fed) — defer to "live ingest" approval
- Daily or higher-frequency series — out of scope; monthly only
- Cross-series alignment / interpolation — caller's responsibility
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from typing import Iterable

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
CACHE_DIR = ROOT / "research" / "data" / "fundamentals"


# ─────────────────────────────────────────────────────────────────────────────
# Series registry
# ─────────────────────────────────────────────────────────────────────────────

SERIES_REGISTRY = {
    "real_yield_10y": {
        "fred_id": "REAINTRATREARAT10Y",
        "description": "10y US real interest rate (TIPS yield), monthly end-of-month, percent",
        "source": "FRED",
        "frequency": "M",
        "unit": "percent",
    },
    "usd_broad": {
        "fred_id": "DTWEXBGS",
        "description": "Broad trade-weighted US dollar index, monthly end-of-month",
        "source": "FRED",
        "frequency": "M",
        "unit": "index_level",
    },
    "acm_term_premium_10y": {
        "fred_id": "THREEFYTP10",
        "description": "ACM model 10y Treasury term premium, monthly, decimal",
        "source": "NY Fed / FRED",
        "frequency": "M",
        "unit": "decimal",
    },
    "sp500_earnings_yield": {
        "fred_id": None,
        "description": "S&P 500 forward earnings yield (1 / forward P/E), monthly, decimal",
        "source": "Shiller / WSJ / proxy",
        "frequency": "M",
        "unit": "decimal",
    },
    "fed_funds_effective": {
        "fred_id": "FEDFUNDS",
        "description": "Effective Federal Funds rate, monthly average, percent",
        "source": "FRED",
        "frequency": "M",
        "unit": "percent",
    },
    "boj_policy_rate": {
        "fred_id": None,
        "description": "BoJ policy rate / basic loan rate, monthly, percent",
        "source": "BoJ / OECD / FRED proxy",
        "frequency": "M",
        "unit": "percent",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# I/O
# ─────────────────────────────────────────────────────────────────────────────

def _path_for(name: str) -> Path:
    return CACHE_DIR / f"{name}.json"


def write_series(name: str, values: dict, source_note: str = "manual bootstrap",
                 overwrite: bool = False) -> Path:
    """Write/refresh a series file with metadata + values dict."""
    if name not in SERIES_REGISTRY:
        raise KeyError(f"series {name!r} not registered; add to SERIES_REGISTRY first")
    p = _path_for(name)
    if p.exists() and not overwrite:
        raise FileExistsError(f"{p} exists — pass overwrite=True to replace")
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    meta = SERIES_REGISTRY[name].copy()
    meta.update({
        "name": name,
        "written": date.today().isoformat(),
        "source_note": source_note,
        "n_obs": len(values),
        "values": {str(k): float(v) for k, v in sorted(values.items())},
    })
    p.write_text(json.dumps(meta, indent=2))
    return p


def load_series(name: str) -> pd.Series:
    """Load a series as pd.Series indexed by month-end Timestamp."""
    p = _path_for(name)
    if not p.exists():
        raise FileNotFoundError(f"{p} — series {name!r} not in cache")
    data = json.loads(p.read_text())
    s = pd.Series({pd.to_datetime(k): v for k, v in data["values"].items()},
                  name=name)
    return s.sort_index()


def list_cached() -> list[str]:
    if not CACHE_DIR.exists():
        return []
    return sorted(p.stem for p in CACHE_DIR.glob("*.json"))


# ─────────────────────────────────────────────────────────────────────────────
# Missing-data report
# ─────────────────────────────────────────────────────────────────────────────

def missing_data_report(min_start: str = "2019-01-31",
                        max_end: str | None = None) -> dict:
    """Scan registry + cache; report which series are missing months."""
    if max_end is None:
        max_end = date.today().isoformat()
    expected_months = pd.date_range(min_start, max_end, freq="ME")
    cached = set(list_cached())

    report = {
        "checked": date.today().isoformat(),
        "min_start": min_start,
        "max_end": max_end,
        "expected_months_total": len(expected_months),
        "series": {},
    }
    for name in SERIES_REGISTRY:
        entry = {
            "in_cache": name in cached,
            "missing_months": [],
            "coverage_pct": 0.0,
        }
        if name in cached:
            try:
                s = load_series(name)
                present = set(s.index.normalize())
                missing = [str(d.date()) for d in expected_months if d.normalize() not in present]
                entry["missing_months"] = missing[:6]  # truncate for readability
                entry["missing_count"] = len(missing)
                entry["coverage_pct"] = 100.0 * (len(expected_months) - len(missing)) / len(expected_months)
            except Exception as e:
                entry["error"] = str(e)
        report["series"][name] = entry
    return report


# ─────────────────────────────────────────────────────────────────────────────
# Bootstrap from V1 / Spec C hardcoded values (preserve the work already done)
# ─────────────────────────────────────────────────────────────────────────────

def bootstrap_from_existing(overwrite: bool = True) -> dict:
    """Seed the cache from the hardcoded values already in V1 + Spec C scripts.
    Idempotent if overwrite=True. Returns per-series write status.
    """
    from research.forge_spec_c_6j_carry_screen import FED_FUNDS, BOJ_RATE
    from research.forge_v1_gold_realrate_screen import REAL_YIELD_10Y, USD_BROAD

    results = {}
    for name, vals in (
        ("real_yield_10y", REAL_YIELD_10Y),
        ("usd_broad", USD_BROAD),
        ("fed_funds_effective", FED_FUNDS),
        ("boj_policy_rate", BOJ_RATE),
    ):
        try:
            p = write_series(name, vals,
                             source_note="bootstrap from V1/Spec C hardcoded values",
                             overwrite=overwrite)
            results[name] = {"status": "written", "path": str(p), "n": len(vals)}
        except Exception as e:
            results[name] = {"status": "error", "error": str(e)}
    return results


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def _print_report(rep: dict):
    print(f"Fundamentals cache check — {rep['checked']}")
    print(f"  expected months: {rep['expected_months_total']} "
          f"({rep['min_start']} → {rep['max_end']})")
    print(f"  series in registry: {len(SERIES_REGISTRY)}")
    print(f"  series in cache: {sum(1 for s in rep['series'].values() if s['in_cache'])}")
    print()
    print(f"  {'series':28s} {'cached':>7s} {'cov%':>6s} {'missing':>8s}  sample_missing")
    for name, e in rep["series"].items():
        cov = f"{e.get('coverage_pct', 0):.0f}" if e["in_cache"] else "—"
        miss = str(e.get("missing_count", "—")) if e["in_cache"] else "—"
        sample = ", ".join(e.get("missing_months", [])[:3]) if e["in_cache"] else "(not cached)"
        flag = "✓" if e["in_cache"] else "✗"
        print(f"  {name:28s} {flag:>7s} {cov:>6s} {miss:>8s}  {sample}")


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Fundamentals cache management (research layer)")
    ap.add_argument("--bootstrap", action="store_true",
                    help="Seed cache from V1/Spec C hardcoded values")
    ap.add_argument("--report", action="store_true", help="Print missing-data report")
    ap.add_argument("--list", action="store_true", help="List cached series")
    args = ap.parse_args()
    if args.bootstrap:
        r = bootstrap_from_existing(overwrite=True)
        for k, v in r.items():
            print(f"{k}: {v}")
    if args.list:
        for s in list_cached():
            print(s)
    if args.report or (not args.bootstrap and not args.list):
        rep = missing_data_report()
        _print_report(rep)


if __name__ == "__main__":
    main()
