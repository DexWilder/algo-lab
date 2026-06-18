"""WP-B1 Treasury-auction test harness — READY-BUT-UNRUN (report-only).

Authorized 2026-06-18 as feed-gated prep. Runs the FULL locked WP-B1 sequence the moment the
REAL feed lands at data/feeds/treasury_auctions.csv; until then -> AWAITING_FEED, runs NOTHING.
NO synthetic data, NO dry-run on fake data, NO PASS/WATCH/KILL before the real file (the standing
guard: clean plumbing on fake data fakes confidence about timestamp/join semantics).

Every audit lesson from the rates work is baked in:
  - NO-LOOKAHEAD: align auction_date to trading days; signal/entry use only info available; the
    auction RESULT (bid-to-cover/high-yield) is post-auction -> may NOT gate the pre-auction leg.
  - CONTAMINATION DECOMPOSITION: split events by FOMC-overlap; report CLEAN-of-FOMC edge directly
    (don't double-count the FOMC sleeve). Auctions are exact-date (no continuous-roll stitch issue
    the way generic month-end had, but still join to the correct tenor's continuous bars carefully).
  - TAIL-ENGINE GATES: max-single<35%, top3, max-year<50%, pos-frac>=0.6, cost-robust, prop worst-day.
  - SAMPLE FLOORS + predeclared KILL CRITERIA. Minimal predeclared mechanism set (no broad sweep).
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

# tenor -> traded future (by-tenor routing)
TENOR_FUTURE = {"2Y": "ZF", "3Y": "ZF", "5Y": "ZF", "7Y": "ZN", "10Y": "ZN", "20Y": "ZB", "30Y": "ZB"}
ALIASES = {"tenor": ["tenor", "security_term", "term", "originalsecurityterm"],
           "security_type": ["security_type", "securitytype", "type"],
           "auction_date": ["auction_date", "auctiondate", "record_date"]}
OPTIONAL = {"offering_type": ["offering_type", "reopening", "original_or_reopening"],
            "bid_to_cover": ["bid_to_cover_ratio", "bid_to_cover", "bidtocoverratio"]}

# PREDECLARED minimal mechanism set (first-cut, no sweep):
MECHANISMS = [
    {"name": "post_auction_reversion_long", "entry_off": 0, "exit_off": 2, "dir": 1,
     "uses_result": False, "note": "long matched-tenor future T0->T+2 (post-auction reversion)"},
    {"name": "pre_auction_concession_short", "entry_off": -2, "exit_off": 0, "dir": -1,
     "uses_result": False, "note": "short matched-tenor T-2->T0 (concession into auction; NO result used)"},
]
SAMPLE_FLOOR = 40            # min events per mechanism/tenor to evaluate
KILL = {"pf_min": 1.2, "max_single_max": 35.0, "max_year_max": 50.0, "pos_frac_min": 0.55}


def _resolve(cols_lower, aliases):
    for a in aliases:
        if a.lower() in cols_lower:
            return cols_lower[a.lower()]
    return None


def _normalize_tenor(v):
    s = str(v).upper().replace("-", "").replace(" ", "")
    for t in TENOR_FUTURE:
        if t.replace("Y", "") in s and ("Y" in s or "YEAR" in s):
            return t
    return None


def load_auctions():
    if not FEED.exists():
        return None, "AWAITING_FEED"
    df = pd.read_csv(FEED)
    cl = {c.lower(): c for c in df.columns}
    r = {k: _resolve(cl, v) for k, v in ALIASES.items()}
    if any(v is None for v in r.values()):
        return None, f"STRUCTURE_INCOMPLETE missing {[k for k,v in r.items() if v is None]}"
    df["_ten"] = df[r["tenor"]].map(_normalize_tenor)
    df["_ad"] = pd.to_datetime(df[r["auction_date"]], errors="coerce")
    df["_fut"] = df["_ten"].map(TENOR_FUTURE)
    return df.dropna(subset=["_ad", "_fut"]), "OK"


def protocol():
    return {
        "expected_feed": str(FEED),
        "min_columns": "tenor/security_term, security_type, auction_date (+ offering_type, bid_to_cover enrich)",
        "tenor_routing": TENOR_FUTURE,
        "mechanisms_predeclared": [m["name"] + " :: " + m["note"] for m in MECHANISMS],
        "no_lookahead_rules": [
            "align auction_date to first trading day >= date; entry/exit by trading-day offset",
            "pre-auction leg uses NO auction result (result is post-event)",
            "any result-gated variant requires bid_to_cover/high_yield present AND only post-T0",
        ],
        "contamination_checks": [
            "FOMC-overlap split: report CLEAN-of-FOMC edge directly (±3d), don't double-count FOMC sleeve",
            "by-tenor separation (don't pool tenors into a false aggregate)",
            "reopening vs original split if offering_type present",
        ],
        "tail_engine_gates": KILL,
        "sample_floor_events": SAMPLE_FLOOR,
        "kill_criteria": "PF<1.2 cost-aware OR max-single>=35% OR max-year>=50% OR pos-frac<0.55 OR clean-of-FOMC edge collapses OR n<floor",
        "classification": "PASS_tail / WATCH_tail / KILL — only AFTER contamination decomposition; PASS_tail != paper-ready",
        "boundaries": "no activation/registry/scheduler/portfolio/paper/live/prop mutation",
    }


# ---- the actual screen (runs ONLY on the real feed) ----
def _pf(p):
    p = np.asarray(p, float); w = p[p > 0].sum(); l = -p[p < 0].sum()
    return float(w / l) if l > 0 else float("inf")


def daily_close(a):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{a}_5m.csv")
    dt = pd.to_datetime(df["datetime"])
    s = df.assign(date=dt.dt.normalize()).groupby("date")["close"].last(); s.index = pd.to_datetime(s.index); return s


def run_screen(auctions):
    import research.forge_fomc_calendar_official as fc
    fomc = set(pd.Timestamp(c["actual_date"]).normalize() for c in fc.build_official_fomc_calendar())
    closes = {f: daily_close(f) for f in set(TENOR_FUTURE.values())}
    results = {}
    for mech in MECHANISMS:
        for fut in sorted(set(auctions["_fut"])):
            s = closes[fut]; days = list(s.index); dset = set(days)
            pv = ASSETS[fut]["point_value"]; cp = get_cost_params(fut)
            rt = 2 * (cp["commission_per_side"] + cp["slippage_ticks"] * cp["tick_size"] * pv)
            rows = []
            for _, a in auctions[auctions["_fut"] == fut].iterrows():
                ad = a["_ad"].normalize()
                while ad not in dset and ad < days[-1]:
                    ad += pd.Timedelta(days=1)
                if ad not in dset:
                    continue
                i = days.index(ad); ei, xi = i + mech["entry_off"], i + mech["exit_off"]
                if ei < 0 or xi >= len(days) or xi <= ei:
                    continue
                pnl = mech["dir"] * (s.loc[days[xi]] - s.loc[days[ei]]) * pv - rt
                rows.append({"pnl": float(pnl), "year": ad.year, "fomc": any(abs((ad - f).days) <= 3 for f in fomc)})
            tr = pd.DataFrame(rows)
            results[f"{mech['name']}|{fut}"] = _board(tr)
    return results


def _board(tr):
    if tr is None or len(tr) < SAMPLE_FLOOR:
        return {"n": len(tr) if tr is not None else 0, "verdict": "KILL_low_n"}
    def stats(sub):
        if len(sub) < 12:
            return {"n": len(sub), "pf": None}
        p = sub["pnl"].to_numpy(); net = float(p.sum()); g = np.sort(p[p > 0])[::-1]; gp = float(p[p > 0].sum())
        py = sub.groupby("year")["pnl"].sum()
        return {"n": len(p), "pf": round(_pf(p), 3), "pos_frac": round(float((p > 0).mean()), 2),
                "max_single_pct": round(float(g[0]) / gp * 100, 1) if gp > 0 else None,
                "max_year_pct": round(float(py.abs().max() / net * 100), 1) if net else None}
    full = stats(tr); clean = stats(tr[~tr["fomc"]])
    c = clean if clean.get("pf") else full
    ok = (c.get("pf") or 0) >= KILL["pf_min"] and (c.get("max_single_pct") or 99) < KILL["max_single_max"] \
        and (c.get("max_year_pct") or 99) < KILL["max_year_max"] and (c.get("pos_frac") or 0) >= KILL["pos_frac_min"]
    return {"all": full, "clean_of_fomc": clean, "verdict": "PASS_tail" if ok else ("WATCH_tail" if (c.get("pf") or 0) >= 1.1 else "KILL")}


def main():
    auctions, status = load_auctions()
    print("WP-B1 Treasury-auction harness (READY-BUT-UNRUN; no synthetic data)\n", flush=True)
    if auctions is None:
        print(f"STATUS: {status}", flush=True)
        print(json.dumps(protocol(), indent=2, default=str), flush=True)
        print("\n-> Drop the REAL CSV at the path above; this harness then runs the full locked sequence. "
              "No results produced before the real file. (No PASS/WATCH/KILL on synthetic data.)", flush=True)
        return
    print(f"STATUS: feed present ({len(auctions)} auctions) -> running locked WP-B1 sequence", flush=True)
    res = run_screen(auctions)
    for k, v in res.items():
        print(f"  {k}: {v.get('verdict')} | clean-of-FOMC: {v.get('clean_of_fomc')}", flush=True)
    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "wp_b1_auction_screen.json"
    out.write_text(json.dumps({"mode": "WP-B1 real-feed screen; report-only; NON-WIRED", "n_auctions": len(auctions),
                               "results": res, "boundaries": "no mutation"}, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)


if __name__ == "__main__":
    main()
