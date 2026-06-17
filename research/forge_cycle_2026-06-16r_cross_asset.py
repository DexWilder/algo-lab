"""Cycle 2026-06-16r — CROSS-ASSET confirmation/divergence, first board (report-only).

Track 1 frontier move (single-series exhausted over 112 candidates). No-lookahead is
first-class (research/cross_asset_harness.py). Per operator guardrail, cross-asset state
is tested TWO ways, NOT bolted onto dead entries to overfit:
  MODE 1 — confirmation/state FILTER on the live credible structures (gold survivors
           MGC-ORB, MGC-prior_day_break) by dollar-state and rates-state. Pre vs post
           trade-count/PF/net/DD/concentration. OVERFIT-RISK flag if PF improves only by
           cutting trades below a retention floor or tiny-n.
  MODE 2 — STANDALONE divergence mechanism (MNQ/MYM/MES daily dispersion -> reversion of
           the laggard), a genuine trade source, not a rescue.

Deliverables: A no-lookahead proof, B instrument overlap, C first board, D verdicts,
E archive of failed confirmations. NO mutation; NON-WIRED.
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
from engine.backtest import get_cost_params, run_backtest  # noqa: E402
from research.crossbreeding.crossbreeding_engine import generate_crossbred_signals as gcs  # noqa: E402
from research.fql_forge_batch_runner import _metrics  # noqa: E402
import research.cross_asset_harness as cah  # noqa: E402


def _pf(p):
    p = np.asarray(p, float); w = p[p > 0].sum(); l = -p[p < 0].sum()
    return float(w / l) if l > 0 else float("inf")


def base_trades(asset, entry):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv"); cfg = ASSETS[asset]; c = get_cost_params(asset)
    s = gcs(df, entry_name=entry, exit_name="profit_ladder", filter_name="ema_slope", params={})
    return run_backtest(df, s, mode="both", point_value=cfg["point_value"], symbol=asset,
                        commission_per_side=c["commission_per_side"], slippage_ticks=c["slippage_ticks"],
                        tick_size=c["tick_size"])["trades_df"]


def stats(tr):
    if tr is None or len(tr) == 0:
        return {"n": 0}
    p = tr["pnl"].to_numpy(); t = tr.copy(); t["y"] = pd.to_datetime(t["entry_time"]).dt.year
    g = t[t["pnl"] > 0]["pnl"].sort_values(ascending=False); gp = float(g.sum())
    top3 = round(float(g.head(3).sum()) / gp * 100, 1) if gp > 0 else None
    eq = t.sort_values("entry_time")["pnl"].cumsum().to_numpy(); dd = float((eq - np.maximum.accumulate(eq)).min())
    return {"n": int(len(p)), "pf": round(_pf(p), 3), "net": round(float(p.sum()), 0),
            "median": round(float(np.median(p)), 2), "max_dd": round(dd, 0), "top3": top3,
            "yrs_pos": int((t.groupby("y")["pnl"].sum() > 0).sum()), "n_yrs": int(t["y"].nunique())}


def mode1(asset, entry, mnq_ref):
    """Confirmation: split base trades by dollar-state and rates-state (strictly-prior)."""
    tr = base_trades(asset, entry)
    base = stats(tr)
    out = {"asset": asset, "mechanism": entry, "baseline": base, "filters": {}, "proof": {}}
    for sdf, col, label in [(cah.dollar_state(), "usd_state", "USD"), (cah.trend_state("ZN"), "ZN_state", "RATES")]:
        merged = cah.attribute_by_state(tr, sdf, col)
        out["proof"][label] = cah.prove_no_lookahead(merged)
        for sign, tag in [(1.0, f"{label}_up"), (-1.0, f"{label}_dn")]:
            sub = merged[merged[col] == sign]
            st = stats(sub)
            retain = round(st["n"] / base["n"] * 100, 1) if base["n"] else 0
            # OVERFIT guard: PF must improve meaningfully AND retain >= 40% of trades AND n>=120
            improved = st.get("pf", 0) >= base["pf"] + 0.15
            ok_retain = retain >= 40 and st.get("n", 0) >= 120
            verdict = ("CONFIRMATION_EDGE" if (improved and ok_retain)
                       else ("OVERFIT_RISK" if (improved and not ok_retain) else "NO_EDGE"))
            out["filters"][tag] = {**st, "retain_pct": retain, "verdict": verdict}
    return out


def mode2_dispersion(mnq_ref):
    """STANDALONE: rank MNQ/MYM/MES daily returns; the laggard reverts next day (long laggard
    at next session, exit next close). No-lookahead: rank on completed day t, trade day t+1."""
    closes = {}
    for a in ("MNQ", "MYM", "MES"):
        d = cah.daily_closes(a); d = d.set_index("date")["c"]; closes[a] = d
    px = pd.concat(closes, axis=1).dropna()
    rets = px.pct_change().dropna(how="any")     # valid ranking days (drops all-NaN first row)
    pv = {a: ASSETS[a]["point_value"] for a in ("MNQ", "MYM", "MES")}
    cps = {a: get_cost_params(a) for a in ("MNQ", "MYM", "MES")}
    px_dates = list(px.index)
    pos = {d: k for k, d in enumerate(px_dates)}
    rows = []
    for d in rets.index:                          # rank on COMPLETED day d
        lag = rets.loc[d].idxmin()
        k = pos.get(d)
        if k is None or k + 1 >= len(px_dates):
            continue
        nd = px_dates[k + 1]                       # trade next session (no-lookahead)
        move = px.loc[nd, lag] - px.loc[d, lag]    # close-to-close on the laggard
        cost = 2 * (cps[lag]["commission_per_side"] + cps[lag]["slippage_ticks"] * cps[lag]["tick_size"] * pv[lag])
        rows.append({"entry_time": str(nd), "pnl": move * pv[lag] - cost, "asset": lag})
    tr = pd.DataFrame(rows)
    base = stats(tr)
    # correlation to MNQ workhorse
    if not tr.empty:
        a = tr.copy(); a["d"] = pd.to_datetime(a["entry_time"]).dt.date
        b = mnq_ref.copy(); b["d"] = pd.to_datetime(b["entry_time"]).dt.date
        al = pd.concat([a.groupby("d")["pnl"].sum(), b.groupby("d")["pnl"].sum()], axis=1, keys=["x", "y"]).fillna(0.0)
        corr = round(float(al["x"].corr(al["y"])), 3)
    else:
        corr = None
    tpy = round(base["n"] / max(base.get("n_yrs", 1), 1), 1) if base["n"] else 0
    quality = base.get("pf", 0) > 1.2 and base.get("median", -1) >= 0 and base.get("n", 0) >= 200
    verdict = ("FORWARD_CLOCK_CREDIBLE" if quality and abs(corr or 1) < 0.3 else ("WATCH_corr" if quality else "KILL"))
    return {"mechanism": "index_dispersion_laggard_revert", "stats": base, "trades_per_yr": tpy,
            "corr_mnq": corr, "verdict": verdict}


def run():
    print("Cycle 2026-06-16r — CROSS-ASSET confirmation/divergence first board (REPORT-ONLY)\n", flush=True)

    # B. instrument overlap
    ov = cah.overlap_ranges(["MGC", "MES", "MYM", "MNQ", "MCL", "ZN", "ZF", "6E", "6J", "6B"])
    print("B. INSTRUMENT DATE RANGES:", flush=True)
    for a, r in ov.items():
        print(f"   {a}: {r}", flush=True)

    _, = (None,)
    mnq_ref = base_trades("MNQ", "orb_breakout")

    # MODE 1 — confirmation on gold survivors
    print("\nMODE 1 — cross-asset CONFIRMATION on gold survivors (pre vs post; overfit-guarded):", flush=True)
    m1 = []
    for asset, entry in [("MGC", "orb_breakout"), ("MGC", "prior_day_break")]:
        r = mode1(asset, entry, mnq_ref); m1.append(r)
        b = r["baseline"]
        print(f"\n  {asset}-{entry}: baseline n={b['n']} PF={b['pf']} net=${b['net']} top3={b['top3']}%", flush=True)
        # A. no-lookahead proof (print once per state family)
        for lbl, pf_ in r["proof"].items():
            print(f"    [no-lookahead {lbl}] checked={pf_['trades_checked']} violations={pf_['violations']} "
                  f"min_lag={pf_['min_lag_days']}d median_lag={pf_['median_lag_days']}d", flush=True)
        for tag, s in r["filters"].items():
            print(f"    {tag:<10} n={s['n']:>4} ({s['retain_pct']:>5}%) PF={s.get('pf','-')} net=${s.get('net','-')} "
                  f"-> {s['verdict']}", flush=True)

    # MODE 2 — standalone dispersion
    print("\nMODE 2 — STANDALONE index dispersion (laggard reversion), a trade source:", flush=True)
    m2 = mode2_dispersion(mnq_ref)
    s = m2["stats"]
    print(f"  index_dispersion_laggard_revert: n={s.get('n')} PF={s.get('pf')} net=${s.get('net')} "
          f"median=${s.get('median')} {m2['trades_per_yr']}/yr corr_mnq={m2['corr_mnq']} -> {m2['verdict']}", flush=True)

    # D. verdicts / E. archive
    conf_edges = [f"{r['asset']}-{r['mechanism']}:{tag}" for r in m1 for tag, s in r["filters"].items() if s["verdict"] == "CONFIRMATION_EDGE"]
    overfit = [f"{r['asset']}-{r['mechanism']}:{tag}" for r in m1 for tag, s in r["filters"].items() if s["verdict"] == "OVERFIT_RISK"]
    print("\n=== VERDICTS ===", flush=True)
    print(f"  CONFIRMATION_EDGE: {conf_edges or 'none'}", flush=True)
    print(f"  OVERFIT_RISK (flagged, NOT survivors): {overfit or 'none'}", flush=True)
    print(f"  MODE 2 standalone: {m2['verdict']}", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-16r_cross_asset.json"
    out.write_text(json.dumps({"cycle": "2026-06-16r_cross_asset",
        "mode": "Lane B report-only; cross-asset first board; NO-LOOKAHEAD enforced; NON-WIRED",
        "instrument_overlap": ov, "mode1_confirmation": m1, "mode2_standalone": m2,
        "confirmation_edges": conf_edges, "overfit_risk": overfit,
        "boundaries": "no activation/registry/scheduler/portfolio/order mutation"}, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)
    print("(report-only; no activation/registry/scheduler/portfolio/order mutation)", flush=True)


if __name__ == "__main__":
    run()
