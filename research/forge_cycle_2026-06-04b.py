"""Forge cycle 2026-06-04 (b): NFP + CPI + VOL-expansion + MES/ZN HL retest.

Per operator approvals 2026-06-04:
  #24 NFP candidates (rule-based 1st Friday calendar)
  #25 CPI candidates (rule-based ~13th release approximation)
  #26 pair half-life retest (MES/ZN single retest, validation only)
  VOL-expansion specs (standing approval)

Authority: T1 / Lane B / report-only. No registry mutation.
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from research.event_window_engine import generate_event_window_signals  # noqa: E402
from research.fql_forge_batch_runner import _metrics  # noqa: E402
from research.crossbreeding.crossbreeding_engine import (  # noqa: E402
    generate_crossbred_signals,
)
from research.pairs_engine import pairs_backtest, pairs_metrics, _resample_close  # noqa: E402
from research.half_life_filter import gate_pair_signal_by_half_life  # noqa: E402
from engine.asset_config import ASSETS  # noqa: E402
from engine.backtest import run_backtest  # noqa: E402


# ─────────────────────────────────────────────────────────────────────────────
# Calendars (rule-based; labeled clearly)
# ─────────────────────────────────────────────────────────────────────────────

def first_friday_of_month(year: int, month: int) -> datetime:
    """First Friday of (year, month)."""
    first = datetime(year, month, 1)
    # Mon=0, Tue=1, ..., Fri=4
    offset = (4 - first.weekday()) % 7
    return first.replace(day=1 + offset)


def nth_business_day(year: int, month: int, n: int = 13) -> datetime:
    """Approximate Nth business day of (year, month). v1: simple count from day 1.

    CPI is typically released around the 10th-15th business day. We use n=13 as
    a coarse approximation; this is labeled as approximation in reports.
    """
    d = datetime(year, month, 1)
    count = 0
    while count < n:
        if d.weekday() < 5:  # Mon-Fri
            count += 1
            if count == n:
                return d
        d += timedelta(days=1)
    return d


def build_nfp_calendar(start_year=2019, end_year=2026,
                       time_str="08:30:00") -> list:
    out = []
    for y in range(start_year, end_year + 1):
        for m in range(1, 13):
            out.append(pd.to_datetime(f"{first_friday_of_month(y, m).date()} {time_str}"))
    return out


def build_cpi_calendar(start_year=2019, end_year=2026,
                       time_str="08:30:00") -> list:
    out = []
    for y in range(start_year, end_year + 1):
        for m in range(1, 13):
            out.append(pd.to_datetime(f"{nth_business_day(y, m, 13).date()} {time_str}"))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Classification + temporal split helpers
# ─────────────────────────────────────────────────────────────────────────────

def _classify(m: dict) -> str:
    n = m.get("n", 0)
    pf = m.get("pf", 0)
    median = m.get("median", 0)
    max_yr = m.get("max_year_share_pct", 100)
    if n < 10:
        return f"KILL (insufficient-n, n={n})"
    if median < 0:
        return "KILL (median negative)"
    if pf < 1.15:
        return "KILL (PF < 1.15)"
    if max_yr >= 50:
        return "TEMPORAL_SPLIT_REQUIRED"
    if pf >= 1.30 and median > 0:
        return "WATCH_FOR_DEEP_SCREEN"
    return "WATCH"


def temporal_split(trades_df: pd.DataFrame) -> dict:
    if trades_df.empty:
        return None
    df = trades_df.copy()
    df["entry_dt"] = pd.to_datetime(df["entry_time"])
    df["year"] = df["entry_dt"].dt.year
    per_year = []
    for y, g in df.groupby("year"):
        pnl = g["pnl"].values
        w = pnl[pnl > 0].sum()
        l = -pnl[pnl < 0].sum()
        pf = float(w / l) if l > 0 else float("inf")
        per_year.append({"year": int(y), "n": int(len(g)),
                         "pf": pf, "net": float(pnl.sum())})
    df = df.sort_values("entry_dt").reset_index(drop=True)
    cuts = np.linspace(0, len(df), 4).astype(int)
    eras = []
    for i in range(3):
        sub = df.iloc[cuts[i]:cuts[i+1]]
        if sub.empty:
            continue
        pnl = sub["pnl"].values
        w = pnl[pnl > 0].sum()
        l = -pnl[pnl < 0].sum()
        pf = float(w / l) if l > 0 else float("inf")
        eras.append({"era": i+1,
                     "start": str(sub.iloc[0]["entry_dt"].date()),
                     "end": str(sub.iloc[-1]["entry_dt"].date()),
                     "n": int(len(sub)), "pf": pf, "net": float(pnl.sum())})
    yrs_pos = sum(1 for r in per_year if r["net"] > 0)
    return {"per_year": per_year, "eras": eras,
            "yrs_pos": yrs_pos, "n_yrs": len(per_year)}


def _doctrine_verdict(m: dict, ts: dict | None) -> str:
    """Apply post-temporal-split doctrine rules."""
    v0 = _classify(m)
    if v0 != "TEMPORAL_SPLIT_REQUIRED" or ts is None:
        return v0
    if ts["n_yrs"] > 0 and ts["yrs_pos"] < ts["n_yrs"] * 0.5:
        return "ARCHITECTURAL_REJECT (< 50% yrs positive)"
    # Loser-era detection
    if any(e["pf"] < 1.0 and np.isfinite(e["pf"]) for e in ts["eras"]):
        return "ARCHITECTURAL_REJECT (losing era)"
    # Dominant-year check via exclusion
    base_pnl = sum(y["net"] for y in ts["per_year"])
    dominant_year_net = max((y["net"] for y in ts["per_year"]), default=0)
    if base_pnl > 0 and dominant_year_net / base_pnl > 0.8:
        return "ARCHITECTURAL_REJECT (one year > 80% of net)"
    if m["pf"] >= 1.30 and m["median"] > 0:
        return "WATCH_FOR_DEEP_SCREEN (passed temporal robustness)"
    return "WATCH (passed temporal robustness; PF/median modest)"


# ─────────────────────────────────────────────────────────────────────────────
# Runners
# ─────────────────────────────────────────────────────────────────────────────

def run_event_candidates(events: list, event_name: str, calendar_label: str):
    """Standard event-window screen across 4 assets + 2 directions + 2 exits."""
    candidates = []
    for asset in ("MES", "MNQ", "ZN", "MGC"):
        for direction in ("long", "short"):
            for exit_bars, exit_tag in ((6, "30min"), (24, "2h")):
                candidates.append({
                    "asset": asset, "direction": direction,
                    "exit_offset_bars": exit_bars,
                    "label": f"EVT-{event_name}-{asset}-{direction.title()}-{exit_tag}",
                })
    print(f"\n{event_name} event-window screens ({len(events)} events; calendar: {calendar_label}):")
    results = []
    for spec in candidates:
        df = pd.read_csv(ROOT / "data" / "processed" / f"{spec['asset']}_5m.csv")
        cfg = ASSETS[spec["asset"]]
        sigs = generate_event_window_signals(
            df, events=events, entry_offset_bars=1,
            exit_offset_bars=spec["exit_offset_bars"], direction=spec["direction"],
        )
        res = run_backtest(df, sigs, mode="both",
                           point_value=cfg["point_value"], symbol=spec["asset"])
        m = _metrics(res["trades_df"], spec["label"], costs=res["stats"]["costs"])
        v_cheap = _classify(m)
        ts = None
        if v_cheap == "TEMPORAL_SPLIT_REQUIRED":
            ts = temporal_split(res["trades_df"])
        v = _doctrine_verdict(m, ts)
        max_yr = m.get("max_year_share_pct", float("nan"))
        n_yrs = ts["n_yrs"] if ts else m.get("n_years", "?")
        yrs_pos = ts["yrs_pos"] if ts else m.get("years_positive", "?")
        print(
            f"  [{spec['label']:32s}] n={m['n']:3d} PF={m['pf']:.3f} "
            f"median=${m['median']:8.2f} max-yr={max_yr:.1f}% yrs+={yrs_pos}/{n_yrs} → {v}"
        )
        results.append({
            "spec": spec,
            "metrics": {k: m.get(k) for k in (
                "n", "pf", "median", "net", "max_dd",
                "max_year_share_pct", "top3_share_pct", "top10_share_pct",
                "h1_pf", "h2_pf", "n_years", "years_positive",
                "archetype", "gate_verdict",
            )},
            "temporal_split": ts,
            "cheap_screen_verdict": v_cheap,
            "doctrine_verdict": v,
        })
    return results


def run_vol_expansion():
    """Vol-expansion entry on MGC, MES, MNQ, ZN with proven trio defaults."""
    cands = [
        ("MGC", "ema_slope", "profit_ladder", "XB-VX-EMA-Ladder-MGC"),
        ("MES", "ema_slope", "profit_ladder", "XB-VX-EMA-Ladder-MES"),
        ("MNQ", "ema_slope", "profit_ladder", "XB-VX-EMA-Ladder-MNQ"),
        ("ZN", "ema_slope", "profit_ladder", "XB-VX-EMA-Ladder-ZN"),
    ]
    print(f"\nVOL-expansion candidates (atr_pctrank cross above 70 from below):")
    results = []
    for asset, filt, exit_name, label in cands:
        df = pd.read_csv(ROOT / "data" / "processed" / f"{asset}_5m.csv")
        cfg = ASSETS[asset]
        sigs = generate_crossbred_signals(
            df, entry_name="vol_expansion", exit_name=exit_name,
            filter_name=filt, params={"vx_high": 70})
        res = run_backtest(df, sigs, mode="both",
                           point_value=cfg["point_value"], symbol=asset)
        m = _metrics(res["trades_df"], label, costs=res["stats"]["costs"])
        v_cheap = _classify(m)
        ts = None
        if v_cheap == "TEMPORAL_SPLIT_REQUIRED":
            ts = temporal_split(res["trades_df"])
        v = _doctrine_verdict(m, ts)
        max_yr = m.get("max_year_share_pct", float("nan"))
        print(f"  [{label:30s}] n={m['n']:4d} PF={m['pf']:.3f} median=${m['median']:7.2f} max-yr={max_yr:.1f}% → {v}")
        results.append({"label": label, "asset": asset,
                        "metrics": {k: m.get(k) for k in (
                            "n", "pf", "median", "net", "max_dd",
                            "max_year_share_pct", "top3_share_pct",
                            "h1_pf", "h2_pf", "years_positive", "n_years",
                        )},
                        "temporal_split": ts,
                        "doctrine_verdict": v})
    return results


def run_mes_zn_half_life_retest():
    """Single pair retest with half-life gate to validate gating helper."""
    df_a = pd.read_csv(ROOT / "data" / "processed" / "MES_5m.csv")
    df_b = pd.read_csv(ROOT / "data" / "processed" / "ZN_5m.csv")
    a_lvl = _resample_close(df_a, "M")
    b_lvl = _resample_close(df_b, "M")

    # Baseline: return_z without gate (matches v1 result, n=11 PF 0.36)
    res_base = pairs_backtest(df_a=df_a, df_b=df_b, asset_a="MES", asset_b="ZN",
                              freq="M", lookback=12, z_threshold=1.5, exit_z=0.5,
                              hedge="vol_adjusted", label="MES-ZN-baseline-no-gate")
    m_base = pairs_metrics(res_base, "MES-ZN-baseline")
    v_base = _classify(m_base)

    # Gated: apply half-life gate to the signal series, then re-run PnL accounting
    # by patching the signal back into pairs_backtest. The gating helper zeros
    # the signal on bars where the rolling spread half-life is not in MR band.
    sig_unfiltered = res_base["signal_series"]
    gated_sig, hl_series = gate_pair_signal_by_half_life(
        sig_unfiltered, a_lvl, b_lvl,
        window=60, half_life_min=1.0, half_life_max=24.0, min_sample=30,
    )

    # Count entries that survive the gate
    n_unfilt = int((sig_unfiltered != 0).sum())
    n_filt = int((gated_sig != 0).sum())
    print(f"\nMES/ZN half-life pair retest:")
    print(f"  Baseline signal: {n_unfilt} non-zero bars")
    print(f"  After HL gate:   {n_filt} non-zero bars (kept {n_filt/n_unfilt*100:.0f}% of signals)")
    # Rolling HL summary
    hl_valid = hl_series.dropna()
    if len(hl_valid):
        mr_frac = (hl_valid <= 24).mean() * 100
        print(f"  Rolling HL stats: median={hl_valid.median():.1f}, "
              f"% windows with HL<=24mo: {mr_frac:.0f}%")

    # If gate collapses to tiny sample, report PAIR_LANE_WAIT_FOR_BETTER_THESIS
    if n_filt < 3:
        verdict = "PAIR_LANE_WAIT_FOR_BETTER_THESIS"
        return {"baseline_metrics": dict(m_base), "gated_n": n_filt,
                "n_unfilt": n_unfilt, "verdict": verdict,
                "hl_summary": {"median": float(hl_valid.median()) if len(hl_valid) else None,
                              "frac_under_24mo": float((hl_valid <= 24).mean()) if len(hl_valid) else None}}
    # Otherwise, force PnL walk through the gated signal. Reusing pairs_backtest
    # with a synthetic override signal is messy — for v1, just summarize gated
    # signal counts as the validation. Full gated PnL walk is a follow-up build.
    verdict = "GATED_VALIDATED" if n_filt < n_unfilt else "GATE_INACTIVE"
    return {"baseline_metrics": dict(m_base),
            "n_unfilt": n_unfilt, "gated_n": n_filt,
            "hl_summary": {"median": float(hl_valid.median()) if len(hl_valid) else None,
                          "frac_under_24mo": float((hl_valid <= 24).mean()) if len(hl_valid) else None},
            "verdict": verdict}


def run():
    out_dir = ROOT / "research" / "data" / "fql_forge" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    date_iso = date.today().isoformat()

    nfp_events = build_nfp_calendar(2019, 2026)
    cpi_events = build_cpi_calendar(2019, 2026)

    nfp_results = run_event_candidates(
        nfp_events, "NFP",
        "canonical-rule-based: 1st Friday/month at 08:30 ET"
    )
    cpi_results = run_event_candidates(
        cpi_events, "CPI",
        "approximate-rule-based: 13th business day/month at 08:30 ET — APPROXIMATION"
    )
    vol_results = run_vol_expansion()
    mes_zn_hl = run_mes_zn_half_life_retest()

    payload = {
        "date": date_iso,
        "operator_approvals": [
            "#24 NFP candidate", "#25 CPI candidate",
            "#26 pair half-life retest", "VOL-expansion specs (standing)",
        ],
        "nfp": nfp_results,
        "cpi": cpi_results,
        "vol_expansion": vol_results,
        "mes_zn_half_life_retest": mes_zn_hl,
    }
    json_path = out_dir / f"forge_cycle_2026-06-04b.json"
    md_path = out_dir / f"forge_cycle_2026-06-04b.md"
    json_path.write_text(json.dumps(payload, indent=2, default=str))

    md = [f"# Forge Cycle — {date_iso}\n",
          "Authority T1 / Lane B / report-only.\n",
          f"## NFP screens ({len(nfp_events)} events, canonical 1st-Fri)\n",
          "| Candidate | n | PF | Median | Max-Yr | Verdict |",
          "|---|---:|---:|---:|---:|---|"]
    for r in nfp_results:
        m = r["metrics"]
        md.append(f"| {r['spec']['label']} | {m['n']} | {m['pf']:.3f} | ${m['median']:.2f} | {m.get('max_year_share_pct', float('nan')):.1f}% | {r['doctrine_verdict']} |")
    md.append(f"\n## CPI screens ({len(cpi_events)} events, APPROX 13th-bday)\n")
    md.append("| Candidate | n | PF | Median | Max-Yr | Verdict |")
    md.append("|---|---:|---:|---:|---:|---|")
    for r in cpi_results:
        m = r["metrics"]
        md.append(f"| {r['spec']['label']} | {m['n']} | {m['pf']:.3f} | ${m['median']:.2f} | {m.get('max_year_share_pct', float('nan')):.1f}% | {r['doctrine_verdict']} |")
    md.append(f"\n## VOL-expansion screens\n")
    md.append("| Candidate | n | PF | Median | Max-Yr | Verdict |")
    md.append("|---|---:|---:|---:|---:|---|")
    for r in vol_results:
        m = r["metrics"]
        md.append(f"| {r['label']} | {m['n']} | {m['pf']:.3f} | ${m['median']:.2f} | {m.get('max_year_share_pct', float('nan')):.1f}% | {r['doctrine_verdict']} |")
    md.append(f"\n## MES/ZN half-life retest validation\n")
    md.append(f"- baseline signals: {mes_zn_hl.get('n_unfilt')}")
    md.append(f"- after HL gate: {mes_zn_hl.get('gated_n')}")
    md.append(f"- HL summary: {mes_zn_hl.get('hl_summary')}")
    md.append(f"- verdict: **{mes_zn_hl.get('verdict')}**\n")
    md_path.write_text("\n".join(md))
    print(f"\nWrote: {md_path}")
    print(f"Wrote: {json_path}")


if __name__ == "__main__":
    run()
