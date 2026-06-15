"""Cycle 2026-06-15h — Rates relative-value PAIRS engine v1 (new mechanism family).

Lane B / REPORT-ONLY full-search. Unblocks harvest #01/#02/#03/#04 (non-equity
relative-value pairs) — testable NOW on existing ZN/ZF/ZB data. New family:
single-instrument engine had no 2-leg support. No promotion/wiring/mutation.

Mechanism (cointegration/z-band reversion, harvest-aligned):
  - align two rates contracts on datetime (inner join, RTH+Globex 5m).
  - dollar values: value = close * point_value.
  - trailing hedge ratio h via OLS of value_A on value_B over BETA_WIN (no lookahead).
  - dollar spread = value_A - h*value_B; z over Z_WIN (trailing).
  - entry when flat and |z| > Z_ENTRY (z>0 -> short spread; z<0 -> long spread);
    hedge h fixed at entry. exit when |z| < Z_EXIT or z crosses sign.
  - per-trade $PnL on both legs minus per-leg costs (A=1 contract, B=|h| contracts).
  RV spreads are inherently multi-day holds -> overnight exposure reported honestly.

Defaults are standard (no tuning); a param sweep is a follow-up if v1 shows life.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from research.fql_forge_batch_runner import _metrics  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import get_cost_params  # noqa: E402

PAIRS = [("ZN", "ZF"), ("ZN", "ZB"), ("ZF", "ZB")]
BETA_WIN, Z_WIN = 500, 100
Z_ENTRY, Z_EXIT = 2.0, 0.5


def _load(asset):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")[["datetime", "close"]]
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df.rename(columns={"close": asset})


def _leg_cost(asset, contracts):
    c = get_cost_params(asset)
    pv = ASSETS[asset]["point_value"]
    per_contract = c["commission_per_side"] + c["slippage_ticks"] * c["tick_size"] * pv
    return per_contract * abs(contracts)


def screen_pair(a, b):
    da, db = _load(a), _load(b)
    m = da.merge(db, on="datetime", how="inner").dropna().reset_index(drop=True)
    if len(m) < BETA_WIN + Z_WIN + 100:
        return {"pair": f"{a}/{b}", "error": "insufficient_overlap", "n_bars": len(m)}
    pv_a, pv_b = ASSETS[a]["point_value"], ASSETS[b]["point_value"]
    va = m[a].values * pv_a
    vb = m[b].values * pv_b
    n = len(m)
    # trailing rolling OLS hedge ratio h = cov(va,vb)/var(vb) over BETA_WIN (ending at t-1)
    s_va, s_vb = pd.Series(va), pd.Series(vb)
    cov = s_va.rolling(BETA_WIN).cov(s_vb)
    var = s_vb.rolling(BETA_WIN).var()
    h = (cov / var).shift(1).values  # shift -> use info up to t-1 (no lookahead)
    spread = va - h * vb
    sp = pd.Series(spread)
    z = ((sp - sp.rolling(Z_WIN).mean()) / sp.rolling(Z_WIN).std()).values
    dt = pd.to_datetime(m["datetime"])

    trades = []
    pos = 0; e_i = None; e_h = None
    cost_a = _leg_cost(a, 1)
    for i in range(BETA_WIN + Z_WIN, n):
        zi = z[i]
        if np.isnan(zi) or np.isnan(h[i]):
            continue
        if pos == 0:
            if zi > Z_ENTRY or zi < -Z_ENTRY:
                pos = -1 if zi > 0 else 1   # z>0: A rich -> short spread
                e_i, e_h = i, h[i]
        else:
            revert = abs(zi) < Z_EXIT
            flip = (pos == -1 and zi < 0) or (pos == 1 and zi > 0)
            if revert or flip:
                # realize trade PnL ($), legs: A=1 contract dir=pos; B=-e_h*pos contracts
                dval_a = (va[i] - va[e_i])
                dval_b = (vb[i] - vb[e_i])
                gross = pos * (dval_a - e_h * dval_b)
                costs = 2 * (cost_a + _leg_cost(b, e_h))  # entry+exit, both legs
                trades.append({"entry_time": dt.iloc[e_i], "exit_time": dt.iloc[i],
                               "pnl": gross - costs})
                pos = 0; e_i = e_h = None
    if not trades:
        return {"pair": f"{a}/{b}", "n": 0, "note": "no trades"}
    tdf = pd.DataFrame(trades)
    mt = _metrics(tdf, f"{a}/{b}-RVpair")
    et = pd.to_datetime(tdf["entry_time"]); xt = pd.to_datetime(tdf["exit_time"])
    overnight = int((xt.dt.date > et.dt.date).sum())
    largest_day = round(float(tdf["pnl"].groupby(et.dt.date).sum().min()), 2)
    hold_bars_med = None
    pf = mt.get("pf"); h1 = mt.get("h1_pf"); h2 = mt.get("h2_pf")
    return {
        "pair": f"{a}/{b}", "n": int(mt.get("n", 0)),
        "pf": round(float(pf), 3) if pf == pf else None,
        "median": round(float(mt.get("median", 0)), 2),
        "net": round(float(mt.get("net", 0)), 2),
        "win_rate_pct": round(float(mt.get("win_rate_pct", 0)), 1),
        "max_year_share_pct": round(float(mt.get("max_year_share_pct", 0)), 1),
        "h1_pf": round(float(h1), 3) if h1 == h1 else None,
        "h2_pf": round(float(h2), 3) if h2 == h2 else None,
        "overnight_holds": overnight, "pct_overnight": round(100 * overnight / len(tdf), 1),
        "largest_day_loss": largest_day,
        "archetype": mt.get("archetype"), "gate_verdict": mt.get("gate_verdict"),
    }


def run():
    print("Cycle 2026-06-15h — Rates RV pairs engine v1 (REPORT-ONLY, new family)\n", flush=True)
    print(f"params: beta_win={BETA_WIN} z_win={Z_WIN} z_entry={Z_ENTRY} z_exit={Z_EXIT}\n", flush=True)
    rows = []
    for a, b in PAIRS:
        r = screen_pair(a, b)
        rows.append(r)
        if "error" in r or r.get("n", 0) == 0:
            print(f"  {r['pair']}: {r.get('error') or r.get('note')}", flush=True)
        else:
            print(f"  {r['pair']:8s} n={r['n']:>4} PF={r['pf']} median=${r['median']} "
                  f"WR={r['win_rate_pct']}% maxyr={r['max_year_share_pct']}% "
                  f"H1/H2={r['h1_pf']}/{r['h2_pf']} ON={r['pct_overnight']}% "
                  f"dayLoss=${r['largest_day_loss']} -> {r['gate_verdict']}", flush=True)
    ok = [r for r in rows if "error" not in r and r.get("n", 0) >= 30]
    interesting = [r for r in ok if r.get("pf") and r["pf"] >= 1.3
                   and r.get("h1_pf") and r.get("h2_pf") and r["h1_pf"] > 1.0 and r["h2_pf"] > 1.0
                   and r["max_year_share_pct"] <= 50]
    print("\n=== SUMMARY ===", flush=True)
    print(f"  pairs screened: {len(ok)} | candidates (PF>=1.3, both halves>1, conc<=50%): {len(interesting)}", flush=True)
    for r in interesting:
        print(f"   ** {r['pair']}: PF={r['pf']} n={r['n']} median=${r['median']} maxyr={r['max_year_share_pct']}%", flush=True)
    if not interesting:
        print("   (none clear the bar at default params; a z-band/window sweep is the follow-up if any show life)", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-15h_rates_pairs_engine.json"
    out.write_text(json.dumps({
        "cycle": "2026-06-15h_rates_pairs_engine", "mode": "Lane B report-only (new family)",
        "params": {"beta_win": BETA_WIN, "z_win": Z_WIN, "z_entry": Z_ENTRY, "z_exit": Z_EXIT},
        "results": rows, "candidates": interesting,
        "note": "v1 default params, no tuning. RV spreads hold multi-day (overnight exposure reported). "
                "Unblocks harvest #01-04. If any pair shows life, follow-up = param sweep + Kalman hedge + ADF/Hurst gate.",
        "boundaries": "report-only; no promotion/wiring/mutation; canonical feeds untouched",
    }, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)


if __name__ == "__main__":
    run()
