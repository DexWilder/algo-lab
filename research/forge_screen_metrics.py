"""Forge cheap-screen metric pack — Phase 1 upgrade (2026-05-28).

Single source of truth for the upgraded cheap-screen output. Every candidate
emits the same full minimum gate set at intake, so concentration / median /
walk-forward asymmetry / archetype-mismatch issues that took multiple
post-hoc audits to surface (MYM, Chandelier) are visible immediately.

Used by `research/fql_forge_batch_runner.py:_metrics` and any other code path
that wants intake-grade screening.

Output shape: see `compute_full_screen_metrics` docstring.
Verdict semantics: PASS_TO_FORWARD_CLOCK / MUTATE / DEFER / KILL.
"""

import numpy as np
import pandas as pd


# ── Gate thresholds (single source of truth for cheap-screen verdicts) ────

GATES = {
    # workhorse path
    "workhorse_pf_min": 1.20,
    "workhorse_median_min": 0.0,
    "workhorse_top3_max": 30.0,
    "workhorse_top10_max": 55.0,
    "workhorse_max_year_max": 40.0,
    "workhorse_h_pf_min": 1.0,
    "workhorse_trade_min": 500,
    # tail-engine path
    "tail_pf_viable": 1.15,
    "tail_pf_strong": 1.30,
    "tail_max_single_max": 35.0,
    "tail_trade_min_sample": 30,
    # payoff-ratio at workhorse frequency (Track 2 / Chandelier pattern)
    "payoff_pf_min": 1.20,
    "payoff_years_positive_fraction_min": 0.75,
    # universal KILL conditions — only structural failures, not reformulation cases
    "kill_pf_below": 1.0,
    "kill_cost_ratio_above": 50.0,
    "kill_years_positive_fraction_below": 0.5,
    # Note: concentration failures (max-year, top-3, top-10) are DEFER, not KILL.
    # A high-concentration candidate may be saved by regime filter / session
    # split / year-stratification work — that's reformulation, not edge denial.
}


# ── Metric computation ────────────────────────────────────────────────────

def compute_full_screen_metrics(trades_df, cost_block=None, entry_time_col="entry_time"):
    """Compute the full cheap-screen metric set from a trades DataFrame.

    Returns dict with all keys in the Phase 1 intake spec:
        n, net, pf, median, mean, win_rate_pct, max_dd,
        cost_ratio_pct, max_single_pct,
        top3_share_pct, top10_share_pct, max_year_share_pct,
        n_years, years_positive,
        h1_pf, h2_pf, h1_median, h2_median,
        cost_block

    Returns None if trades_df is empty (caller should handle).
    """
    if trades_df is None or len(trades_df) == 0:
        return None
    pnl = trades_df["pnl"].values
    n = len(pnl)
    net = float(pnl.sum())

    gp = float(pnl[pnl > 0].sum())
    gl = float(abs(pnl[pnl < 0].sum()))
    pf = (gp / gl) if gl > 0 else float("inf")
    median = float(np.median(pnl))
    mean = float(pnl.mean())
    win_rate = float((pnl > 0).mean() * 100)

    eq = np.cumsum(pnl)
    max_dd = float((eq - np.maximum.accumulate(eq)).min())

    # Cost ratio: friction-per-trade as % of gross avg trade
    cb = cost_block or {}
    total_friction = float(cb.get("total_friction", 0))
    if total_friction > 0 and n > 0:
        gross_pnl = net + total_friction
        cost_ratio = (total_friction / gross_pnl * 100) if gross_pnl > 0 else None
    else:
        cost_ratio = None

    # Concentration: top-K share of net PnL (only meaningful if net > 0)
    sorted_pnl = np.sort(pnl)[::-1]  # descending
    if net > 0:
        top3 = float(sorted_pnl[:3].sum() / net * 100)
        top10 = float(sorted_pnl[:10].sum() / net * 100)
    else:
        top3 = top10 = 0.0
    abs_total = float(np.abs(pnl).sum())
    max_single = float(np.abs(pnl).max() / abs_total * 100) if abs_total > 0 else 0.0

    # Year share + years_positive
    td = trades_df.copy()
    try:
        td["__year"] = pd.to_datetime(td[entry_time_col]).dt.year
        yearly = td.groupby("__year")["pnl"].sum()
        yearly_sum = float(yearly.sum())
        max_year_share = float(yearly.max() / yearly_sum * 100) if yearly_sum > 0 else 0.0
        n_years = int(len(yearly))
        years_positive = int((yearly > 0).sum())
    except Exception:
        max_year_share = 0.0
        n_years = 0
        years_positive = 0

    # Walk-forward H1/H2 (date midpoint split)
    try:
        td_sorted = td.sort_values(entry_time_col).reset_index(drop=True)
        mid = len(td_sorted) // 2
        h1 = td_sorted.iloc[:mid]["pnl"].values
        h2 = td_sorted.iloc[mid:]["pnl"].values
        def half_pf(p):
            w = float(p[p > 0].sum())
            l = float(abs(p[p < 0].sum()))
            return (w / l) if l > 0 else float("inf")
        h1_pf = half_pf(h1)
        h2_pf = half_pf(h2)
        h1_median = float(np.median(h1)) if len(h1) else 0.0
        h2_median = float(np.median(h2)) if len(h2) else 0.0
    except Exception:
        h1_pf = h2_pf = float("nan")
        h1_median = h2_median = 0.0

    return {
        "n": n,
        "net": round(net, 2),
        "pf": round(pf, 3) if pf != float("inf") else pf,
        "median": round(median, 2),
        "mean": round(mean, 2),
        "win_rate_pct": round(win_rate, 1),
        "max_dd": round(max_dd, 2),
        "cost_ratio_pct": round(cost_ratio, 1) if cost_ratio is not None else None,
        "max_single_pct": round(max_single, 1),
        "top3_share_pct": round(top3, 1),
        "top10_share_pct": round(top10, 1),
        "max_year_share_pct": round(max_year_share, 1),
        "n_years": n_years,
        "years_positive": years_positive,
        "h1_pf": round(h1_pf, 3) if h1_pf != float("inf") else h1_pf,
        "h2_pf": round(h2_pf, 3) if h2_pf != float("inf") else h2_pf,
        "h1_median": round(h1_median, 2),
        "h2_median": round(h2_median, 2),
        "cost_block": cb,
    }


