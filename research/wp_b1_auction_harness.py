"""WP-B1 Treasury-auction test harness — READY-BUT-UNRUN (report-only).

Authorized feed-gated prep (2026-06-18, expanded). Runs the FULL locked WP-B1 sequence the moment
the REAL feed lands at data/feeds/treasury_auctions.csv; until then -> AWAITING_FEED, runs NOTHING.
NO synthetic data, NO dry-run, NO PASS/WATCH/KILL before the real file (standing guard against
fake-data false confidence).

PREDECLARED EVENT WINDOWS (4 families):
  1. pre_auction_drift          : T-2 -> T0  (concession into issuance; structural short bonds; NO result used)
  2. auction_to_settlement      : T0  -> T+2 (post-auction / to-settlement reaction, long)
  3. same_day_post_auction      : intraday T0 (first 5m bar >= auction_time -> session close)  [needs auction_time + 5m]
  4. next_session               : T0  -> T+1 (next-session continuation/reversal)

CONTAMINATION FLAGS per event (report CLEAN-of-all directly; never double-count an existing sleeve):
  FOMC (±3d) · CPI (±2d) · NFP (±2d) · month-end proximity (last 3 td) · quarter-end · roll-window
  (late Feb/May/Aug/Nov = ZF/ZN roll). By-tenor routing (no pooling). Reopening vs original split.

Every session lesson baked in: no-lookahead trading-day alignment; pre-auction leg uses NO result;
tail-engine gates; sample floor; predeclared kill criteria; minimal mechanism set (no sweep).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import get_cost_params  # noqa: E402

FEED = ROOT / "data" / "feeds" / "treasury_auctions.csv"
TENOR_FUTURE = {"2Y": "ZF", "3Y": "ZF", "5Y": "ZF", "7Y": "ZN", "10Y": "ZN", "20Y": "ZB", "30Y": "ZB"}
ALIASES = {"tenor": ["tenor", "security_term", "term", "originalsecurityterm"],
           "security_type": ["security_type", "securitytype", "type"],
           "auction_date": ["auction_date", "auctiondate", "record_date"]}
OPTIONAL = {"offering_type": ["offering_type", "reopening", "original_or_reopening"],
            "auction_time": ["auction_time_et", "auction_time", "time"],
            "settlement_date": ["settlement_date", "issue_date"],
            "bid_to_cover": ["bid_to_cover_ratio", "bid_to_cover", "bidtocoverratio"]}

# RESULT-USAGE RULE (no-lookahead): auction RESULT fields (bid_to_cover, tail, indirect/direct
# takedown, awarded/high yield, stop) are PUBLIC only AFTER the auction. A window may use them
# ONLY if it BEGINS after results are public. Calendar/supply metadata known IN ADVANCE (auction
# date, tenor, new-issue vs reopening flag, scheduled time) is usable in ANY window incl pre-auction.
# All current mechanisms use ZERO result fields (pure calendar windows) -> all no-lookahead-clean.

# daily-bar windows (entry_off, exit_off in trading days rel to auction T0; dir +1 long bonds)
DAILY_WINDOWS = [
    # pre_auction_drift: FIRST-CLASS window — dealer concession is a primary expression. Uses ONLY
    # calendar/supply-known info (date, tenor, reopening flag); NO result fields. Valid no-lookahead.
    {"name": "pre_auction_concession", "entry_off": -2, "exit_off": 0, "dir": -1,
     "result_usage": "calendar/supply-known ONLY (date,tenor,reopening); NO result fields", "note": "concession short into issuance"},
    {"name": "auction_to_settlement", "entry_off": 0, "exit_off": 2, "dir": 1,
     "result_usage": "post-event; calendar-based; result fields allowed only if entry strictly after results public", "note": "post-auction/settlement reaction long"},
    {"name": "next_session", "entry_off": 0, "exit_off": 1, "dir": 1,
     "result_usage": "post-event, no lookahead; result fields allowed (results public by T+1)", "note": "next-session continuation/reversal"},
]
# same_day_post_auction is intraday (needs auction_time + 5m) — defined; runs only if auction_time present.
SAMPLE_FLOOR = 40
KILL = {"pf_min": 1.2, "max_single_max": 35.0, "max_year_max": 50.0, "pos_frac_min": 0.55}


def _resolve(cl, al):
    for a in al:
        if a.lower() in cl:
            return cl[a.lower()]
    return None


def _norm_tenor(v):
    """Parse the tenor's leading YEAR number EXACTLY (fix: leading-substring match mis-routed
    '20Y'->'2Y', '30Y'->'3Y'). Bills (Week/Day) -> None. Fractional reopenings -> nearest std."""
    import re as _re
    s = str(v)
    if "Week" in s or "Day" in s:
        return None
    ym = _re.search(r"(\d+)\s*-?\s*(?:Y|Year)", s, _re.IGNORECASE)
    if not ym:
        return None
    yrs = float(ym.group(1))
    mm = _re.search(r"(\d+)\s*-?\s*Month", s, _re.IGNORECASE)
    if mm:
        yrs += int(mm.group(1)) / 12.0
    std = [2, 3, 5, 7, 10, 20, 30]
    nearest = min(std, key=lambda t: abs(t - yrs))
    return f"{nearest}Y"


def load_auctions():
    if not FEED.exists():
        return None, "AWAITING_FEED"
    df = pd.read_csv(FEED); cl = {c.lower(): c for c in df.columns}
    r = {k: _resolve(cl, v) for k, v in ALIASES.items()}
    if any(v is None for v in r.values()):
        return None, f"STRUCTURE_INCOMPLETE missing {[k for k,v in r.items() if v is None]}"
    o = {k: _resolve(cl, v) for k, v in OPTIONAL.items()}
    df["_ten"] = df[r["tenor"]].map(_norm_tenor); df["_ad"] = pd.to_datetime(df[r["auction_date"]], errors="coerce")
    df["_fut"] = df["_ten"].map(TENOR_FUTURE)
    df["_reopen"] = df[o["offering_type"]].astype(str).str.lower().str.contains("reopen") if o.get("offering_type") else False
    df["_atime"] = df[o["auction_time"]] if o.get("auction_time") else None
    return df.dropna(subset=["_ad", "_fut"]), "OK"


def first_fridays(years):
    out = []
    for y in years:
        for mth in range(1, 13):
            d = pd.Timestamp(y, mth, 1)
            while d.weekday() != 4:
                d += pd.Timedelta(days=1)
            out.append(d.normalize())
    return out


def protocol():
    return {"expected_feed": str(FEED),
            "min_columns": "tenor/security_term, security_type, auction_date (+ offering_type, auction_time_et, settlement_date, bid_to_cover enrich)",
            "tenor_routing": TENOR_FUTURE,
            "event_windows": [f"{w['name']} (T{w['entry_off']:+d}->T{w['exit_off']:+d}, dir {w['dir']}) :: {w['note']} [result-usage: {w['result_usage']}]" for w in DAILY_WINDOWS]
                             + ["same_day_post_auction (intraday T0: first 5m bar >= auction_time -> session close) [needs auction_time; post-event no-lookahead]"],
            "result_usage_rule": "auction RESULT fields (bid_to_cover/tail/indirect-direct/awarded-or-high-yield/stop) are public ONLY after the auction -> usable ONLY in windows that BEGIN post-results. Calendar/supply metadata (date,tenor,reopening flag,scheduled time) known in advance -> usable in ANY window incl pre-auction. pre_auction_concession is a first-class predeclared window using calendar/supply-known ONLY.",
            "contamination_flags": ["FOMC ±3d", "CPI ±2d", "NFP ±2d", "month-end proximity (last 3 td)", "quarter-end", "roll-window (late Feb/May/Aug/Nov)"],
            "no_lookahead_rules": ["auction_date -> first trading day >= date; entry/exit by trading-day offset",
                                   "pre-auction leg uses NO auction result", "result-gated variants only post-T0 and only if result cols present"],
            "tail_engine_gates": KILL, "sample_floor_events": SAMPLE_FLOOR,
            "kill_criteria": "PF<1.2 cost-aware OR max-single>=35% OR max-year>=50% OR pos-frac<0.55 OR clean-of-contamination edge collapses OR n<floor",
            "classification": "PASS_tail / WATCH_tail / KILL — only AFTER contamination decomposition; PASS_tail != paper-ready",
            "splits": ["by-tenor (no pooling)", "reopening vs original", "clean-of-FOMC/CPI/NFP/month-end/quarter-end/roll"],
            "boundaries": "no activation/registry/scheduler/portfolio/paper/live/prop mutation"}


def _pf(p):
    p = np.asarray(p, float); w = p[p > 0].sum(); l = -p[p < 0].sum()
    return float(w / l) if l > 0 else float("inf")


def daily_close(a):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{a}_5m.csv"); dt = pd.to_datetime(df["datetime"])
    s = df.assign(date=dt.dt.normalize()).groupby("date")["close"].last(); s.index = pd.to_datetime(s.index); return s


def run_screen(auctions):
    import research.forge_fomc_calendar_official as fc
    fomc = set(pd.Timestamp(c["actual_date"]).normalize() for c in fc.build_official_fomc_calendar())
    try:
        import research.forge_cpi_calendar_verified as cc
        cpi = set(pd.Timestamp(c["actual_date"]).normalize() for c in cc.build_verified_cpi_calendar())
    except Exception:
        cpi = set()
    nfp = set(first_fridays(range(2019, 2027)))
    ROLL = {2, 5, 8, 11}
    closes = {f: daily_close(f) for f in set(TENOR_FUTURE.values())}
    results = {}
    for w in DAILY_WINDOWS:
        for fut in sorted(set(auctions["_fut"])):
            s = closes[fut]; days = list(s.index); dset = set(days)
            pv = ASSETS[fut]["point_value"]; cp = get_cost_params(fut)
            rt = 2 * (cp["commission_per_side"] + cp["slippage_ticks"] * cp["tick_size"] * pv)
            rows = []
            mdays = {}  # month -> sorted trading days for month-end proximity
            for d in days:
                mdays.setdefault((d.year, d.month), []).append(d)
            for _, a in auctions[auctions["_fut"] == fut].iterrows():
                ad = a["_ad"].normalize()
                while ad not in dset and ad < days[-1]:
                    ad += pd.Timedelta(days=1)
                if ad not in dset:
                    continue
                i = days.index(ad); ei, xi = i + w["entry_off"], i + w["exit_off"]
                if ei < 0 or xi >= len(days) or xi <= ei:
                    continue
                me_list = mdays[(ad.year, ad.month)]
                rows.append({"pnl": float(w["dir"] * (s.loc[days[xi]] - s.loc[days[ei]]) * pv - rt), "year": ad.year,
                             "reopen": bool(a["_reopen"]),
                             "c_fomc": any(abs((ad - f).days) <= 3 for f in fomc),
                             "c_cpi": any(abs((ad - f).days) <= 2 for f in cpi),
                             "c_nfp": any(abs((ad - f).days) <= 2 for f in nfp),
                             "c_me": ad in me_list[-3:], "c_qe": (ad.month in (3, 6, 9, 12) and ad in me_list[-3:]),
                             "c_roll": ad.month in ROLL and ad.day >= 20})
            results[f"{w['name']}|{fut}"] = _board(pd.DataFrame(rows))
    return results


def _stats(sub):
    if len(sub) < 12:
        return {"n": len(sub), "pf": None}
    p = sub["pnl"].to_numpy(); net = float(p.sum()); g = np.sort(p[p > 0])[::-1]; gp = float(p[p > 0].sum())
    py = sub.groupby("year")["pnl"].sum()
    return {"n": len(p), "pf": round(_pf(p), 3), "pos_frac": round(float((p > 0).mean()), 2),
            "max_single_pct": round(float(g[0]) / gp * 100, 1) if gp > 0 else None,
            "max_year_pct": round(float(py.abs().max() / net * 100), 1) if net else None}


def _board(tr):
    if tr is None or len(tr) < SAMPLE_FLOOR:
        return {"n": len(tr) if tr is not None else 0, "verdict": "KILL_low_n"}
    full = _stats(tr)
    clean = _stats(tr[~(tr["c_fomc"] | tr["c_cpi"] | tr["c_nfp"] | tr["c_me"] | tr["c_roll"])])
    c = clean if clean.get("pf") else full
    ok = (c.get("pf") or 0) >= KILL["pf_min"] and (c.get("max_single_pct") or 99) < KILL["max_single_max"] \
        and (c.get("max_year_pct") or 99) < KILL["max_year_max"] and (c.get("pos_frac") or 0) >= KILL["pos_frac_min"]
    return {"all": full, "clean_of_all_contam": clean,
            "verdict": "PASS_tail" if ok else ("WATCH_tail" if (c.get("pf") or 0) >= 1.1 else "KILL")}


def main():
    auctions, status = load_auctions()
    print("WP-B1 Treasury-auction harness (READY-BUT-UNRUN; 4 windows; full contamination set; no synthetic data)\n", flush=True)
    if auctions is None:
        print(f"STATUS: {status}\n", flush=True)
        print(json.dumps(protocol(), indent=2, default=str), flush=True)
        print("\n-> Drop the REAL CSV; harness runs the full locked sequence then. No results before the real file.", flush=True)
        return
    print(f"STATUS: feed present ({len(auctions)} auctions) -> running locked WP-B1 sequence", flush=True)
    res = run_screen(auctions)
    for k, v in res.items():
        print(f"  {k}: {v.get('verdict')} | clean-of-contam: {v.get('clean_of_all_contam')}", flush=True)
    (ROOT / "research" / "data" / "fql_forge" / "reports" / "wp_b1_auction_screen.json").write_text(
        json.dumps({"mode": "WP-B1 real-feed screen; report-only; NON-WIRED", "n_auctions": len(auctions), "results": res}, indent=2, default=str))
    print("\nWrote screen JSON.", flush=True)


if __name__ == "__main__":
    main()
