"""Cycle 2026-06-11r — Final robustness on WH-MNQ-stop_run_reversal +
WH-MNQ-range_compression_break + coexistence/exposure matrix.

Per operator #181 nonstop order:
  1. WH-MNQ-stop_run_reversal final robustness (primary daily foundation)
  2. WH-MNQ-range_compression_break final robustness (secondary)
  3. Combined coexistence/portfolio exposure table

Robustness checks per operator (workhorse-adapted):
  - year exclusion (leave-one-year-out)
  - half split / era split
  - Era 3 PF and median
  - remove largest win / largest loss
  - rolling window PF (per 60-trade block)
  - max-year share
  - max-month / max-week share
  - stress cost/slippage ladder
  - day-of-week dependence
  - time-of-day dependence
  - correlation to XB-ORB-MNQ probation
  - pairwise correlation between the 2 candidates
  - median survival under stress

Boundaries: report-only Lane B.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from research.crossbreeding.crossbreeding_engine import generate_crossbred_signals  # noqa: E402
from research.event_window_engine import generate_event_window_signals  # noqa: E402
from research.forge_fomc_calendar_official import build_official_fomc_calendar  # noqa: E402
from research.forge_nfp_calendar_verify import build_verified_nfp_calendar  # noqa: E402
from research.fql_forge_batch_runner import _metrics  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import run_backtest, get_cost_params  # noqa: E402


def _pf(pnl):
    arr = np.asarray(pnl)
    w = arr[arr > 0].sum(); l = -arr[arr < 0].sum()
    return float(w / l) if l > 0 else float("inf")


def _run_xb(asset, entry, exit_name, filter_name, label, cost_mult=1.0, slip_mult=1.0):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    cfg = ASSETS[asset]
    costs = get_cost_params(asset)
    sigs = generate_crossbred_signals(df, entry_name=entry, exit_name=exit_name,
                                       filter_name=filter_name, params={})
    res = run_backtest(df, sigs, mode="both", point_value=cfg["point_value"], symbol=asset,
                       commission_per_side=costs["commission_per_side"] * cost_mult,
                       slippage_ticks=int(np.ceil(costs["slippage_ticks"] * slip_mult)),
                       tick_size=costs["tick_size"])
    return _metrics(res["trades_df"], label, costs=res["stats"]["costs"]), res["trades_df"]


def _run_event(asset, events, exit_bars, direction, label):
    df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
    cfg = ASSETS[asset]
    costs = get_cost_params(asset)
    sigs = generate_event_window_signals(df, events=events, entry_offset_bars=1,
                                          exit_offset_bars=exit_bars, direction=direction)
    res = run_backtest(df, sigs, mode="both", point_value=cfg["point_value"], symbol=asset,
                       commission_per_side=costs["commission_per_side"],
                       slippage_ticks=costs["slippage_ticks"], tick_size=costs["tick_size"])
    return _metrics(res["trades_df"], label, costs=res["stats"]["costs"]), res["trades_df"]


def strict_filter(events, df, max_gap_minutes=60):
    df_dt = pd.to_datetime(df["datetime"])
    clean = []
    for ev in events:
        if ev < df_dt.iloc[0]: continue
        after = df[df_dt > ev].head(1)
        if len(after) == 0: continue
        gap_min = (pd.to_datetime(after["datetime"].iloc[0]) - ev).total_seconds() / 60
        if gap_min <= max_gap_minutes: clean.append(ev)
    return clean


def family_corr(trades_a, trades_b):
    if trades_a.empty or trades_b.empty: return float("nan"), float("nan")
    da = trades_a.copy(); da["entry_dt"] = pd.to_datetime(da["entry_time"]); da["date"] = da["entry_dt"].dt.date
    db = trades_b.copy(); db["entry_dt"] = pd.to_datetime(db["entry_time"]); db["date"] = db["entry_dt"].dt.date
    pa = da.groupby("date")["pnl"].sum(); pb = db.groupby("date")["pnl"].sum()
    aligned = pd.concat([pa, pb], axis=1, keys=["a", "b"]).fillna(0.0)
    corr = float(aligned["a"].corr(aligned["b"]))
    overlap = set(da["date"]) & set(db["date"])
    return corr, len(overlap) / len(set(da["date"])) * 100 if da.shape[0] else 0


def robustness_check(asset, entry, label):
    """Full workhorse robustness check."""
    print(f"\n=== ROBUSTNESS: {label} ===", flush=True)
    m, trades = _run_xb(asset, entry, "profit_ladder", "ema_slope", label)
    trades = trades.copy()
    trades["entry_dt"] = pd.to_datetime(trades["entry_time"])
    trades["year"] = trades["entry_dt"].dt.year
    trades["month"] = trades["entry_dt"].dt.to_period("M")
    trades["week"] = trades["entry_dt"].dt.to_period("W")
    trades["dow"] = trades["entry_dt"].dt.day_name()
    trades["hour"] = trades["entry_dt"].dt.hour

    pnls = trades["pnl"].values
    net = float(pnls.sum())

    print(f"  Baseline: n={m['n']} PF={m['pf']:.3f} median=${m['median']:.2f} net=${net:.0f}", flush=True)

    # Year exclusion
    yr_excl = {}
    for y in sorted(trades["year"].unique()):
        sub = trades[trades["year"] != y]
        yr_excl[int(y)] = {"pf": _pf(sub["pnl"]), "median": float(np.median(sub["pnl"]))}
    yr_pfs = [v["pf"] for v in yr_excl.values()]
    print(f"  Year-excl PF range: [{min(yr_pfs):.3f}, {max(yr_pfs):.3f}]", flush=True)

    # Era split (3 thirds)
    sorted_trades = trades.sort_values("entry_dt").reset_index(drop=True)
    cuts = np.linspace(0, len(sorted_trades), 4).astype(int)
    eras = []
    for i in range(3):
        sub = sorted_trades.iloc[cuts[i]:cuts[i+1]]
        pnl = sub["pnl"].values
        eras.append({"era": i+1, "n": len(sub), "pf": _pf(pnl),
                     "median": float(np.median(pnl)), "net": float(pnl.sum())})
    for e in eras:
        print(f"  Era {e['era']}: n={e['n']} PF={e['pf']:.3f} median=${e['median']:.2f} net=${e['net']:.0f}", flush=True)

    # Largest win/loss removal
    max_idx = trades["pnl"].idxmax(); min_idx = trades["pnl"].idxmin()
    max_pnl = trades.loc[max_idx, "pnl"]; min_pnl = trades.loc[min_idx, "pnl"]
    max_event = trades.loc[max_idx, "entry_time"]; min_event = trades.loc[min_idx, "entry_time"]
    pf_no_max = _pf(trades[trades.index != max_idx]["pnl"].values)
    pf_no_min = _pf(trades[trades.index != min_idx]["pnl"].values)
    print(f"  Largest win:  ${max_pnl:+.2f} @ {max_event} → remove: PF {pf_no_max:.3f}", flush=True)
    print(f"  Largest loss: ${min_pnl:+.2f} @ {min_event} → remove: PF {pf_no_min:.3f}", flush=True)
    max_event_abs_share = max(abs(max_pnl), abs(min_pnl)) / net * 100 if net != 0 else 0
    max_is_loss = abs(min_pnl) > abs(max_pnl)
    print(f"  Max abs event share: {max_event_abs_share:.1f}% (max is {'LOSS' if max_is_loss else 'WIN'})", flush=True)

    # Rolling 60-trade block PF
    block_size = 60
    n_blocks = len(sorted_trades) // block_size
    block_pfs = []
    for i in range(n_blocks):
        block = sorted_trades.iloc[i*block_size:(i+1)*block_size]
        block_pfs.append(_pf(block["pnl"].values))
    block_pfs_arr = np.array([p for p in block_pfs if not np.isinf(p)])
    pct_pos = float((block_pfs_arr > 1.0).mean() * 100) if len(block_pfs_arr) else 0
    pct_strong = float((block_pfs_arr > 1.2).mean() * 100) if len(block_pfs_arr) else 0
    worst_block = float(block_pfs_arr.min()) if len(block_pfs_arr) else float("nan")
    print(f"  Rolling 60-trade blocks: {n_blocks} blocks, {pct_pos:.0f}% > 1.0 PF, {pct_strong:.0f}% > 1.2 PF, worst {worst_block:.3f}", flush=True)

    # Max-year share, max-month, max-week
    per_year_net = trades.groupby("year")["pnl"].sum()
    max_yr_share = float(per_year_net.abs().max() / net * 100) if net != 0 else 0
    per_month_net = trades.groupby("month")["pnl"].sum()
    max_mo_share = float(per_month_net.abs().max() / net * 100) if net != 0 else 0
    per_week_net = trades.groupby("week")["pnl"].sum()
    max_wk_share = float(per_week_net.abs().max() / net * 100) if net != 0 else 0
    print(f"  Max-year share: {max_yr_share:.1f}%, max-month: {max_mo_share:.1f}%, max-week: {max_wk_share:.1f}%", flush=True)

    # Day-of-week
    dow_stats = {}
    for d, g in trades.groupby("dow"):
        dow_stats[d] = {"n": int(len(g)), "pf": _pf(g["pnl"].values),
                        "median": float(np.median(g["pnl"])),
                        "net": float(g["pnl"].sum())}
    dow_pfs = {d: s["pf"] for d, s in dow_stats.items()}
    print(f"  Day-of-week PFs: {{{', '.join(f'{d[:3]}={pf:.2f}' for d, pf in sorted(dow_pfs.items()))}}}",
          flush=True)

    # Time-of-day
    tod_stats = {}
    for h, g in trades.groupby("hour"):
        tod_stats[int(h)] = {"n": int(len(g)), "pf": _pf(g["pnl"].values)}
    tod_parts = [f"{h}h={s['pf']:.2f}" for h, s in sorted(tod_stats.items())[:8]]
    print(f"  Time-of-day PFs: {', '.join(tod_parts)}", flush=True)
    tod_summary = {str(h): s for h, s in sorted(tod_stats.items())}

    # Stress cost ladder
    cost_sens = []
    for cm, sm, lab in [(1.0, 1.0, "baseline"), (1.5, 2.0, "1.5x+1t"),
                          (2.0, 3.0, "2x+2t"), (3.0, 3.0, "3x+2t"),
                          (4.0, 4.0, "4x+3t"), (5.0, 5.0, "5x+4t")]:
        m_s, _ = _run_xb(asset, entry, "profit_ladder", "ema_slope", f"{label}-stress",
                          cost_mult=cm, slip_mult=sm)
        cost_sens.append({"label": lab, "pf": float(m_s["pf"]),
                          "median": float(m_s["median"])})
    print(f"  Stress: " + " | ".join(f"{c['label']}: PF {c['pf']:.3f} med ${c['median']:.2f}"
                                       for c in cost_sens), flush=True)

    # Robustness checks
    median_survives = cost_sens[2]["median"] > 0  # 2x+2t
    extreme_survives = cost_sens[5]["pf"] > 0.8  # 5x+4t
    rob_checks = {
        "year_excl_min_PF_>=_1.2": min(yr_pfs) >= 1.2,
        "Era3_PF_>=_1.0": eras[2]["pf"] >= 1.0,
        "Era3_median_>=_0": eras[2]["median"] >= 0,
        "rolling_blocks_>1.0_PF_>_60%": pct_pos > 60,
        "remove_largest_win_PF_>_1.15": pf_no_max >= 1.15,
        "remove_largest_loss_PF_>_1.15": pf_no_min >= 1.15,
        "max_yr_share_<=_50": max_yr_share <= 50,
        "max_event_share_<=_15_or_LOSS_TAIL_ABSORPTION":
            max_event_abs_share <= 15 or (max_is_loss and pf_no_min > m["pf"]),
        "stress_2x+2t_median_>_0": median_survives,
        "stress_5x+4t_PF_>_0.8": extreme_survives,
    }
    print(f"  Robustness checks: {rob_checks}", flush=True)
    all_pass = all(rob_checks.values())
    if all_pass:
        verdict = "ROBUSTNESS GREEN — confirmed PAPER_PACKET_CANDIDATE"
    elif max_is_loss and not (max_event_abs_share <= 15) and pf_no_min > m["pf"] and sum(rob_checks.values()) >= 9:
        verdict = "PASS_WITH_LOSS_TAIL_WARN (per V1.1 Amendment B)"
    else:
        failed = [k for k, v in rob_checks.items() if not v]
        verdict = f"ROBUSTNESS PARTIAL — failed: {failed}"
    print(f"  Verdict: {verdict}", flush=True)

    return {
        "label": label, "asset": asset, "entry": entry,
        "baseline": {"n": int(m["n"]), "pf": float(m["pf"]), "median": float(m["median"]), "net": net},
        "year_exclusion": yr_excl,
        "year_excl_pf_range": [min(yr_pfs), max(yr_pfs)],
        "eras": eras,
        "largest_event_removal": {
            "max_pnl": float(max_pnl), "max_event": str(max_event),
            "pf_no_max": pf_no_max,
            "min_pnl": float(min_pnl), "min_event": str(min_event),
            "pf_no_min": pf_no_min,
            "max_event_abs_share_pct": max_event_abs_share,
            "max_is_loss": bool(max_is_loss),
        },
        "rolling_60_trade_blocks": {
            "n_blocks": n_blocks, "pct_>_1.0": pct_pos,
            "pct_>_1.2": pct_strong, "worst": worst_block,
        },
        "concentration": {"max_yr_share_pct": max_yr_share,
                          "max_month_share_pct": max_mo_share,
                          "max_week_share_pct": max_wk_share},
        "day_of_week": dow_stats,
        "time_of_day": tod_summary,
        "stress_ladder": cost_sens,
        "robustness_checks": rob_checks,
        "all_pass": all_pass,
        "verdict": verdict,
        "trades": trades,  # for downstream coexistence
    }


def run():
    print("Cycle 2026-06-11r — Daily workhorse final robustness + coexistence matrix\n", flush=True)
    t_start = time.time()

    # 1. WH-MNQ-stop_run_reversal
    rob_stop = robustness_check("MNQ", "stop_run_reversal", "WH-MNQ-stop_run_reversal")
    # 2. WH-MNQ-range_compression_break
    rob_rcb = robustness_check("MNQ", "range_compression_break", "WH-MNQ-range_compression_break")

    # 3. Coexistence/exposure matrix
    print(f"\n=== COEXISTENCE/EXPOSURE MATRIX ===", flush=True)
    # Build reference trade sets
    _, t_orb_mnq = _run_xb("MNQ", "orb_breakout", "profit_ladder", "ema_slope", "XB-ORB-MNQ")
    _, t_bbkc = _run_xb("MNQ", "bb_keltner_squeeze", "profit_ladder", "ema_slope", "BBKC-MNQ")
    fomc_events = [pd.to_datetime(f"{c['actual_date']} {c['actual_time_et']}")
                   for c in build_official_fomc_calendar()]
    df_mnq = pd.read_csv(ROOT / "data" / "processed" / "MNQ_5m.csv")
    fomc_clean = strict_filter(fomc_events, df_mnq)
    _, t_fomc = _run_event("MNQ", fomc_clean, 12, "long", "FOMC-MNQ")
    df_mgc = pd.read_csv(ROOT / "data" / "processed" / "MGC_5m.csv")
    nfp_events = [pd.to_datetime(f"{c['actual_date']} 08:30:00")
                  for c in build_verified_nfp_calendar(2019, 2026)]
    nfp_clean = strict_filter(nfp_events, df_mgc)
    _, t_packet1 = _run_event("MGC", nfp_clean, 24, "long", "NFP-MGC")

    coexistence = {}
    refs = [
        ("WH_stop_run", rob_stop["trades"]),
        ("WH_range_compression", rob_rcb["trades"]),
        ("XB_ORB_MNQ_probation", t_orb_mnq),
        ("FOMC_MNQ_Long_1h", t_fomc),
        ("Packet1_NFP_MGC_archive", t_packet1),
        ("BBKC_MNQ_archive", t_bbkc),
    ]
    print(f"\n  Pairwise daily-PnL correlation matrix:", flush=True)
    print(f"  {'':<26} " + " ".join(f"{r[0][:10]:>11}" for r in refs), flush=True)
    for name_a, t_a in refs:
        row = []
        for name_b, t_b in refs:
            if name_a == name_b: row.append(1.0)
            else:
                c, _ = family_corr(t_a, t_b)
                row.append(c)
        coexistence[name_a] = {refs[i][0]: row[i] for i in range(len(refs))}
        print(f"  {name_a:<26} " + " ".join(f"{v:>+11.3f}" for v in row), flush=True)

    # Strip trades from serializable
    for r in (rob_stop, rob_rcb):
        r.pop("trades", None)

    total = time.time() - t_start
    print(f"\nTotal: {total:.0f}s", flush=True)

    out = ROOT / "research" / "data" / "fql_forge" / "reports" / "forge_cycle_2026-06-11r_workhorse_final_robustness.json"
    out.write_text(json.dumps({
        "date": date.today().isoformat(),
        "purpose": "Daily workhorse final robustness + coexistence matrix per #181 nonstop",
        "stop_run_reversal_robustness": rob_stop,
        "range_compression_break_robustness": rob_rcb,
        "coexistence_correlation_matrix": coexistence,
    }, indent=2, default=str))
    print(f"\nWrote: {out}", flush=True)


if __name__ == "__main__":
    run()