# ── Archetype classification ──────────────────────────────────────────────

ARCHETYPES = (
    "WORKHORSE",
    "TAIL_ENGINE",
    "PAYOFF_RATIO_WORKHORSE_FREQUENCY",
    "EVENT_DRIVEN",
    "PORTFOLIO_OVERLAY",
    "UNKNOWN",
)


def classify_archetype(metrics, hint=None):
    """Auto-classify candidate archetype based on shape of metrics.

    hint can be 'EVENT_DRIVEN' or 'PORTFOLIO_OVERLAY' to override auto-detect
    for strategies whose archetype is known from metadata (e.g. NFP event-
    driven, vol-managed overlay).
    """
    if hint in ("EVENT_DRIVEN", "PORTFOLIO_OVERLAY"):
        return hint
    n = metrics["n"]
    median = metrics["median"]
    mean = metrics["mean"]

    if n == 0:
        return "UNKNOWN"
    if n < GATES["workhorse_trade_min"]:
        return "TAIL_ENGINE" if mean > 0 else "UNKNOWN"
    # n >= 500 territory
    if median >= 0 and mean > 0:
        return "WORKHORSE"
    if median < 0 and mean > 0:
        return "PAYOFF_RATIO_WORKHORSE_FREQUENCY"
    return "UNKNOWN"


# ── Gate verdict ──────────────────────────────────────────────────────────

VERDICTS = ("PASS_TO_FORWARD_CLOCK", "MUTATE", "DEFER", "KILL")


