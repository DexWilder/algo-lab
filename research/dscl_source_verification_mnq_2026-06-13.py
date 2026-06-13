"""DSCL Source Verification — MNQ, in-repo scope (2026-06-13).

Operator-authorized: DSCL Source Verification for MNQ using the in-repo
components available now; external-feed components are marked BLOCKED, not
skipped or faked.

Answers:
  1. Is MNQ data Databento-backed?            (lineage trace)
  2. Can the processed file lineage be proven? (provenance + reproducibility)
  3. In-repo data audits                       (continuity / dupes / gaps /
                                                session-boundary / rollover /
                                                append-only since DATA_AUDIT_GREEN)
  4. Rebuild + compare the DATA_AUDIT_GREEN window (OHLCV hash, signal hash,
     trades, PF, median, largest single-trade & single-day loss)

Lineage (traced from code, see packet for detail):
  vendor=Databento dataset=GLBX.MDP3 schema=ohlcv-1m stype=continuous
  raw_symbol=MNQ.c.0 (front-month continuous, CALENDAR roll, raw stitch /
  NOT back-adjusted) tz=US/Eastern(naive) bars=1m->5m(label=left,closed=left)
  loader=data/databento_loader.py  daily=scripts/update_daily_data.py(mode=a)

Boundaries: report-only. No registry/runner/scheduler/portfolio mutation.
No stop_run wiring. External components explicitly BLOCKED.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from research.crossbreeding.crossbreeding_engine import generate_crossbred_signals  # noqa: E402
from research.fql_forge_batch_runner import _metrics  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import run_backtest, get_cost_params  # noqa: E402

ASSET = "MNQ"
CSV = ROOT / "data" / "processed" / f"{ASSET}_5m.csv"
AUDIT_WINDOW_END = "2026-06-10 19:55:00"
AUDIT_FILE_HASH = "739875437ded8a76"
AUDIT_N_BARS = 487168
AUDIT_SIGNAL_HASH = "d2d31c3f0e7e86bb"
BASE = {"n": 1414, "pf": 1.477, "median": 15.51, "net": 35368.64, "largest_loss": -1457.24}


def ohlcv_hash(df: pd.DataFrame) -> str:
    arr = df[["open", "high", "low", "close", "volume"]].to_numpy()
    return hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest()[:16]


def lineage() -> dict:
    return {
        "vendor": "Databento",
        "dataset": "GLBX.MDP3",
        "schema": "ohlcv-1m",
        "stype_in": "continuous",
        "raw_symbol": "MNQ.c.0",
        "roll_method": "front-month continuous, CALENDAR roll (.c.0), raw stitch — NOT back-adjusted (roll-day price gaps possible)",
        "timezone": "UTC -> US/Eastern, tz-stripped (naive Eastern)",
        "bar_construction": "trade-based 1m OHLCV resampled to 5m (label=left, closed=left; O=first H=max L=min C=last V=sum)",
        "loader_bulk": "data/databento_loader.py",
        "loader_incremental": "scripts/update_daily_data.py (fetches Databento 1m, resamples, append mode='a')",
        "incremental_raw_retained": False,
        "reproducibility_note": "post-March bars NOT re-derivable from a retained raw file; only by re-querying Databento (bulk raw frozen 2026-03-07).",
        "cost_model": get_cost_params(ASSET),
        "databento_backed": True,
    }


def in_repo_audits(df: pd.DataFrame) -> dict:
    dt = pd.to_datetime(df["datetime"])
    diffs = dt.diff().dt.total_seconds() / 60
    # session-boundary / overnight gaps: bars where gap is large (next session)
    # rollover-adjacent: detect large overnight price jumps (|open - prev close| big)
    o = df["open"].to_numpy(); c = df["close"].to_numpy()
    prev_c = np.roll(c, 1); prev_c[0] = np.nan
    overnight_gap_pts = np.abs(o - prev_c)
    # flag gaps > 50 MNQ points at a session boundary (>60 min since prior bar)
    boundary = (diffs > 60).to_numpy()
    big_gap_at_boundary = int(np.nansum((overnight_gap_pts > 50) & boundary))
    # candidate roll days: quarterly (Mar/Jun/Sep/Dec) large boundary gaps
    roll_candidates = []
    idx = np.where((overnight_gap_pts > 100) & boundary)[0]
    for i in idx[:50]:
        roll_candidates.append({"datetime": str(dt.iloc[i]),
                                 "gap_pts": round(float(overnight_gap_pts[i]), 2)})
    return {
        "n_bars": int(len(df)),
        "span_start": str(dt.iloc[0]),
        "span_end": str(dt.iloc[-1]),
        "duplicate_timestamps": int(dt.duplicated().sum()),
        "monotonic_increasing": bool(dt.is_monotonic_increasing),
        "bar_gaps": {
            "exactly_5min": int((diffs == 5).sum()),
            "sub_5min": int(((diffs > 0) & (diffs < 5)).sum()),
            "gt_10min": int((diffs > 10).sum()),
            "gt_60min_session_boundaries": int((diffs > 60).sum()),
            "gt_1d": int((diffs > 1440).sum()),
            "gt_3d": int((diffs > 4320).sum()),
        },
        "session_boundary_big_price_gaps_gt50pt": big_gap_at_boundary,
        "rollover_candidate_gaps_gt100pt": roll_candidates,
        "ohlcv_hash_full": ohlcv_hash(df),
        "current_file_hash": hashlib.sha256(CSV.read_bytes()).hexdigest()[:16],
    }


def rebuild_audit_window(df: pd.DataFrame) -> dict:
    dt = pd.to_datetime(df["datetime"])
    trunc = df[dt <= pd.Timestamp(AUDIT_WINDOW_END)].reset_index(drop=True)
    cfg = ASSETS[ASSET]; costs = get_cost_params(ASSET)
    sigs = generate_crossbred_signals(trunc, entry_name="stop_run_reversal",
                                      exit_name="profit_ladder", filter_name="ema_slope", params={})
    res = run_backtest(trunc, sigs, mode="both", point_value=cfg["point_value"], symbol=ASSET,
                       commission_per_side=costs["commission_per_side"],
                       slippage_ticks=costs["slippage_ticks"], tick_size=costs["tick_size"])
    m = _metrics(res["trades_df"], "audit_window", costs=res["stats"]["costs"])
    trades = res["trades_df"]
    pnl = trades["pnl"].astype(float)
    day = pd.to_datetime(trades["entry_time"]).dt.date
    largest_day = float(pnl.groupby(day).sum().min())
    tdt = pd.to_datetime(trunc["datetime"])
    return {
        "truncated_n_bars": int(len(trunc)),
        "audit_n_bars": AUDIT_N_BARS,
        "n_bars_match_append_only": len(trunc) == AUDIT_N_BARS,
        "first_ts": str(tdt.iloc[0]),
        "last_ts": str(tdt.iloc[-1]),
        "ohlcv_hash_window": ohlcv_hash(trunc),
        "signal_hash": hashlib.sha256(sigs["signal"].values.tobytes()).hexdigest()[:16],
        "signal_hash_matches_audit": hashlib.sha256(sigs["signal"].values.tobytes()).hexdigest()[:16] == AUDIT_SIGNAL_HASH,
        "n": int(m["n"]), "pf": round(float(m["pf"]), 3),
        "median": round(float(m["median"]), 2), "net": round(float(m["net"]), 2),
        "largest_single_trade_loss": round(float(pnl.min()), 2),
        "largest_single_day_loss": round(largest_day, 2),
        "matches_committed_baseline": (int(m["n"]) == BASE["n"] and round(float(m["pf"]), 3) == BASE["pf"]
                                        and round(float(m["median"]), 2) == BASE["median"]),
    }


def run():
    print("DSCL Source Verification — MNQ, in-repo scope (2026-06-13)\n", flush=True)
    lin = lineage()
    print("--- 1/2. LINEAGE ---", flush=True)
    print(f"  Databento-backed: {lin['databento_backed']} | {lin['dataset']} {lin['schema']} {lin['raw_symbol']}", flush=True)
    print(f"  roll: {lin['roll_method']}", flush=True)
    print(f"  incremental raw retained: {lin['incremental_raw_retained']} ({lin['reproducibility_note']})", flush=True)

    df = pd.read_csv(CSV)
    print("\n--- 3. IN-REPO AUDITS ---", flush=True)
    aud = in_repo_audits(df)
    print(f"  bars={aud['n_bars']} span {aud['span_start']} -> {aud['span_end']}", flush=True)
    print(f"  duplicates={aud['duplicate_timestamps']} monotonic={aud['monotonic_increasing']}", flush=True)
    print(f"  bar_gaps={aud['bar_gaps']}", flush=True)
    print(f"  session-boundary big price gaps (>50pt): {aud['session_boundary_big_price_gaps_gt50pt']}", flush=True)
    print(f"  rollover-candidate gaps (>100pt): {len(aud['rollover_candidate_gaps_gt100pt'])} found", flush=True)
    print(f"  full-file OHLCV hash: {aud['ohlcv_hash_full']} | file hash: {aud['current_file_hash']}", flush=True)

    print("\n--- 4. REBUILD + COMPARE DATA_AUDIT_GREEN WINDOW ---", flush=True)
    rb = rebuild_audit_window(df)
    print(f"  truncated bars={rb['truncated_n_bars']} (audit {rb['audit_n_bars']}) append_only={rb['n_bars_match_append_only']}", flush=True)
    print(f"  window: {rb['first_ts']} -> {rb['last_ts']}", flush=True)
    print(f"  signal_hash={rb['signal_hash']} matches_audit={rb['signal_hash_matches_audit']}", flush=True)
    print(f"  n={rb['n']} pf={rb['pf']} median=${rb['median']} net=${rb['net']}", flush=True)
    print(f"  largest_trade_loss=${rb['largest_single_trade_loss']} largest_day_loss=${rb['largest_single_day_loss']}", flush=True)
    print(f"  matches committed baseline: {rb['matches_committed_baseline']}", flush=True)

    external = {
        "component_7_cme_settlement_comparison": "BLOCKED_ON_EXTERNAL_FEED_ACCESS (CME DataMine)",
        "component_8_secondary_vendor_spotcheck": "BLOCKED_ON_EXTERNAL_FEED_ACCESS (e.g. dxFeed)",
        "component_9_paper_execution_reconciliation": "BLOCKED_PENDING_PAPER_PERIOD",
    }
    print("\n--- EXTERNAL DSCL COMPONENTS (honest status) ---", flush=True)
    for k, v in external.items():
        print(f"  {k}: {v}", flush=True)

    in_repo_pass = (aud["duplicate_timestamps"] == 0 and aud["monotonic_increasing"]
                    and rb["n_bars_match_append_only"] and rb["signal_hash_matches_audit"]
                    and rb["matches_committed_baseline"])
    verdict = "DSCL_IN_REPO_VERIFIED" if in_repo_pass else "DSCL_IN_REPO_NEEDS_REVIEW"
    canonical_for_paper = "ACCEPTABLE_AS_CANONICAL_FOR_PAPER" if in_repo_pass else "NOT_YET"
    print(f"\n  IN-REPO VERDICT: {verdict}", flush=True)
    print(f"  Canonical for PAPER (not capital): {canonical_for_paper}", flush=True)
    print(f"  Canonical for LIVE/PROP: BLOCKED until external DSCL §7 (components 7-9) pass", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "dscl_source_verification_mnq_2026-06-13.json"
    out.write_text(json.dumps({
        "purpose": "DSCL Source Verification — MNQ in-repo scope",
        "boundaries": "report-only; external components BLOCKED not faked; no wiring",
        "lineage": lin,
        "in_repo_audits": aud,
        "rebuild_audit_window": rb,
        "external_components": external,
        "in_repo_verdict": verdict,
        "databento_backed": True,
        "canonical_for_paper": canonical_for_paper,
        "canonical_for_live_prop": "BLOCKED_until_DSCL_section7",
        "stop_run_may_proceed_to_phase1c": "ONLY after Org Hygiene/Elite Classification Audit confirms no remaining activation-risk mismatches (operator gate)",
    }, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)
    return verdict


if __name__ == "__main__":
    v = run()
    sys.exit(0 if v == "DSCL_IN_REPO_VERIFIED" else 1)
