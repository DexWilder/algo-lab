"""Cycle 2026-06-15g — MGC v-roll event-only dataset + MGC pre-CPI-drift re-test.

Operator option 2. Lane B / REPORT-ONLY. Builds a SEPARATE research-only dataset
from Databento MGC.v.0 (volume-roll) covering ONLY CPI event windows, to get an
honest verdict on the MGC pre-CPI-drift signal WITHOUT touching the canonical
.c.0 feed (read by active MGC books).

HARD: does NOT edit data/processed/MGC_5m.csv. Writes only the research file
research/data/fql_forge/MGC_vroll_event.csv. Confirms canonical hash unchanged.
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from data.databento_loader import get_client, resample_5m  # noqa: E402
from research.event_window_engine import generate_event_window_signals  # noqa: E402
from research.forge_cpi_calendar_verified import build_verified_cpi_calendar  # noqa: E402
from research.fql_forge_batch_runner import _metrics  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import run_backtest, get_cost_params  # noqa: E402

CANON = ROOT / "data" / "processed" / "MGC_5m.csv"
CANON_EXPECTED_HASH = "90aa5c4e182a458b"
OUT_CSV = ROOT / "research" / "data" / "fql_forge" / "MGC_vroll_event.csv"
SYMBOL = "MGC.v.0"
DATASET, SCHEMA, STYPE = "GLBX.MDP3", "ohlcv-1m", "continuous"
EASTERN = "US/Eastern"
MAX_GAP_MIN, MAX_HOLD_GAP_MIN = 10, 15


def fetch_vroll_day(client, day: str) -> pd.DataFrame:
    """Fetch one Eastern calendar day of MGC.v.0 1m, processed like databento_loader."""
    with contextlib.redirect_stdout(io.StringIO()):
        store = client.timeseries.get_range(
            dataset=DATASET, start=f"{day}T00:00:00", end=f"{day}T23:59:59",
            symbols=[SYMBOL], schema=SCHEMA, stype_in=STYPE)
        df = store.to_df()
    if df is None or len(df) == 0:
        return pd.DataFrame()
    df.index = df.index.tz_convert(EASTERN).tz_localize(None)
    df.index.name = "datetime"
    df = df[["open", "high", "low", "close", "volume"]].copy()
    if df["close"].mean() > 100_000:
        for c in ["open", "high", "low", "close"]:
            df[c] = df[c] / 1e9
    return df


def build_dataset():
    client = get_client()
    cal = build_verified_cpi_calendar()
    # restrict to MGC canonical span (use canonical to define coverage years)
    canon_dts = pd.to_datetime(pd.read_csv(CANON)["datetime"])
    lo, hi = canon_dts.iloc[0], canon_dts.iloc[-1]
    events = [(c["actual_date"], pd.to_datetime(f"{c['actual_date']} {c['actual_time_et']}")) for c in cal]
    events = [(d, e) for d, e in events if lo <= e <= hi]

    rows_per_date, frames, still_missing = {}, [], []
    for d, _e in events:
        try:
            day_df = fetch_vroll_day(client, d)
        except Exception as ex:
            rows_per_date[d] = f"ERR:{type(ex).__name__}"; still_missing.append(d); continue
        if len(day_df) == 0:
            rows_per_date[d] = 0; still_missing.append(d); continue
        d5 = resample_5m(day_df)
        d5 = d5[pd.to_datetime(d5.index).date == pd.Timestamp(d).date()]  # only target date
        rows_per_date[d] = int(len(d5))
        frames.append(d5.reset_index())
    if not frames:
        return None, rows_per_date, still_missing, events
    out = pd.concat(frames, ignore_index=True)
    out = out.drop_duplicates(subset=["datetime"]).sort_values("datetime").reset_index(drop=True)
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_CSV, index=False)
    return out, rows_per_date, still_missing, events


def clean_events(df, events, entry_off, exit_off):
    dts = pd.to_datetime(df["datetime"]).reset_index(drop=True); vals = dts.values; n = len(dts)
    kept, da, dg = [], 0, 0
    for e in events:
        e = pd.Timestamp(e); idx = int(np.searchsorted(vals, np.datetime64(e)))
        if idx >= n: da += 1; continue
        cand = [j for j in (idx, idx - 1) if 0 <= j < n]
        if min(abs((dts.iloc[j] - e).total_seconds()) for j in cand) / 60 > MAX_GAP_MIN: da += 1; continue
        ei, xi = idx + entry_off, idx + entry_off + exit_off
        if ei < 0 or xi >= n: da += 1; continue
        win = dts.iloc[min(ei, idx):max(xi, idx) + 1]
        if win.diff().dropna().dt.total_seconds().max() / 60 > MAX_HOLD_GAP_MIN: dg += 1; continue
        kept.append(e)
    return kept, da, dg


def retest(df):
    events = [pd.to_datetime(f"{c['actual_date']} {c['actual_time_et']}") for c in build_verified_cpi_calendar()]
    dts = pd.to_datetime(df["datetime"]); raw = [e for e in events if dts.iloc[0] <= e <= dts.iloc[-1]]
    clean, da, dg = clean_events(df, raw, -12, 12)
    cfg = ASSETS["MGC"]; costs = get_cost_params("MGC")
    sigs = generate_event_window_signals(df, events=clean, entry_offset_bars=-12,
                                         exit_offset_bars=12, direction="long")
    res = run_backtest(df, sigs, mode="both", point_value=cfg["point_value"], symbol="MGC",
                       commission_per_side=costs["commission_per_side"],
                       slippage_ticks=costs["slippage_ticks"], tick_size=costs["tick_size"])
    tr = res["trades_df"]; m = _metrics(tr, "MGC-preCPI-vroll", costs=res["stats"]["costs"])
    ld = on = None
    if tr is not None and not tr.empty and "pnl" in tr.columns:
        et = pd.to_datetime(tr["entry_time"]); ld = round(float(tr["pnl"].astype(float).groupby(et.dt.date).sum().min()), 2)
        if "exit_time" in tr.columns: on = int((pd.to_datetime(tr["exit_time"]).dt.date > et.dt.date).sum())
    pf = m.get("pf"); h1 = m.get("h1_pf"); h2 = m.get("h2_pf")
    return {"raw_n": len(raw), "clean_n": len(clean), "dropped_align": da, "dropped_gap": dg,
            "pf": round(float(pf), 3) if pf == pf else None,
            "median": round(float(m.get("median", 0)), 2),
            "h1_pf": round(float(h1), 3) if h1 == h1 else None,
            "h2_pf": round(float(h2), 3) if h2 == h2 else None,
            "max_year_share_pct": round(float(m.get("max_year_share_pct", 0)), 1),
            "largest_event_day_loss": ld, "overnight_holds": on,
            "gate_verdict": m.get("gate_verdict"), "archetype": m.get("archetype")}


def run():
    print("Cycle 2026-06-15g — MGC v-roll event dataset + pre-CPI re-test (REPORT-ONLY, option 2)\n", flush=True)
    pre_hash = hashlib.sha256(CANON.read_bytes()).hexdigest()[:16]
    print(f"canonical pre-run hash: {pre_hash} (expected {CANON_EXPECTED_HASH})", flush=True)

    out, rows_per_date, missing, events = build_dataset()
    post_hash = hashlib.sha256(CANON.read_bytes()).hexdigest()[:16]
    canon_ok = (post_hash == pre_hash == CANON_EXPECTED_HASH)
    print(f"canonical post-run hash: {post_hash} | UNCHANGED={canon_ok}", flush=True)
    if out is None:
        print("NO v-roll data fetched (all events returned empty/error). Aborting re-test.", flush=True)
        print("still_missing:", missing, flush=True); return
    fetched_dates = sum(1 for v in rows_per_date.values() if isinstance(v, int) and v > 0)
    print(f"v-roll dataset: {len(out)} bars over {fetched_dates}/{len(events)} event dates "
          f"-> {OUT_CSV.relative_to(ROOT)}", flush=True)
    print(f"still missing on v.0: {len(missing)} {missing[:6]}", flush=True)

    r = retest(out)
    print("\n=== MGC pre-CPI-drift re-test on v-roll event data ===", flush=True)
    print(f"  raw_n={r['raw_n']} -> clean_n={r['clean_n']} (drop align={r['dropped_align']} gap={r['dropped_gap']})", flush=True)
    print(f"  clean PF={r['pf']} median=${r['median']} H1/H2={r['h1_pf']}/{r['h2_pf']} "
          f"maxyr={r['max_year_share_pct']}% ON={r['overnight_holds']} dayLoss=${r['largest_event_day_loss']} "
          f"-> {r['gate_verdict']}", flush=True)
    print("\n  vs canonical .c.0: clean PF=1.422 n=42 maxyr=53.6% (DEFER)", flush=True)

    # disposition
    passes_bar = (r["pf"] and r["pf"] >= 1.3 and r["clean_n"] >= 30 and r["h1_pf"] and r["h2_pf"]
                  and r["h1_pf"] > 1.0 and r["h2_pf"] > 1.0)
    if not passes_bar:
        disp = "KILL_OR_WEAK — does not clear screen bar on complete v-roll data"
    elif r["max_year_share_pct"] > 50:
        disp = "RESEARCH/WATCH or DEFER — survives but concentration >50% (not candidate)"
    else:
        disp = "PACKET_CANDIDATE (v-roll RESEARCH data only; NOT production-wiring eligible)"
    print(f"\n  DISPOSITION: {disp}", flush=True)

    OUT_HASH = hashlib.sha256(OUT_CSV.read_bytes()).hexdigest()[:16]
    rep = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-15g_mgc_vroll_event_retest.json"
    rep.write_text(json.dumps({
        "cycle": "2026-06-15g_mgc_vroll_event_retest", "mode": "Lane B report-only (option 2)",
        "provenance": {
            "symbol": SYMBOL, "dataset": DATASET, "schema": SCHEMA, "stype": STYPE,
            "fetch_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "event_dates_requested": len(events), "rows_per_date": rows_per_date,
            "still_missing_on_vroll": missing, "output_file": str(OUT_CSV.relative_to(ROOT)),
            "output_rows": int(len(out)), "output_sha256_16": OUT_HASH,
            "resample_rule": "1m->5m label=left closed=left (canonical resample_5m)",
        },
        "canonical_integrity": {"pre_hash": pre_hash, "post_hash": post_hash,
                                "expected": CANON_EXPECTED_HASH, "unchanged": canon_ok},
        "retest_vroll": r,
        "canonical_croll_reference": {"clean_pf": 1.422, "clean_n": 42, "max_year_share_pct": 53.6, "verdict": "DEFER"},
        "disposition": disp,
        "data_integrity_grade": "v-roll RESEARCH data (MGC.v.0); CPI calendar DATA_REQUIRED; NOT production-eligible",
        "boundaries": "report-only; canonical .c.0 untouched; no promotion/wiring; no active MGC book change",
    }, indent=2, default=str))
    print(f"\nWrote: {rep}", flush=True)


if __name__ == "__main__":
    run()