def gate_verdict(metrics, archetype):
    """Return (verdict, blocker_reason).

    Verdicts:
        PASS_TO_FORWARD_CLOCK — all archetype-appropriate gates clean
        MUTATE — a single named gate fails but is fixable via a controlled
                 variant (PF below gate, negative median in supposed workhorse)
        DEFER — concentration / walk-forward / archetype-framework gap; not
                kill, not pass — needs out-of-band resolution
        KILL — structurally failing (PF<1.0, extreme concentration, mostly
               negative years)
    """
    n = metrics["n"]
    pf = metrics["pf"]
    median = metrics["median"]
    top3 = metrics["top3_share_pct"]
    top10 = metrics["top10_share_pct"]
    max_year = metrics["max_year_share_pct"]
    h1_pf = metrics["h1_pf"]
    h2_pf = metrics["h2_pf"]
    n_years = metrics["n_years"]
    years_pos = metrics["years_positive"]
    cost_ratio = metrics["cost_ratio_pct"]
    max_single = metrics["max_single_pct"]

    # Universal KILL conditions (structural failures only — not reformulation cases)
    if pf < GATES["kill_pf_below"]:
        return "KILL", f"PF {pf:.2f} < 1.0 (not profitable)"
    if cost_ratio is not None and cost_ratio > GATES["kill_cost_ratio_above"]:
        return "KILL", f"cost ratio {cost_ratio:.1f}% > {GATES['kill_cost_ratio_above']:.0f}% (cost eats edge)"
    if n_years > 0 and (years_pos / n_years) < GATES["kill_years_positive_fraction_below"]:
        return "KILL", f"only {years_pos}/{n_years} years positive (<50%)"

    if archetype == "WORKHORSE":
        if pf < GATES["workhorse_pf_min"]:
            return "MUTATE", f"PF {pf:.2f} < workhorse gate {GATES['workhorse_pf_min']}; try exit/filter variant"
        if median < GATES["workhorse_median_min"]:
            return "MUTATE", f"negative median ${median:.2f}; try exit change or reclassify as payoff-ratio"
        if top3 > GATES["workhorse_top3_max"]:
            return "DEFER", f"top-3 {top3:.1f}% > {GATES['workhorse_top3_max']:.0f}% gate"
        if top10 > GATES["workhorse_top10_max"]:
            return "DEFER", f"top-10 {top10:.1f}% > {GATES['workhorse_top10_max']:.0f}% gate"
        if max_year > GATES["workhorse_max_year_max"]:
            return "DEFER", f"max-year {max_year:.1f}% > {GATES['workhorse_max_year_max']:.0f}% gate (MYM-style)"
        if h1_pf < GATES["workhorse_h_pf_min"] or h2_pf < GATES["workhorse_h_pf_min"]:
            return "DEFER", f"walk-forward H1={h1_pf:.2f} H2={h2_pf:.2f} — not both above 1.0"
        return "PASS_TO_FORWARD_CLOCK", None

    if archetype == "TAIL_ENGINE":
        if n < GATES["tail_trade_min_sample"]:
            return "DEFER", f"only {n} trades — below tail-engine sample minimum {GATES['tail_trade_min_sample']}"
        if pf < GATES["tail_pf_viable"]:
            return "MUTATE", f"PF {pf:.2f} < tail-engine VIABLE gate {GATES['tail_pf_viable']}"
        if max_single > GATES["tail_max_single_max"]:
            return "DEFER", f"max single-trade share {max_single:.1f}% > {GATES['tail_max_single_max']:.0f}% (single-trade dominance)"
        if max_year > GATES["workhorse_max_year_max"]:
            return "DEFER", f"max-year {max_year:.1f}% > {GATES['workhorse_max_year_max']:.0f}% gate"
        return "PASS_TO_FORWARD_CLOCK", None

    if archetype == "PAYOFF_RATIO_WORKHORSE_FREQUENCY":
        # Track 2 archetype: structurally negative median is OK by design,
        # but concentration + walk-forward + multi-year positivity must hold.
        if pf < GATES["payoff_pf_min"]:
            return "MUTATE", f"PF {pf:.2f} < {GATES['payoff_pf_min']} even for payoff-ratio archetype"
        if top3 > GATES["workhorse_top3_max"]:
            return "DEFER", f"top-3 {top3:.1f}% > {GATES['workhorse_top3_max']:.0f}% gate"
        if top10 > GATES["workhorse_top10_max"]:
            return "DEFER", f"top-10 {top10:.1f}% > {GATES['workhorse_top10_max']:.0f}% gate"
        if max_year > GATES["workhorse_max_year_max"]:
            return "DEFER", f"max-year {max_year:.1f}% > {GATES['workhorse_max_year_max']:.0f}% gate"
        if h1_pf < GATES["workhorse_h_pf_min"] or h2_pf < GATES["workhorse_h_pf_min"]:
            return "DEFER", f"walk-forward H1={h1_pf:.2f} H2={h2_pf:.2f} — not both above 1.0"
        if n_years > 0 and (years_pos / n_years) < GATES["payoff_years_positive_fraction_min"]:
            return "DEFER", f"only {years_pos}/{n_years} years positive (<{GATES['payoff_years_positive_fraction_min']*100:.0f}%)"
        # Payoff-ratio passes go to Track 2 (forward clock) per 2026-05-28 doctrine
        return "PASS_TO_FORWARD_CLOCK", "archetype=PAYOFF_RATIO_WORKHORSE_FREQUENCY — Track 2 only, not paper-eligible without archetype review"

    if archetype == "EVENT_DRIVEN":
        return "DEFER", "event-driven archetype — per-event decomposition required before forward-clock"

    if archetype == "PORTFOLIO_OVERLAY":
        return "DEFER", "portfolio-overlay archetype (e.g. vol-managed) — needs marginal-Sharpe contribution framework, not per-trade gates"

    # UNKNOWN
    return "DEFER", f"archetype UNKNOWN (n={n}, median={median:.2f}, mean={mean:.2f}) — manual classification needed"


# ── Convenience entry point ───────────────────────────────────────────────

def screen(trades_df, cost_block=None, archetype_hint=None, entry_time_col="entry_time"):
    """One-shot: metrics + archetype + verdict in a single call.

    Returns dict with all metric fields plus:
        archetype: str
        gate_verdict: str
        blocker_reason: str or None

    Returns None if trades_df is empty.
    """
    m = compute_full_screen_metrics(trades_df, cost_block, entry_time_col)
    if m is None:
        return None
    arche = classify_archetype(m, hint=archetype_hint)
    verdict, reason = gate_verdict(m, arche)
    m["archetype"] = arche
    m["gate_verdict"] = verdict
    m["blocker_reason"] = reason
    return m
