"""Strategy DNA Clustering — Build profiles, cluster, and report.

Generates DNA profiles for all converted strategies using:
- Strategy source code structure
- Validation results and performance metrics
- Regime profiles from Phase 8

Outputs:
- dna_catalog.json — DNA profile for every strategy
- dna_clusters.json — Structural similarity clusters
- dna_report.md — Analysis of diversity, duplicates, and gaps

Usage:
    python3 research/dna/build_dna_profiles.py
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

OUTPUT_DIR = Path(__file__).resolve().parent

# ── Load regime profiles if available ────────────────────────────────────────
REGIME_PROFILES_PATH = PROJECT_ROOT / "research" / "regime" / "strategy_regime_profiles.json"
regime_profiles = {}
if REGIME_PROFILES_PATH.exists():
    with open(REGIME_PROFILES_PATH) as f:
        regime_profiles = json.load(f)


# ── DNA Catalog: hand-verified from strategy source + research artifacts ─────

DNA_CATALOG = [
    {
        "strategy_id": "PB-MGC-Short",
        "strategy_name": "pb_trend",
        "family": "pullback",
        "asset": "MGC",
        "mode": "short",
        "status": "deployment_ready",
        "entry_type": "pullback",
        "entry_trigger": "Price dips toward slow EMA in established trend, bounces through fast EMA with strong close (top/bottom 20% of range)",
        "confirmation_type": ["trend_filter", "adx_filter", "volume_filter", "vwap_filter", "regime_gate", "ema_filter"],
        "filter_depth": 6,
        "exit_type": "bracket",
        "exit_features": ["atr_stop", "eod_flatten"],
        "risk_model": "atr_adaptive",
        "session_window": "08:30-15:15",
        "session_restriction": "power_windows",
        "regime_dependency": {
            "preferred_regimes": regime_profiles.get("PB-MGC-Short", {}).get("preferred_regimes", []),
            "avoid_regimes": regime_profiles.get("PB-MGC-Short", {}).get("avoid_regimes", []),
            "best_regime": "HIGH_RV",
            "best_regime_pf": 4.99,
        },
        "holding_time_class": "intraday_swing",
        "direction_bias": "bidirectional",
        "trade_frequency_bucket": "rare",
        "cost_sensitivity": "low",
        "portfolio_role": "core",
        "overlap_risk": "none",
        "confidence_level": "medium",
        "key_performance": {
            "net_pf": 2.36,
            "sharpe": 5.27,
            "trades": 21,
            "maxdd": 233.48,
            "correlation_vs_portfolio": -0.009,
        },
        "structural_notes": "Extracted from Lucid v6.3. Deepest filter stack in the lab (6 layers). Only 21 gated trades — high confidence in direction, low confidence in precise PF. Power windows restrict to 08:45-11:00 + 13:30-15:10.",
    },
    {
        "strategy_id": "ORB-009-MGC-Long",
        "strategy_name": "orb_009",
        "family": "orb",
        "asset": "MGC",
        "mode": "long",
        "status": "deployment_ready",
        "entry_type": "breakout",
        "entry_trigger": "Price closes outside 30-min opening range (09:30-10:00). Long above OR_high, short below OR_low.",
        "confirmation_type": ["vwap_filter", "volume_filter", "momentum_filter"],
        "filter_depth": 3,
        "exit_type": "bracket",
        "exit_features": ["range_stop", "breakeven", "eod_flatten"],
        "risk_model": "range_based",
        "session_window": "09:30-15:15",
        "session_restriction": "full_rth",
        "regime_dependency": {
            "preferred_regimes": regime_profiles.get("ORB-009-MGC-Long", {}).get("preferred_regimes", []),
            "avoid_regimes": regime_profiles.get("ORB-009-MGC-Long", {}).get("avoid_regimes", []),
            "best_regime": "TRENDING",
            "best_regime_pf": 2.06,
        },
        "holding_time_class": "intraday_swing",
        "direction_bias": "bidirectional",
        "trade_frequency_bucket": "low",
        "cost_sensitivity": "low",
        "portfolio_role": "core",
        "overlap_risk": "none",
        "confidence_level": "high",
        "key_performance": {
            "net_pf": 2.07,
            "sharpe": 3.93,
            "trades": 75,
            "maxdd": 685.48,
            "correlation_vs_portfolio": 0.001,
        },
        "structural_notes": "Faithful conversion from luiscaballero. Range-based risk (SL at OR boundary, TP at 2x range). Breakeven at 50% TP. Most statistically robust strategy in the lab (DSR=1.000).",
    },
    {
        "strategy_id": "VIX-Channel-MES-Both",
        "strategy_name": "vix_channel",
        "family": "session",
        "asset": "MES",
        "mode": "both",
        "status": "pending_validation",
        "entry_type": "regime_detection",
        "entry_trigger": "30-min observation window determines trend direction from session open anchor. Enter in detected direction. One trade per day.",
        "confirmation_type": ["session_gate"],
        "filter_depth": 1,
        "exit_type": "channel_boundary",
        "exit_features": ["channel_exit", "atr_stop", "eod_flatten"],
        "risk_model": "rv_scaled",
        "session_window": "09:30-15:45",
        "session_restriction": "full_rth",
        "regime_dependency": {
            "preferred_regimes": regime_profiles.get("VIX-Channel-MES-Both", {}).get("preferred_regimes", []),
            "avoid_regimes": regime_profiles.get("VIX-Channel-MES-Both", {}).get("avoid_regimes", []),
            "best_regime": "LOW_VOL",
            "best_regime_pf": 1.79,
        },
        "holding_time_class": "day_trade",
        "direction_bias": "bidirectional",
        "trade_frequency_bucket": "medium",
        "cost_sensitivity": "medium",
        "portfolio_role": "regime_filler",
        "overlap_risk": "none",
        "confidence_level": "medium",
        "key_performance": {
            "net_pf": 1.298,
            "sharpe": 1.60,
            "trades": 503,
            "maxdd": 1339.57,
            "correlation_vs_portfolio": -0.024,
        },
        "structural_notes": "Unique in lab: uses realized vol proxy (VIX-like) for dynamic channel sizing. Only strategy that thrives in LOW_VOL regime. Near-zero correlation with gold portfolio. Passes 5/8 validation criteria.",
    },
    {
        "strategy_id": "GAP-MOM-MGC-Long",
        "strategy_name": "gap_mom",
        "family": "gap_momentum",
        "asset": "MGC",
        "mode": "long",
        "status": "watchlist",
        "entry_type": "gap_signal",
        "entry_trigger": "Cumulative gap series (today open - yesterday close) crosses above 20-day SMA signal line at session open.",
        "confirmation_type": ["session_gate"],
        "filter_depth": 1,
        "exit_type": "signal_reversal",
        "exit_features": ["signal_exit", "atr_stop", "eod_flatten"],
        "risk_model": "atr_adaptive",
        "session_window": "09:30-15:15",
        "session_restriction": "full_rth",
        "regime_dependency": {
            "preferred_regimes": [],
            "avoid_regimes": [],
            "best_regime": "unknown",
            "best_regime_pf": 0,
        },
        "holding_time_class": "day_trade",
        "direction_bias": "long_only",
        "trade_frequency_bucket": "rare",
        "cost_sensitivity": "low",
        "portfolio_role": "watchlist",
        "overlap_risk": "low",
        "confidence_level": "low",
        "key_performance": {
            "net_pf": 3.26,
            "sharpe": 3.67,
            "trades": 24,
            "maxdd": 518,
            "correlation_vs_portfolio": -0.01,
        },
        "structural_notes": "Perry Kaufman TASC 2024.01. Only 24 trades, top trade = 86% of PnL. Fails diversification goal (no MES/MNQ edge). MGC result interesting but single-trade dependent. Long-only bias unique in lab.",
    },
    {
        "strategy_id": "VWAP-006-MES-Long",
        "strategy_name": "vwap_006",
        "family": "vwap",
        "asset": "MES",
        "mode": "long",
        "status": "rejected",
        "entry_type": "crossover",
        "entry_trigger": "RSI(3) crosses above 30 (oversold) with EMA9 > EMA21 alignment and price above VWAP.",
        "confirmation_type": ["rsi_filter", "ema_filter", "vwap_filter"],
        "filter_depth": 3,
        "exit_type": "bracket",
        "exit_features": ["atr_stop", "eod_flatten"],
        "risk_model": "atr_adaptive",
        "session_window": "09:30-15:15",
        "session_restriction": "full_rth",
        "regime_dependency": {
            "preferred_regimes": [],
            "avoid_regimes": [],
            "best_regime": "unknown",
            "best_regime_pf": 0,
        },
        "holding_time_class": "scalp",
        "direction_bias": "bidirectional",
        "trade_frequency_bucket": "high",
        "cost_sensitivity": "high",
        "portfolio_role": "rejected",
        "overlap_risk": "moderate",
        "confidence_level": "medium",
        "key_performance": {
            "net_pf": 1.05,
            "sharpe": 1.32,
            "trades": 572,
            "maxdd": 0,
            "correlation_vs_portfolio": 0,
        },
        "structural_notes": "michaelriggs. 74% PnL eaten by friction (572 trades × high round-trip cost). Short side destroyed value. Structurally similar to any RSI+VWAP scalper — not a unique edge.",
    },
    {
        "strategy_id": "RVWAP-MR-MES-Both",
        "strategy_name": "rvwap_mr",
        "family": "mean_reversion",
        "asset": "MES",
        "mode": "both",
        "status": "rejected",
        "entry_type": "mean_reversion",
        "entry_trigger": "Price crosses back inside VWAP ± 2.0σ rolling stdev band after breaching it.",
        "confirmation_type": ["vwap_filter"],
        "filter_depth": 1,
        "exit_type": "dynamic_target",
        "exit_features": ["signal_exit", "atr_stop", "eod_flatten"],
        "risk_model": "atr_adaptive",
        "session_window": "09:30-15:15",
        "session_restriction": "full_rth",
        "regime_dependency": {
            "preferred_regimes": [],
            "avoid_regimes": [],
            "best_regime": "unknown",
            "best_regime_pf": 0,
        },
        "holding_time_class": "intraday_swing",
        "direction_bias": "bidirectional",
        "trade_frequency_bucket": "high",
        "cost_sensitivity": "high",
        "portfolio_role": "rejected",
        "overlap_risk": "high",
        "confidence_level": "medium",
        "key_performance": {
            "net_pf": 0.83,
            "sharpe": -1.83,
            "trades": 1004,
            "maxdd": 0,
            "correlation_vs_portfolio": 0,
        },
        "structural_notes": "vvedding. VWAP stdev band reversion fails completely on 5m with fill-at-next-open. 1,004 trades generates massive friction. Same structural flaw as VWAP-006: too many low-quality entries. Mean reversion thesis may need higher timeframe.",
    },
    {
        "strategy_id": "ICT-010-MES-Both",
        "strategy_name": "ict_010",
        "family": "ict",
        "asset": "MES",
        "mode": "both",
        "status": "rejected",
        "entry_type": "pullback",
        "entry_trigger": "3-phase state machine: range formation → sweep detection (wick breaks range, close recaptures) → pullback entry (close reversal pattern).",
        "confirmation_type": ["session_gate"],
        "filter_depth": 1,
        "exit_type": "fixed_points",
        "exit_features": ["fixed_stop", "eod_flatten"],
        "risk_model": "fixed_points",
        "session_window": "09:30-15:15",
        "session_restriction": "custom",
        "regime_dependency": {
            "preferred_regimes": [],
            "avoid_regimes": [],
            "best_regime": "unknown",
            "best_regime_pf": 0,
        },
        "holding_time_class": "day_trade",
        "direction_bias": "bidirectional",
        "trade_frequency_bucket": "medium",
        "cost_sensitivity": "medium",
        "portfolio_role": "rejected",
        "overlap_risk": "moderate",
        "confidence_level": "medium",
        "key_performance": {
            "net_pf": 0.65,
            "sharpe": -2.95,
            "trades": 232,
            "maxdd": 1603,
            "correlation_vs_portfolio": 0,
        },
        "structural_notes": "tradeforopp (Captain Backtest). Only strategy with FIXED stop distances (not ATR-adaptive). Sweep detection is structurally unique but unfiltered pullback entry generates noise. PF < 1.0 on all assets. Fixed stops = key failure vector.",
    },
    {
        "strategy_id": "ORION-VOL-MES-Both",
        "strategy_name": "orion_vol",
        "family": "vol_compression",
        "asset": "MES",
        "mode": "both",
        "status": "rejected",
        "entry_type": "breakout",
        "entry_trigger": "Volatility compression box (15-bar high/low). Enter on breakout above/below box when tightness + flatness filters pass. EMA150 trend gate.",
        "confirmation_type": ["compression_filter", "trend_filter"],
        "filter_depth": 2,
        "exit_type": "bracket",
        "exit_features": ["range_stop", "eod_flatten"],
        "risk_model": "compression_based",
        "session_window": "09:30-15:15",
        "session_restriction": "full_rth",
        "regime_dependency": {
            "preferred_regimes": [],
            "avoid_regimes": [],
            "best_regime": "unknown",
            "best_regime_pf": 0,
        },
        "holding_time_class": "intraday_swing",
        "direction_bias": "bidirectional",
        "trade_frequency_bucket": "medium",
        "cost_sensitivity": "medium",
        "portfolio_role": "component_donor",
        "overlap_risk": "moderate",
        "confidence_level": "medium",
        "key_performance": {
            "net_pf": 0.94,
            "sharpe": -0.35,
            "trades": 400,
            "maxdd": 3271,
            "correlation_vs_portfolio": 0,
        },
        "structural_notes": "ana_gagua. Compression box concept (tightness + flatness filters) is structurally interesting. Box breakout is similar to ORB-009 in shape but triggered by compression, not time. Failed on MES/MNQ. Compression filters could be reused as entry components.",
    },
    {
        "strategy_id": "BBKC-SQUEEZE-MES-Both",
        "strategy_name": "bbkc_squeeze",
        "family": "squeeze",
        "asset": "MES",
        "mode": "both",
        "status": "rejected",
        "entry_type": "squeeze_release",
        "entry_trigger": "BB exits KC (squeeze release) + momentum direction (linreg of close - KC midline). Lime momentum = long, red momentum = short.",
        "confirmation_type": ["momentum_filter", "session_gate"],
        "filter_depth": 2,
        "exit_type": "momentum_decel",
        "exit_features": ["momentum_exit", "atr_stop", "eod_flatten"],
        "risk_model": "atr_adaptive",
        "session_window": "09:30-15:15",
        "session_restriction": "full_rth",
        "regime_dependency": {
            "preferred_regimes": [],
            "avoid_regimes": [],
            "best_regime": "unknown",
            "best_regime_pf": 0,
        },
        "holding_time_class": "intraday_swing",
        "direction_bias": "bidirectional",
        "trade_frequency_bucket": "high",
        "cost_sensitivity": "high",
        "portfolio_role": "component_donor",
        "overlap_risk": "high",
        "confidence_level": "medium",
        "key_performance": {
            "net_pf": 1.24,
            "sharpe": 2.87,
            "trades": 1295,
            "maxdd": 1002,
            "correlation_vs_portfolio": 0,
        },
        "structural_notes": "LazyBear classic. Gross PF=1.49 but 1,295 trades × $3.74/RT = 50% friction impact. Momentum color state machine (lime/green/red/maroon) is unique exit logic. Structurally similar to ORION-VOL (both are compression→expansion). Component value: squeeze detection + momentum states could enhance other strategies.",
    },
]


# ── Clustering ───────────────────────────────────────────────────────────────

# Feature vector for each strategy (categorical → numeric encoding)
ENTRY_TYPE_MAP = {
    "breakout": 0, "pullback": 1, "crossover": 2, "mean_reversion": 3,
    "regime_detection": 4, "squeeze_release": 5, "gap_signal": 6,
}
RISK_MODEL_MAP = {
    "atr_adaptive": 0, "range_based": 1, "rv_scaled": 2,
    "compression_based": 3, "fixed_points": 4,
}
HOLD_MAP = {"scalp": 0, "intraday_swing": 1, "day_trade": 2}
FREQ_MAP = {"rare": 0, "low": 1, "medium": 2, "high": 3}
COST_MAP = {"low": 0, "medium": 1, "high": 2}
BIAS_MAP = {"long_only": 0, "short_only": 1, "bidirectional": 2}


def strategy_to_vector(dna):
    """Convert DNA profile to numeric feature vector for distance calculation."""
    return np.array([
        ENTRY_TYPE_MAP.get(dna["entry_type"], -1),
        dna["filter_depth"],
        RISK_MODEL_MAP.get(dna["risk_model"], -1),
        HOLD_MAP.get(dna["holding_time_class"], -1),
        FREQ_MAP.get(dna["trade_frequency_bucket"], -1),
        COST_MAP.get(dna["cost_sensitivity"], -1),
        BIAS_MAP.get(dna["direction_bias"], -1),
    ], dtype=float)


def compute_distance_matrix(catalog):
    """Compute normalized Euclidean distance between all strategies."""
    vectors = [strategy_to_vector(s) for s in catalog]
    n = len(vectors)
    # Normalize each feature to [0, 1]
    mat = np.array(vectors)
    mins = mat.min(axis=0)
    maxs = mat.max(axis=0)
    ranges = maxs - mins
    ranges[ranges == 0] = 1  # avoid division by zero
    normed = (mat - mins) / ranges

    dist = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            dist[i, j] = np.sqrt(np.sum((normed[i] - normed[j]) ** 2))
    return dist


def cluster_strategies(catalog, dist_matrix, threshold=0.4):
    """Simple agglomerative clustering by distance threshold."""
    n = len(catalog)
    assigned = [-1] * n
    cluster_id = 0

    for i in range(n):
        if assigned[i] >= 0:
            continue
        assigned[i] = cluster_id
        for j in range(i + 1, n):
            if assigned[j] >= 0:
                continue
            if dist_matrix[i, j] <= threshold:
                assigned[j] = cluster_id
        cluster_id += 1

    clusters = defaultdict(list)
    for i, cid in enumerate(assigned):
        clusters[cid].append(catalog[i]["strategy_id"])

    return dict(clusters), assigned


def classify_strategy(dna):
    """Classify strategy into role categories."""
    status = dna["status"]
    if status == "deployment_ready":
        return "true_diversifier" if dna["overlap_risk"] == "none" else "core"
    elif status in ("candidate_validated", "pending_validation"):
        return "true_diversifier" if dna["overlap_risk"] == "none" else "candidate"
    elif status == "watchlist":
        return "watchlist"
    elif dna["portfolio_role"] == "component_donor":
        return "component_donor"
    else:
        return "rejected_but_informative"


def main():
    print("=" * 70)
    print("  STRATEGY DNA CLUSTERING")
    print("  (Structural fingerprinting + similarity analysis)")
    print("=" * 70)

    # ── Save catalog ─────────────────────────────────────────────────────
    with open(OUTPUT_DIR / "dna_catalog.json", "w") as f:
        json.dump(DNA_CATALOG, f, indent=2)
    print(f"\n  Catalog: {len(DNA_CATALOG)} strategies profiled")
    print(f"  Saved to: {OUTPUT_DIR / 'dna_catalog.json'}")

    # ── Compute distances ────────────────────────────────────────────────
    dist = compute_distance_matrix(DNA_CATALOG)
    n = len(DNA_CATALOG)
    ids = [s["strategy_id"] for s in DNA_CATALOG]

    print(f"\n{'─' * 70}")
    print("  PAIRWISE STRUCTURAL DISTANCE")
    print(f"{'─' * 70}")
    print(f"  {'':>25}", end="")
    for sid in ids:
        print(f" {sid[:8]:>8}", end="")
    print()
    for i in range(n):
        print(f"  {ids[i]:>25}", end="")
        for j in range(n):
            marker = " *" if dist[i, j] < 0.3 and i != j else "  "
            print(f" {dist[i, j]:>6.2f}{marker}", end="")
        print()
    print("  (* = structurally similar, distance < 0.3)")

    # ── Cluster ──────────────────────────────────────────────────────────
    clusters, assignments = cluster_strategies(DNA_CATALOG, dist)

    print(f"\n{'─' * 70}")
    print("  STRUCTURAL CLUSTERS")
    print(f"{'─' * 70}")

    cluster_details = {}
    for cid, members in sorted(clusters.items()):
        # Get shared traits
        member_dnas = [d for d in DNA_CATALOG if d["strategy_id"] in members]
        entry_types = set(d["entry_type"] for d in member_dnas)
        risk_models = set(d["risk_model"] for d in member_dnas)

        label = f"Cluster {cid}"
        if len(members) == 1:
            label += " (singleton)"
        elif entry_types == {"breakout"}:
            label += " (breakout family)"
        elif len(entry_types) == 1:
            label += f" ({list(entry_types)[0]} family)"
        else:
            label += " (mixed)"

        print(f"\n  {label}:")
        for m in members:
            dna = next(d for d in DNA_CATALOG if d["strategy_id"] == m)
            role = classify_strategy(dna)
            print(f"    {m:30s} [{dna['entry_type']:17s}] [{dna['risk_model']:18s}] → {role}")

        cluster_details[f"cluster_{cid}"] = {
            "members": members,
            "entry_types": list(entry_types),
            "risk_models": list(risk_models),
            "size": len(members),
        }

    # ── Classification ───────────────────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("  STRATEGY CLASSIFICATION")
    print(f"{'─' * 70}")

    classifications = {}
    for dna in DNA_CATALOG:
        role = classify_strategy(dna)
        classifications[dna["strategy_id"]] = role
        status_icon = {"true_diversifier": "★", "core": "●", "candidate": "◆",
                       "component_donor": "◇", "watchlist": "○",
                       "rejected_but_informative": "✗"}.get(role, "?")
        print(f"  {status_icon} {dna['strategy_id']:30s} → {role:25s} [confidence: {dna['confidence_level']}]")

    # ── DNA Type Analysis ────────────────────────────────────────────────
    print(f"\n{'─' * 70}")
    print("  DNA TYPE DISTRIBUTION")
    print(f"{'─' * 70}")

    entry_counts = defaultdict(int)
    risk_counts = defaultdict(int)
    hold_counts = defaultdict(int)
    for dna in DNA_CATALOG:
        entry_counts[dna["entry_type"]] += 1
        risk_counts[dna["risk_model"]] += 1
        hold_counts[dna["holding_time_class"]] += 1

    print("\n  Entry types:")
    for k, v in sorted(entry_counts.items(), key=lambda x: -x[1]):
        bar = "█" * v
        print(f"    {k:20s} {v}  {bar}")

    print("\n  Risk models:")
    for k, v in sorted(risk_counts.items(), key=lambda x: -x[1]):
        bar = "█" * v
        print(f"    {k:20s} {v}  {bar}")

    print("\n  Holding time:")
    for k, v in sorted(hold_counts.items(), key=lambda x: -x[1]):
        bar = "█" * v
        print(f"    {k:20s} {v}  {bar}")

    # ── Missing DNA types ────────────────────────────────────────────────
    all_entry_types = set(ENTRY_TYPE_MAP.keys())
    present_entries = set(entry_counts.keys())
    missing_entries = all_entry_types - present_entries

    print(f"\n{'─' * 70}")
    print("  MISSING DNA TYPES")
    print(f"{'─' * 70}")

    if missing_entries:
        for m in sorted(missing_entries):
            print(f"  ✗ {m} — no strategy in lab with this entry type")
    else:
        print("  All entry types represented")

    # Additional missing types not in enum
    print("\n  Structural gaps (not in current schema):")
    gaps = [
        "trend_following — no dedicated trend strategy (EMA/SuperTrend/Donchian)",
        "overnight — no globex/overnight session strategies",
        "event_driven — no CPI/FOMC/NFP targeted strategies",
        "pairs — no inter-market spread strategies",
        "higher_timeframe — all strategies operate on 5m only",
    ]
    for g in gaps:
        print(f"  ✗ {g}")

    # ── Save clusters ────────────────────────────────────────────────────
    cluster_output = {
        "clusters": cluster_details,
        "classifications": classifications,
        "overrepresented": [k for k, v in entry_counts.items() if v >= 2],
        "missing_entry_types": list(missing_entries),
        "structural_gaps": gaps,
        "distance_threshold": 0.4,
        "n_strategies": len(DNA_CATALOG),
    }

    with open(OUTPUT_DIR / "dna_clusters.json", "w") as f:
        json.dump(cluster_output, f, indent=2)
    print(f"\n  Saved clusters to: {OUTPUT_DIR / 'dna_clusters.json'}")

    # ── Generate report ──────────────────────────────────────────────────
    generate_report(DNA_CATALOG, cluster_details, classifications, dist, ids,
                    entry_counts, risk_counts, hold_counts, missing_entries, gaps)

    print(f"  Saved report to: {OUTPUT_DIR / 'dna_report.md'}")
    print(f"{'=' * 70}")


def generate_report(catalog, clusters, classifications, dist, ids,
                    entry_counts, risk_counts, hold_counts, missing_entries, gaps):
    """Generate the DNA analysis report."""
    lines = [
        "# Strategy DNA Report",
        "",
        "*Structural fingerprinting and similarity analysis for all converted strategies.*",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
        f"- **{len(catalog)} strategies** profiled across {len(set(d['family'] for d in catalog))} families",
        f"- **{len(clusters)} structural clusters** identified",
        f"- **{sum(1 for c in classifications.values() if c == 'true_diversifier')} true diversifiers**, "
        f"{sum(1 for c in classifications.values() if c == 'component_donor')} component donors, "
        f"{sum(1 for c in classifications.values() if c == 'rejected_but_informative')} rejected-but-informative",
        "",
        "### Key Finding",
        "",
        "The lab has **genuine structural diversity** among its validated strategies. PB-Short (pullback + deep filter stack), "
        "ORB-009 (range breakout + VWAP confirmation), and VIX Channel (regime detection + RV-scaled channel) are structurally "
        "distinct — different entry mechanisms, different risk models, different regime preferences. This is not cosmetic diversity.",
        "",
        "### Near-Duplicates Identified",
        "",
    ]

    # Find near-duplicates
    near_dupes = []
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            if dist[i, j] < 0.3:
                near_dupes.append((ids[i], ids[j], round(dist[i, j], 3)))

    if near_dupes:
        for a, b, d in near_dupes:
            lines.append(f"- **{a}** ↔ **{b}** (distance: {d})")
        lines.append("")
        lines.append("These strategies may be trading the same edge in different wrappers. "
                     "Adding both to a portfolio would provide less diversification than expected.")
    else:
        lines.append("No near-duplicates found (all pairwise distances > 0.3).")
    lines.append("")

    # Classifications
    lines.extend([
        "## Strategy Classifications",
        "",
        "| Strategy | Classification | Confidence | Entry Type | Risk Model |",
        "|----------|---------------|------------|------------|------------|",
    ])
    for dna in catalog:
        role = classifications[dna["strategy_id"]]
        icon = {"true_diversifier": "★", "core": "●", "candidate": "◆",
                "component_donor": "◇", "watchlist": "○",
                "rejected_but_informative": "✗"}.get(role, "?")
        lines.append(
            f"| {icon} {dna['strategy_id']} | {role} | {dna['confidence_level']} | "
            f"{dna['entry_type']} | {dna['risk_model']} |"
        )
    lines.append("")

    # Clusters
    lines.extend([
        "## Structural Clusters",
        "",
    ])
    for cname, cdata in sorted(clusters.items()):
        lines.append(f"### {cname} ({cdata['size']} members)")
        lines.append(f"- **Entry types:** {', '.join(cdata['entry_types'])}")
        lines.append(f"- **Risk models:** {', '.join(cdata['risk_models'])}")
        lines.append(f"- **Members:** {', '.join(cdata['members'])}")
        lines.append("")

    # DNA type analysis
    lines.extend([
        "## DNA Type Distribution",
        "",
        "### Entry Types",
        "",
        "| Type | Count | Strategies |",
        "|------|-------|-----------|",
    ])
    for et in sorted(entry_counts.keys()):
        strats = [d["strategy_id"] for d in catalog if d["entry_type"] == et]
        lines.append(f"| {et} | {entry_counts[et]} | {', '.join(strats)} |")
    lines.append("")

    lines.extend([
        "### Overrepresented Types",
        "",
    ])
    over = [k for k, v in entry_counts.items() if v >= 2]
    if over:
        for o in over:
            lines.append(f"- **{o}** ({entry_counts[o]} strategies) — adding more of this type has diminishing portfolio value")
    else:
        lines.append("- No overrepresented types (all unique)")
    lines.append("")

    lines.extend([
        "### Missing DNA Types",
        "",
    ])
    if missing_entries:
        for m in sorted(missing_entries):
            lines.append(f"- **{m}** — no strategy with this entry mechanism")
    lines.append("")
    lines.append("### Structural Gaps (beyond current schema)")
    lines.append("")
    for g in gaps:
        lines.append(f"- {g}")
    lines.append("")

    # Component donors
    lines.extend([
        "## Component Donor Analysis",
        "",
        "Rejected strategies with reusable structural components:",
        "",
    ])
    for dna in catalog:
        if dna["portfolio_role"] == "component_donor":
            lines.append(f"### {dna['strategy_id']}")
            lines.append(f"- **Reusable component:** {dna['structural_notes']}")
            lines.append("")

    # Recommendations
    lines.extend([
        "## Recommendations",
        "",
        "### For Portfolio Construction",
        "1. The three validated/candidate strategies (PB-Short, ORB-009, VIX Channel) are **genuinely structurally distinct**. Portfolio diversity is real, not cosmetic.",
        "2. ORION-VOL and BBKC-SQUEEZE are structurally similar (compression→breakout). Both failed. Avoid adding more compression breakout strategies.",
        "3. VWAP-006 and RVWAP-MR share the VWAP-based entry DNA. Both failed due to friction. VWAP entry alone is insufficient on 5m futures.",
        "",
        "### For Future Harvesting",
        "1. **Prioritize missing DNA types**: trend_following, overnight, event_driven",
        "2. **Avoid overrepresented types**: breakout (2 strategies), pullback (2 strategies) — adding more has diminishing returns",
        "3. **Regime gap harvest**: target LOW_VOL + RANGING specialists (only VIX Channel covers this)",
        "",
        "### For Evolution Engine",
        "1. **ORION-VOL compression filters** (tightness + flatness) could enhance ORB-009 entries",
        "2. **BBKC-SQUEEZE momentum state machine** (lime/green/red/maroon) is a unique exit logic worth testing on validated strategies",
        "3. **ICT-010 sweep detection** is structurally unique but needs better confirmation filters — not the pullback entry itself",
        "",
        "---",
        "*Generated by build_dna_profiles.py*",
    ])

    with open(OUTPUT_DIR / "dna_report.md", "w") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
