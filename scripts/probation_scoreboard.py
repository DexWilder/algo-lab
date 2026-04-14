#!/usr/bin/env python3
"""FQL Probation Scoreboard — compact promotion/demotion decision surface.

Shows every probationary strategy with forward evidence, drift checks,
and contribution analysis. Designed to answer: "who's earning their slot?"

Usage:
    python3 scripts/probation_scoreboard.py              # Print report
    python3 scripts/probation_scoreboard.py --save       # Print + save to inbox
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TRADE_LOG = ROOT / "logs" / "trade_log.csv"
SIGNAL_LOG = ROOT / "logs" / "signal_log.csv"
REGISTRY_PATH = ROOT / "research" / "data" / "strategy_registry.json"
OUTPUT_PATH = Path.home() / "openclaw-intake" / "inbox" / "_probation_scoreboard.md"

NOW = datetime.now().strftime("%Y-%m-%d %H:%M")
TODAY = datetime.now().strftime("%Y-%m-%d")

# ── Probation targets (from PROBATION_REVIEW_CRITERIA.md) ──
TARGETS = {
    "DailyTrend-MGC-Long":           {"trades": 15, "pf": 1.2, "horizon": "daily",    "review": "Week 8"},
    "MomPB-6J-Long-US":              {"trades": 30, "pf": 1.2, "horizon": "intraday", "review": "Week 8"},
    # FXBreak-6J-Short-London removed 2026-04-14: archived with verified
    # concentration-catastrophe failure mode (top-3=98.7%, max-year=112.6%).
    # See docs/PROBATION_REVIEW_CRITERIA.md §3.
    "PreFOMC-Drift-Equity":          {"trades": 8,  "pf": 1.2, "horizon": "event",    "review": "After 4 FOMC events"},
    "TV-NFP-High-Low-Levels":        {"trades": 8,  "pf": 1.1, "horizon": "event",    "review": "After 4 NFP events (~Jul 2026)"},
    "NoiseBoundary-MNQ-Long":        {"trades": 30, "pf": 1.2, "horizon": "intraday", "review": "Week 8"},
    "Treasury-Rolldown-Carry-Spread": {"trades": 8, "pf": 1.1, "horizon": "monthly",  "review": "June 1 displacement"},
    "ZN-Afternoon-Reversion":        {"trades": 30, "pf": 1.1, "horizon": "intraday", "review": "~Oct 2026"},
    "VolManaged-EquityIndex-Futures": {"trades": 30, "pf": 1.0, "horizon": "daily",    "review": "30 forward days, Sharpe > 0.5"},
}

# Expected signal frequencies (trades per month)
EXPECTED_FREQ = {
    "DailyTrend-MGC-Long":       2.0,
    "MomPB-6J-Long-US":          8.0,
    # FXBreak-6J-Short-London: archived 2026-04-14 (see TARGETS note).
    "PreFOMC-Drift-Equity":      0.67,
    "TV-NFP-High-Low-Levels":    0.8,
    "NoiseBoundary-MNQ-Long":    5.0,
    "Treasury-Rolldown-Carry-Spread": 0.2,
    "ZN-Afternoon-Reversion":    3.75,
    "VolManaged-EquityIndex-Futures": 21.0,  # Always-in, daily rebalance = ~21 trading days/month
}


# ── Probation aging: max weeks before a decision is forced ──
# After this many weeks, strategy must promote, extend (once), or remove.
MAX_PROBATION_WEEKS = {
    "DailyTrend-MGC-Long":           16,
    "MomPB-6J-Long-US":              16,
    # FXBreak-6J-Short-London: archived 2026-04-14 (see TARGETS note).
    "PreFOMC-Drift-Equity":          24,  # Event — slow cadence
    "TV-NFP-High-Low-Levels":        24,  # Event — slow cadence
    "NoiseBoundary-MNQ-Long":        16,
    "Treasury-Rolldown-Carry-Spread": 48, # Monthly — very slow cadence
    "ZN-Afternoon-Reversion":        24,  # ~3-4/month, HIGH_VOL dependent
    "VolManaged-EquityIndex-Futures": 12, # Daily — fast evidence
}


def compute_aging(sid, trades, registry):
    """Compute probation aging status for a strategy.

    Returns dict with:
        days_in_probation, weeks_in_probation, max_weeks,
        expected_trades_by_now, actual_trades, evidence_ratio,
        aging_status: TOO_EARLY | HEALTHY_SLOW | ON_TRACK | UNDER_EVIDENCED | STALE | FAILING
    """
    reg_entry = registry.get(sid, {})

    # Find probation entry date
    entry_date = None
    for h in reg_entry.get("state_history", []):
        if h.get("to") == "probation":
            entry_date = h.get("date")
    if not entry_date:
        entry_date = reg_entry.get("last_review_date", TODAY)

    try:
        entry_dt = datetime.strptime(entry_date, "%Y-%m-%d")
    except (ValueError, TypeError):
        entry_dt = datetime.now()

    days = (datetime.now() - entry_dt).days
    weeks = days / 7.0
    max_weeks = MAX_PROBATION_WEEKS.get(sid, 16)

    # Actual forward trades
    st = trades[trades["strategy"] == sid] if not trades.empty else pd.DataFrame()
    actual = len(st)

    # Expected trades by now (based on expected frequency and time elapsed)
    expected_freq = EXPECTED_FREQ.get(sid, 5.0)  # trades/month
    months_elapsed = max(days / 30.0, 0.1)
    expected_by_now = expected_freq * months_elapsed
    target = TARGETS.get(sid, {}).get("trades", 30)

    # Evidence ratio: actual / expected (1.0 = on track, <0.5 = under-evidenced)
    evidence_ratio = actual / expected_by_now if expected_by_now > 0 else 0

    # PF check for strategies with enough trades
    pf = None
    if actual >= 10 and not st.empty:
        w = st[st["pnl"] > 0]["pnl"].sum()
        l = abs(st[st["pnl"] < 0]["pnl"].sum())
        pf = w / l if l > 0 else 99.0

    # Status classification
    if days < 7:
        status = "TOO_EARLY"
    elif days < 14 and actual < 3:
        status = "TOO_EARLY"
    elif actual >= target:
        # Enough trades for a verdict
        target_pf = TARGETS.get(sid, {}).get("pf", 1.0)
        if pf is not None and pf < 0.9:
            status = "FAILING"
        elif pf is not None and pf >= target_pf:
            status = "GATE_REACHED"
        else:
            status = "REVIEW_READY"
    elif evidence_ratio >= 0.7:
        status = "ON_TRACK"
    elif evidence_ratio >= 0.3:
        # Check if this is a genuinely slow strategy or under-performing
        if expected_freq < 1.0:
            status = "HEALTHY_SLOW"  # Event/monthly — slow is expected
        else:
            status = "UNDER_EVIDENCED"
    elif days > 28 and actual == 0 and expected_freq >= 2.0:
        status = "STALE"  # Should have trades by now but doesn't
    elif expected_freq < 1.0:
        status = "HEALTHY_SLOW"  # Sparse event — patience required
    else:
        status = "UNDER_EVIDENCED"

    # Time pressure
    pct_time_used = weeks / max_weeks * 100 if max_weeks > 0 else 0

    return {
        "days_in_probation": days,
        "weeks_in_probation": round(weeks, 1),
        "max_weeks": max_weeks,
        "pct_time_used": round(pct_time_used, 0),
        "expected_by_now": round(expected_by_now, 1),
        "actual_trades": actual,
        "evidence_ratio": round(evidence_ratio, 2),
        "aging_status": status,
        "entry_date": entry_date,
        "pf": round(pf, 2) if pf is not None else None,
    }


def load_trades():
    if not TRADE_LOG.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(TRADE_LOG)
        df["date"] = pd.to_datetime(df["date"])
        return df
    except Exception:
        return pd.DataFrame()


def load_signals():
    if not SIGNAL_LOG.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(SIGNAL_LOG)
        df["date"] = pd.to_datetime(df["date"])
        return df
    except Exception:
        return pd.DataFrame()


def load_registry():
    if not REGISTRY_PATH.exists():
        return {}
    reg = json.load(open(REGISTRY_PATH))
    result = {}
    for s in reg.get("strategies", []):
        if s.get("status") == "probation":
            result[s["strategy_id"]] = s
    return result


def compute_forward_stats(trades, sid):
    st = trades[trades["strategy"] == sid] if not trades.empty else pd.DataFrame()
    if st.empty:
        return {
            "trades": 0, "pnl": 0, "pf": None, "wr": None, "avg_pnl": None,
            "long_n": 0, "long_pnl": 0, "short_n": 0, "short_pnl": 0,
            "first": None, "last": None, "maxdd": 0,
        }
    n = len(st)
    pnl = st["pnl"].sum()
    w = st[st["pnl"] > 0]["pnl"].sum()
    l = abs(st[st["pnl"] < 0]["pnl"].sum())
    pf = round(w / l, 2) if l > 0 else None
    wr = round((st["pnl"] > 0).sum() / n * 100, 1)
    eq = st["pnl"].cumsum()
    maxdd = round((eq.cummax() - eq).max(), 2)

    longs = st[st.get("side", pd.Series()) == "long"] if "side" in st.columns else pd.DataFrame()
    shorts = st[st.get("side", pd.Series()) == "short"] if "side" in st.columns else pd.DataFrame()

    return {
        "trades": n, "pnl": round(pnl, 2),
        "pf": pf, "wr": wr, "avg_pnl": round(pnl / n, 2),
        "long_n": len(longs), "long_pnl": round(longs["pnl"].sum(), 2) if not longs.empty else 0,
        "short_n": len(shorts), "short_pnl": round(shorts["pnl"].sum(), 2) if not shorts.empty else 0,
        "first": st["date"].min().strftime("%Y-%m-%d"),
        "last": st["date"].max().strftime("%Y-%m-%d"),
        "maxdd": maxdd,
    }


def compute_signal_drift(signals, sid):
    """Check if signal frequency matches expectations."""
    st = signals[signals["strategy"] == sid] if not signals.empty else pd.DataFrame()
    if st.empty or sid not in EXPECTED_FREQ:
        return {"logged_days": 0, "signal_days": 0, "actual_freq": None, "drift": None}

    logged_days = len(st)
    signal_days = (st["signals_total"] > 0).sum() if "signals_total" in st.columns else 0

    if logged_days < 5:
        return {"logged_days": logged_days, "signal_days": int(signal_days),
                "actual_freq": None, "drift": "INSUFFICIENT_DATA"}

    # Estimate actual monthly frequency
    date_range = (st["date"].max() - st["date"].min()).days
    months = max(date_range / 30.0, 0.5)
    actual_freq = round(signal_days / months, 2) if months > 0 else 0
    expected = EXPECTED_FREQ[sid]

    if actual_freq < expected * 0.5:
        drift = "LOW"
    elif actual_freq > expected * 2.0:
        drift = "HIGH"
    else:
        drift = "NORMAL"

    return {
        "logged_days": logged_days,
        "signal_days": int(signal_days),
        "actual_freq": actual_freq,
        "expected_freq": expected,
        "drift": drift,
    }


def compute_portfolio_contribution(trades):
    """Compute daily PnL correlation between each probation strategy and the rest."""
    if trades.empty:
        return {}

    # Pivot: daily PnL per strategy
    daily = trades.pivot_table(index="date", columns="strategy", values="pnl", aggfunc="sum").fillna(0)

    probation_sids = set(TARGETS.keys()) & set(daily.columns)
    non_probation = [c for c in daily.columns if c not in probation_sids]

    if not non_probation:
        return {}

    portfolio_pnl = daily[non_probation].sum(axis=1)
    result = {}
    for sid in probation_sids:
        if sid in daily.columns:
            strat_pnl = daily[sid]
            overlap_days = ((strat_pnl != 0) & (portfolio_pnl != 0)).sum()
            if overlap_days >= 5:
                corr = round(strat_pnl.corr(portfolio_pnl), 3)
                # Marginal: does adding this strategy improve total PnL?
                total_with = (portfolio_pnl + strat_pnl).sum()
                total_without = portfolio_pnl.sum()
                marginal = round(total_with - total_without, 2)
                result[sid] = {
                    "correlation": corr,
                    "marginal_pnl": marginal,
                    "overlap_days": int(overlap_days),
                    "additive": marginal > 0,
                }
            else:
                result[sid] = {"correlation": None, "overlap_days": int(overlap_days),
                               "marginal_pnl": None, "additive": None}
    return result


def generate_report():
    trades = load_trades()
    signals = load_signals()
    registry = load_registry()
    contributions = compute_portfolio_contribution(trades)

    lines = []
    lines.append("# FQL Probation Scoreboard")
    lines.append(f"*Generated: {NOW}*")
    lines.append(f"*Probation strategies: {len(registry)}*")

    # ── Main scoreboard ──
    lines.append("")
    lines.append("## Scoreboard")
    lines.append("")
    lines.append("| Strategy | Fwd Trades | Target | Fwd PnL | PF | Target PF | Status | Aging |")
    lines.append("|----------|-----------|--------|---------|----|-----------|---------| ------|")

    aging_data = {}
    for sid in sorted(TARGETS.keys()):
        t = TARGETS[sid]
        s = compute_forward_stats(trades, sid)
        a = compute_aging(sid, trades, registry)
        aging_data[sid] = a

        pf_str = f"{s['pf']:.2f}" if s['pf'] is not None else "—"
        pnl_str = f"${s['pnl']:+,.0f}" if s['trades'] > 0 else "—"

        # Status from aging logic (replaces old manual classification)
        status_map = {
            "TOO_EARLY": "Too early",
            "HEALTHY_SLOW": "Healthy/slow",
            "ON_TRACK": "On track",
            "UNDER_EVIDENCED": "**Under-ev**",
            "STALE": "**STALE**",
            "FAILING": "**FAILING**",
            "GATE_REACHED": "**GATE**",
            "REVIEW_READY": "Review",
        }
        status = status_map.get(a["aging_status"], a["aging_status"])

        # Aging: time used as percentage of max probation window
        aging_str = f"{a['pct_time_used']:.0f}% ({a['weeks_in_probation']:.0f}w/{a['max_weeks']}w)"

        lines.append(
            f"| {sid:<38s} | {s['trades']:>9d} | {t['trades']:>6d} | "
            f"{pnl_str:>7s} | {pf_str:>4s} | >{t['pf']:<9} | {status:<9s} | {aging_str} |"
        )

    # ── Caveat flags ──
    lines.append("")
    lines.append("## Flags & Caveats")
    lines.append("")

    for sid in sorted(TARGETS.keys()):
        reg = registry.get(sid, {})
        flags = []

        # Event cadence
        ec = reg.get("event_cadence", {})
        if ec.get("cadence_class") == "sparse_event":
            flags.append(f"Sparse event ({ec.get('trades_per_month', '?')}/month) — extended vitality window")

        # Short-side dependence
        if sid == "ZN-Afternoon-Reversion":
            s = compute_forward_stats(trades, sid)
            if s["trades"] >= 10:
                if s["short_pnl"] <= 0:
                    flags.append("**SHORT SIDE NOT CARRYING** — investigate")
                elif s["short_n"] > 0 and s["trades"] > 0:
                    short_pct = s["short_pnl"] / s["pnl"] * 100 if s["pnl"] != 0 else 0
                    if short_pct < 60:
                        flags.append(f"Short bias weaker than backtest ({short_pct:.0f}% vs 89%)")
            else:
                flags.append("Short-side check pending (need 10+ trades)")

        # HIGH_VOL dependence
        if sid == "ZN-Afternoon-Reversion":
            flags.append("HIGH_VOL dependent — expect quiet periods in calm markets")

        # VolManaged-specific checks
        if sid == "VolManaged-EquityIndex-Futures":
            flags.append("MICRO/REDUCED only — crisis DD not yet confirmed in forward")
            flags.append("Long-only MES — adds to 2.7:1 long bias (unique sizing mechanism justifies)")
            s = compute_forward_stats(trades, sid)
            if s["trades"] >= 1 and s["maxdd"] > 3000:
                flags.append(f"**FLAG:** Forward DD ${s['maxdd']:,.0f} — check if crisis-level")

        # Missing bar caveat
        if sid in ("ZN-Afternoon-Reversion", "Treasury-Rolldown-Carry-Spread"):
            flags.append("~18-20% of weekdays may produce no signal (sparse ZN bars)")

        # Vitality
        vit = reg.get("edge_vitality_tier")
        if vit and vit in ("FADING", "DEAD"):
            flags.append(f"Vitality: {vit} ({reg.get('edge_vitality', '?')})")

        # Half-life
        hl = reg.get("half_life_status")
        if hl and hl in ("DECAYING", "ARCHIVE_CANDIDATE"):
            flags.append(f"Half-life: {hl}")

        if flags:
            lines.append(f"**{sid}:**")
            for f in flags:
                lines.append(f"- {f}")
            lines.append("")

    # ── Aging summary ──
    lines.append("## Probation Aging")
    lines.append("")
    lines.append("| Strategy | Days In | Expected Trades | Actual | Evidence Ratio | Status |")
    lines.append("|----------|---------|----------------|--------|----------------|--------|")

    for sid in sorted(TARGETS.keys()):
        a = aging_data.get(sid, compute_aging(sid, trades, registry))
        exp_str = f"{a['expected_by_now']:.0f}"
        ratio_str = f"{a['evidence_ratio']:.2f}"
        status_markers = {
            "STALE": "**STALE** ◄",
            "UNDER_EVIDENCED": "**Under-ev** ◄",
            "FAILING": "**FAILING** ◄",
            "GATE_REACHED": "GATE ✓",
        }
        status_str = status_markers.get(a["aging_status"], a["aging_status"])
        lines.append(
            f"| {sid:<38s} | {a['days_in_probation']:>7d} | {exp_str:>14s} | "
            f"{a['actual_trades']:>6d} | {ratio_str:>14s} | {status_str} |"
        )

    lines.append("")

    # ── Signal frequency drift ──
    lines.append("## Signal Frequency vs Expectation")
    lines.append("")
    lines.append("| Strategy | Expected/mo | Actual/mo | Signal Days | Logged Days | Drift |")
    lines.append("|----------|------------|-----------|-------------|-------------|-------|")

    for sid in sorted(TARGETS.keys()):
        d = compute_signal_drift(signals, sid)
        exp = f"{EXPECTED_FREQ.get(sid, 0):.1f}"
        act = f"{d['actual_freq']:.1f}" if d['actual_freq'] is not None else "—"
        drift = d.get("drift", "—")
        drift_flag = f" ◄" if drift == "LOW" else ""
        lines.append(
            f"| {sid:<38s} | {exp:>10s} | {act:>9s} | "
            f"{d['signal_days']:>11d} | {d['logged_days']:>11d} | {drift}{drift_flag} |"
        )

    # ── ZN Challenger Contribution ──
    lines.append("")
    lines.append("## ZN Challenger Contribution")
    lines.append("")

    zn_sids = ["Treasury-Rolldown-Carry-Spread", "ZN-Afternoon-Reversion"]
    zn_trades = trades[trades["strategy"].isin(zn_sids)] if not trades.empty else pd.DataFrame()

    if zn_trades.empty or len(zn_trades) < 3:
        lines.append("Insufficient forward data for contribution analysis. Waiting for trades.")
    else:
        lines.append("| Strategy | Fwd PnL | Correlation w/ Portfolio | Marginal PnL | Additive? | Overlap Days |")
        lines.append("|----------|---------|------------------------|-------------|-----------|-------------|")

        for sid in zn_sids:
            s = compute_forward_stats(trades, sid)
            c = contributions.get(sid, {})
            corr_str = f"{c['correlation']:.3f}" if c.get('correlation') is not None else "—"
            marg_str = f"${c['marginal_pnl']:+,.0f}" if c.get('marginal_pnl') is not None else "—"
            add_str = "Yes" if c.get('additive') else ("No" if c.get('additive') is False else "—")
            overlap = c.get('overlap_days', 0)
            pnl_str = f"${s['pnl']:+,.0f}" if s['trades'] > 0 else "—"
            lines.append(f"| {sid:<38s} | {pnl_str:>7s} | {corr_str:>22s} | {marg_str:>11s} | {add_str:>9s} | {overlap:>11d} |")

        # Cross-correlation between the two ZN strategies
        if not zn_trades.empty:
            daily_zn = zn_trades.pivot_table(index="date", columns="strategy", values="pnl", aggfunc="sum")
            if all(s in daily_zn.columns for s in zn_sids):
                both = daily_zn.dropna(subset=zn_sids)
                if len(both) >= 5:
                    cross_corr = round(both[zn_sids[0]].corr(both[zn_sids[1]]), 3)
                    lines.append(f"\nCross-correlation (Rolldown vs Afternoon-Rev): {cross_corr}")
                    if abs(cross_corr) > 0.35:
                        lines.append("**FLAG:** Cross-correlation > 0.35 — check for hidden overlap")
                    else:
                        lines.append("Cross-correlation acceptable — strategies appear independent")

    # ── Review timeline ──
    lines.append("")
    lines.append("## Review Timeline")
    lines.append("")
    lines.append("| Strategy | Next Review | Gate |")
    lines.append("|----------|------------|------|")
    for sid in sorted(TARGETS.keys()):
        t = TARGETS[sid]
        lines.append(f"| {sid:<38s} | {t['review']:<20s} | {t['trades']} trades, PF > {t['pf']} |")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="FQL Probation Scoreboard")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    report = generate_report()
    print(report)

    if args.save:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_PATH, "w") as f:
            f.write(report)
        print(f"\n  Saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
