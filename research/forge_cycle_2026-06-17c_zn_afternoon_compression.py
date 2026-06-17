"""Cycle 2026-06-17c — Claw lead #T7: ZN afternoon range-compression RELEASE (report-only).

Rates-native intraday VOL-EXPANSION mechanism (NOT ORB/donchian/dual-thrust breakout
recycling): on days where the early-afternoon range is compressed vs its own 20-day history,
trade the first afternoon break with volume confirmation, exit same-day.

Self-contained backtest (the crossbreeding engine's session window/exits can't faithfully
express the afternoon window + 15:20 flatten + midpoint/target exits). NO-LOOKAHEAD:
  - compression range from completed 13:30-14:30 bars; 20-day 25th-pct from STRICTLY PRIOR days
  - break scanned only in 14:30-15:20; entry at break-bar close; exits on SUBSEQUENT bars
Predeclared rejects: single-parameter-island only; PF lift from tiny-n or top-year concentration.
Real costs from asset_config. NO mutation; NON-WIRED.
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


def _pf(p):
    p = np.asarray(p, float); w = p[p > 0].sum(); l = -p[p < 0].sum()
    return float(w / l) if l > 0 else float("inf")


def screen(asset, pct=0.25, comp_end="14:30", break_end="15:20", flat="15:20", vol_mult=1.0):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    dt = pd.to_datetime(df["datetime"]); df["date"] = dt.dt.normalize(); df["hm"] = dt.dt.strftime("%H:%M")
    cfg = ASSETS[asset]; cp = get_cost_params(asset); pv = cfg["point_value"]
    rt = 2 * (cp["commission_per_side"] + cp["slippage_ticks"] * cp["tick_size"] * pv)

    # per-day compression range (13:30-comp_end) — completed before the break window
    comp = df[(df["hm"] >= "13:30") & (df["hm"] < comp_end)].groupby("date").agg(
        ch=("high", "max"), cl=("low", "min")).reset_index()
    comp["crange"] = comp["ch"] - comp["cl"]
    comp["pct_prior"] = comp["crange"].shift(1).rolling(20).quantile(pct)   # STRICTLY prior 20 days
    comp["compressed"] = comp["crange"] < comp["pct_prior"]
    cmap = comp.set_index("date").to_dict("index")

    trades = []
    for d, day in df.groupby("date"):
        info = cmap.get(d)
        if not info or not info["compressed"] or pd.isna(info["pct_prior"]):
            continue
        ch, cl, cr = info["ch"], info["cl"], info["crange"]
        mid = (ch + cl) / 2.0
        win = day[(day["hm"] >= comp_end) & (day["hm"] < break_end)].reset_index(drop=True)
        if len(win) < 3:
            continue
        vols = win["volume"].to_numpy(); closes = win["close"].to_numpy()
        entry_i = None; direction = 0
        for k in range(6, len(win)):
            volok = vols[k] > vol_mult * np.mean(vols[max(0, k - 6):k]) if k >= 1 else False
            if closes[k] > ch and volok:
                entry_i, direction = k, 1; break
            if closes[k] < cl and volok:
                entry_i, direction = k, -1; break
        if entry_i is None:
            continue
        entry = closes[entry_i]
        tgt = entry + direction * 1.5 * cr
        exit_px = None
        flat_rows = day[(day["hm"] >= comp_end)].reset_index(drop=True)
        # walk subsequent bars in the break/flatten window for exit
        post = win.iloc[entry_i + 1:]
        for _, b in post.iterrows():
            if b["hm"] >= flat:
                exit_px = b["close"]; break
            # midpoint retrace against position
            if (direction == 1 and b["low"] <= mid) or (direction == -1 and b["high"] >= mid):
                exit_px = mid; break
            # 1.5x range target
            if (direction == 1 and b["high"] >= tgt) or (direction == -1 and b["low"] <= tgt):
                exit_px = tgt; break
        if exit_px is None:
            exit_px = post["close"].iloc[-1] if len(post) else entry
        pnl = direction * (exit_px - entry) * pv - rt
        trades.append({"entry_time": str(d), "pnl": pnl, "dir": direction})
    return pd.DataFrame(trades)


def board(tr, asset, mnq_daily):
    if tr is None or len(tr) < 40:
        return {"asset": asset, "n": int(len(tr) if tr is not None else 0), "verdict": "KILL_low_n"}
    t = tr.copy(); t["y"] = pd.to_datetime(t["entry_time"]).dt.year
    p = t["pnl"].to_numpy(); n = len(p); net = float(p.sum()); ny = int(t["y"].nunique())
    h = n // 2
    g = t[t["pnl"] > 0]["pnl"].sort_values(ascending=False); gp = float(g.sum())
    t3 = round(float(g.head(3).sum()) / gp * 100, 1) if gp > 0 else None
    per_yr = t.groupby("y")["pnl"].sum(); maxyr = round(float(per_yr.abs().max() / net * 100), 1) if net else None
    yx = [round(_pf(t[t["y"] != y]["pnl"]), 3) for y in sorted(t["y"].unique())]
    cuts = np.linspace(0, n, 4).astype(int); st = t.sort_values("entry_time").reset_index(drop=True)
    eras = [round(_pf(st.iloc[cuts[i]:cuts[i + 1]]["pnl"]), 3) for i in range(3)]
    td = t.copy(); td["d"] = pd.to_datetime(td["entry_time"]).dt.date
    dd = td.groupby("d")["pnl"].sum()
    al = pd.concat([dd, mnq_daily], axis=1, keys=["a", "b"]).fillna(0.0); corr = round(float(al["a"].corr(al["b"])), 3)
    tpy = round(n / max(ny, 1), 1)
    quality = (_pf(p) > 1.2 and np.median(p) >= 0 and _pf(p[:h]) > 1.0 and _pf(p[h:]) > 1.0
               and (t3 or 99) < 30 and (maxyr or 99) < 40 and all(e > 1.0 for e in eras) and min(yx) > 1.15)
    v = ("KILL" if not quality else ("WATCH_corr" if abs(corr) >= 0.3
         else ("FORWARD_CLOCK_CREDIBLE" if tpy >= 30 else "WATCH_low_cadence")))
    return {"asset": asset, "n": n, "trades_per_yr": tpy, "pf": round(_pf(p), 3), "net": round(net, 0),
            "median": round(float(np.median(p)), 2), "h1_pf": round(_pf(p[:h]), 3), "h2_pf": round(_pf(p[h:]), 3),
            "max_year_pct": maxyr, "top3": t3, "era_pf": eras, "yr_excl_min": min(yx), "corr_mnq": corr, "verdict": v}


def run():
    print("Cycle 2026-06-17c — ZN afternoon range-compression release (Claw #T7) (REPORT-ONLY)\n", flush=True)
    # MNQ daily ref for correlation (close-to-close proxy is fine for a decorrelation check)
    mdf = pd.read_csv(ROOT / "data" / "processed" / "MNQ_5m.csv")
    mdt = pd.to_datetime(mdf["datetime"]); md = mdf.assign(d=mdt.dt.date).groupby("d")["close"].last()
    mnq_daily = md.diff().rename("b"); mnq_daily.index = pd.to_datetime(mnq_daily.index).date

    rows = []
    print("Base run (pct=25th, vol_mult=1.0):", flush=True)
    base = {}
    for a in ("ZN", "ZF", "ZB"):
        tr = screen(a); r = board(tr, a, mnq_daily); base[a] = r; rows.append({**r, "variant": "base"})
        print(f"  {a}: " + (f"{r['verdict']} (n={r['n']})" if r['verdict'].startswith('KILL') else
              f"{r['verdict']} n={r['n']} {r['trades_per_yr']}/yr PF={r['pf']} med=${r['median']} "
              f"H1/H2={r['h1_pf']}/{r['h2_pf']} top3={r['top3']}% maxyr={r['max_year_pct']}% corr={r['corr_mnq']}"), flush=True)

    # parameter-island check on ZN (reject if only one island works)
    print("\nParameter-island check (ZN):", flush=True)
    island = []
    for pct in (0.20, 0.25, 0.33):
        for vm in (1.0, 1.2):
            tr = screen("ZN", pct=pct, vol_mult=vm); r = board(tr, "ZN", mnq_daily)
            island.append({"pct": pct, "vol_mult": vm, "n": r.get("n"), "pf": r.get("pf"), "verdict": r["verdict"]})
            print(f"  pct={pct} vol_mult={vm}: PF={r.get('pf')} n={r.get('n')} -> {r['verdict']}", flush=True)
    pass_islands = [i for i in island if not str(i["verdict"]).startswith("KILL") and i["verdict"] != "WATCH_low_cadence"]
    robust_island = len(pass_islands) >= 3
    print(f"\n  islands passing: {len(pass_islands)}/6 -> {'ROBUST across params' if robust_island else 'SINGLE-ISLAND / fragile'}", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-17c_zn_afternoon_compression.json"
    out.write_text(json.dumps({"cycle": "2026-06-17c_zn_afternoon_compression", "mode": "Lane B report-only; self-contained no-lookahead; NON-WIRED",
        "base": base, "param_islands": island, "robust_across_params": robust_island,
        "boundaries": "no activation/registry/scheduler/portfolio/order mutation"}, indent=2, default=str))
    print(f"\nWrote: {out}\n(report-only; no mutation)", flush=True)


if __name__ == "__main__":
    run()
