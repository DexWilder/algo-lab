"""Strategy Triage Layer — Algo Lab.

Analyzes all harvested strategies from the intake manifest and produces:
1. strategy_triage_report.md   — Full triage report
2. conversion_queue.json       — Prioritized conversion candidates
3. component_queue.json        — Component-only extractions
4. similarity_clusters.json    — Near-duplicate groupings
5. research_gap_map.md         — Family coverage gaps

Usage:
    python3 research/triage/run_triage.py
"""

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MANIFEST_PATH = PROJECT_ROOT / "intake" / "manifest.json"
OUTPUT_DIR = Path(__file__).resolve().parent

# ── Already converted/validated strategies ───────────────────────────────

ALREADY_CONVERTED = {
    "orb-009-luiscaballero-orb-vwap-volume": "orb_009",
    "michaelriggs--vwap-rsi-scalper-final-v1": "vwap_006",
    "ict-010-tfo-captain-backtest-model": "ict_010",
}

EXISTING_FAMILIES = {
    "pb_trend": {"family": "pb", "entry": "pullback", "status": "validated"},
    "vwap_rev": {"family": "vwap", "entry": "mean_reversion", "status": "candidate"},
    "lucid-100k": {"family": "pb+vwap", "entry": "pullback+mean_reversion", "status": "validated"},
}


# ── Keyword-based classifiers ────────────────────────────────────────────

ENTRY_KEYWORDS = {
    "breakout": ["breakout", "break above", "break below", "crosses above", "crosses below",
                  "cross above", "cross below", "breaks out", "reclaim"],
    "mean_reversion": ["mean reversion", "reversion", "oversold", "overbought",
                        "band touch", "deviation band", "lower band", "dip below"],
    "pullback": ["pullback", "pull back", "retracement", "retrace", "dip", "pullback hold"],
    "crossover": ["crossover", "cross over", "ema cross", "ma cross", "vwap cross",
                   "crosses above", "crosses below"],
    "sweep_reversal": ["sweep", "liquidity sweep", "stop hunt", "reversal",
                        "sweep reversal", "fake breakout"],
    "fvg": ["fvg", "fair value gap", "imbalance"],
    "order_block": ["order block", "ob ", "ob,", "demand zone", "supply zone"],
    "gap": ["gap momentum", "gap", "cumulative gap"],
}

EXIT_KEYWORDS = {
    "atr_based": ["atr", "atr-based", "atr stop", "atr trailing"],
    "fixed_points": ["fixed point", "fixed tick", "fixed stop", "point stop",
                      "tick stop", "40 tick", "80 tick", "20-point"],
    "trailing_stop": ["trailing stop", "trailing sl", "trsl", "trail"],
    "rr_target": ["r:r", "risk:reward", "risk reward", "2:1", "3:1", "1:2", "1:3"],
    "partial_exit": ["partial", "multi-target", "2-stage", "3-level", "scale out"],
    "breakeven": ["breakeven", "break-even", "break even", "be at"],
    "eod_flatten": ["eod", "end of day", "3:15", "15:15", "session close", "session exit"],
    "vwap_cross": ["vwap cross", "exits at rvwap", "exit on vwap"],
    "ma_crossback": ["ma cross", "ema cross", "crossback"],
}

SESSION_KEYWORDS = {
    "ny_session": ["ny session", "new york", "nyse", "us cash", "american session",
                    "9:30", "09:30"],
    "first_30min": ["first 30", "opening range", "first half hour", "30-min",
                     "30 min", "9:30-10:00"],
    "first_15min": ["first 15", "15-min", "15 min", "9:30-9:45"],
    "morning_only": ["morning", "first 2 hours", "first two hours"],
    "full_day": ["full day", "all day"],
    "session_controlled": ["session filter", "session control", "session window",
                           "session-limited", "session-restricted"],
}

RISK_KEYWORDS = {
    "atr_stops": ["atr stop", "atr-based", "atr sl", "atr trailing", "volatility-adjusted"],
    "fixed_stops": ["fixed stop", "fixed point", "fixed tick", "max sl in points"],
    "percent_stops": ["5%", "3%", "percent stop", "pct stop"],
    "dynamic_stops": ["dynamic sl", "dynamic stop", "smart stop", "swing-based"],
    "position_sizing": ["position sizing", "confidence scoring", "equity"],
}


def classify_text(text: str, keyword_map: dict) -> list[str]:
    """Match text against keyword categories."""
    text_lower = text.lower()
    matches = []
    for category, keywords in keyword_map.items():
        for kw in keywords:
            if kw in text_lower:
                matches.append(category)
                break
    return matches


def compute_automation_fitness(script: dict) -> int:
    """Score automation fitness 1-5 based on available data."""
    text = f"{script.get('description', '')} {script.get('notes', '')}"
    text_lower = text.lower()
    score = 3  # Base

    # Positive signals
    if any(k in text_lower for k in ["deterministic", "clear rules", "defined rules"]):
        score += 1
    if any(k in text_lower for k in ["futures", "es ", "nq ", "mes", "mnq", "mgc"]):
        score += 0.5
    if any(k in text_lower for k in ["session control", "session filter", "eod"]):
        score += 0.5
    if any(k in text_lower for k in ["prop firm", "prop fit", "funded"]):
        score += 0.5
    if script.get("pine_file"):
        score += 0.5
    if any(k in text_lower for k in ["af=5", "high automation", "very high automation"]):
        score = max(score, 5)
    elif any(k in text_lower for k in ["af=4"]):
        score = max(score, 4)
    elif any(k in text_lower for k in ["af=3"]):
        score = min(score, 3)

    # Negative signals
    if any(k in text_lower for k in ["long-only", "long only"]):
        score -= 0.5
    if any(k in text_lower for k in ["indicator", "no sl/tp", "no exit"]):
        score -= 1
    if any(k in text_lower for k in ["spot mode", "crypto"]):
        score -= 0.5

    return max(1, min(5, round(score)))


def estimate_trade_frequency(script: dict) -> str:
    """Estimate trade frequency from description."""
    text = f"{script.get('description', '')} {script.get('notes', '')}".lower()

    if any(k in text for k in ["scalp", "scalper", "scalping"]):
        return "high"
    if any(k in text for k in ["max 1 trade", "1 trade/day", "max trades",
                                 "max 2 trade", "limited trade"]):
        return "low"
    if any(k in text for k in ["swing", "daily", "weekly"]):
        return "low"
    if any(k in text for k in ["intraday", "5m", "5-min", "15m"]):
        return "medium"
    return "medium"


def estimate_regime_dependence(script: dict) -> str:
    """Estimate regime dependence."""
    text = f"{script.get('description', '')} {script.get('notes', '')}".lower()

    entry_types = classify_text(text, ENTRY_KEYWORDS)

    if "mean_reversion" in entry_types:
        return "range_bound"
    if "breakout" in entry_types and "mean_reversion" not in entry_types:
        return "trending"
    if "sweep_reversal" in entry_types:
        return "volatile"
    if any(k in text for k in ["trend follow", "trend-following", "trend template"]):
        return "trending"
    if any(k in text for k in ["chop filter", "flat filter", "range filter"]):
        return "adaptive"
    return "mixed"


def estimate_conversion_complexity(script: dict) -> str:
    """Estimate conversion difficulty."""
    text = f"{script.get('description', '')} {script.get('notes', '')}".lower()

    complexity = 2  # Base

    if script.get("pine_version") == "6":
        complexity += 1
    if any(k in text for k in ["comprehensive", "feature-rich", "multiple models",
                                 "multi-mode", "confidence scoring", "dca"]):
        complexity += 1
    if any(k in text for k in ["github", "clean code", "simple", "basic"]):
        complexity -= 1
    if any(k in text for k in ["clear rules", "deterministic", "defined rules"]):
        complexity -= 0.5
    if not script.get("pine_file"):
        complexity += 0.5

    if complexity <= 1.5:
        return "easy"
    elif complexity <= 3:
        return "medium"
    else:
        return "hard"


def compute_similarity_features(script: dict) -> dict:
    """Extract feature vector for similarity comparison."""
    text = f"{script.get('description', '')} {script.get('notes', '')} {' '.join(script.get('tags', []))}"

    return {
        "family": script.get("family", "unknown"),
        "entry_models": classify_text(text, ENTRY_KEYWORDS),
        "exit_models": classify_text(text, EXIT_KEYWORDS),
        "session_models": classify_text(text, SESSION_KEYWORDS),
        "risk_models": classify_text(text, RISK_KEYWORDS),
    }


def compute_similarity(feat_a: dict, feat_b: dict) -> float:
    """Weighted similarity between two feature sets.

    Same family + same primary entry model = high similarity.
    Cross-family similarity is very low by design.
    """
    if feat_a["family"] != feat_b["family"]:
        return 0.0  # Never cluster across families

    # Base: same family
    score = 0.35

    # Entry model overlap (heaviest weight — this defines the strategy)
    a_entry = set(feat_a["entry_models"])
    b_entry = set(feat_b["entry_models"])
    if a_entry and b_entry:
        entry_overlap = len(a_entry & b_entry) / len(a_entry | b_entry)
        score += 0.35 * entry_overlap
    elif not a_entry and not b_entry:
        # Both have no detected entry model — likely similar (underspecified)
        score += 0.15

    # Exit/session/risk overlap (lighter weight)
    for key in ["exit_models", "session_models", "risk_models"]:
        a_set = set(feat_a[key])
        b_set = set(feat_b[key])
        if len(a_set | b_set) > 0:
            score += 0.10 * (len(a_set & b_set) / len(a_set | b_set))

    return score


def determine_best_treatment(script: dict, features: dict, af_score: int,
                              complexity: str, freq: str, regime: str,
                              cluster_rank: int) -> str:
    """Assign label: convert_now, hold_for_later, component_only, reject."""
    text = f"{script.get('description', '')} {script.get('notes', '')}".lower()
    sid = script["id"]

    # Already converted
    if sid in ALREADY_CONVERTED:
        return "already_converted"

    # Reject criteria
    if af_score <= 2:
        return "reject"
    if any(k in text for k in ["no sl/tp", "no exit", "indicator only"]):
        return "reject"
    if any(k in text for k in ["spot mode only"]):
        return "reject"

    # Component-only: strategies with unique extractable parts
    has_unique_component = any(k in text for k in [
        "confidence scoring", "flat filter", "chop filter", "cycle zone",
        "round number", "laddered", "pyramided", "rsi of vwap",
        "obv rsi", "pivot trailing", "supertrend", "market profile",
        "open drive", "minervini", "trend template", "candle pattern",
        "anchored vwap", "trendline breakout",
    ])

    # Convert-now: ONLY cluster rank 1 (representative) with high AF
    # Check this BEFORE component rules so the best-in-cluster always gets promoted
    if cluster_rank == 1 and af_score >= 4 and complexity != "hard":
        return "convert_now"

    if any(k in text for k in ["long-only", "long only"]) and "short" not in text:
        return "component_only" if has_unique_component else "hold_for_later"
    if any(k in text for k in ["partially based"]):
        return "component_only"
    if has_unique_component and af_score < 4:
        return "component_only"

    # Everything else
    if af_score >= 3:
        return "hold_for_later"

    return "reject"


def build_clusters(scripts: list, features_map: dict) -> list[dict]:
    """Group similar strategies into clusters."""
    n = len(scripts)
    ids = [s["id"] for s in scripts]

    # Compute pairwise similarity
    sim_matrix = {}
    for i in range(n):
        for j in range(i + 1, n):
            sim = compute_similarity(features_map[ids[i]], features_map[ids[j]])
            sim_matrix[(ids[i], ids[j])] = sim

    # Greedy clustering with intra-family grouping
    THRESHOLD = 0.45  # Lower threshold since cross-family is already 0
    clusters = []
    assigned = set()

    # Sort scripts by automation fitness to process best first
    scored = sorted(scripts, key=lambda s: s.get("_af_score", 0), reverse=True)

    for script in scored:
        sid = script["id"]
        if sid in assigned:
            continue

        cluster = [sid]
        assigned.add(sid)

        # Find all similar scripts (transitive within threshold)
        changed = True
        while changed:
            changed = False
            for other in scripts:
                oid = other["id"]
                if oid in assigned:
                    continue
                # Check similarity against ANY member of the cluster
                for member in cluster:
                    key = (min(member, oid), max(member, oid))
                    if key in sim_matrix and sim_matrix[key] >= THRESHOLD:
                        cluster.append(oid)
                        assigned.add(oid)
                        changed = True
                        break

        clusters.append(cluster)

    return clusters


def main():
    # Load manifest
    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)
    scripts = manifest["scripts"]

    print(f"Triage: analyzing {len(scripts)} harvested strategies...")

    # ── Phase 1: Score each strategy ─────────────────────────────────────
    triage_data = []
    features_map = {}

    for script in scripts:
        sid = script["id"]
        text = f"{script.get('description', '')} {script.get('notes', '')} {' '.join(script.get('tags', []))}"

        af_score = compute_automation_fitness(script)
        script["_af_score"] = af_score

        features = compute_similarity_features(script)
        features_map[sid] = features

        entry_models = classify_text(text, ENTRY_KEYWORDS)
        exit_models = classify_text(text, EXIT_KEYWORDS)
        session_models = classify_text(text, SESSION_KEYWORDS)
        risk_models = classify_text(text, RISK_KEYWORDS)
        freq = estimate_trade_frequency(script)
        regime = estimate_regime_dependence(script)
        complexity = estimate_conversion_complexity(script)

        triage_data.append({
            "id": sid,
            "title": script["title"],
            "family": script["family"],
            "author": script.get("author", ""),
            "description": script.get("description", ""),
            "notes": script.get("notes", ""),
            "pine_file": script.get("pine_file"),
            "pine_version": script.get("pine_version", "5"),
            "tags": script.get("tags", []),
            "url": script.get("url", ""),
            "automation_fitness": af_score,
            "entry_models": entry_models,
            "exit_models": exit_models,
            "session_models": session_models,
            "risk_models": risk_models,
            "trade_frequency": freq,
            "regime_dependence": regime,
            "conversion_complexity": complexity,
        })

    # ── Phase 2: Build clusters ──────────────────────────────────────────
    clusters_raw = build_clusters(scripts, features_map)

    # Name clusters and rank members
    id_to_entry = {e["id"]: e for e in triage_data}
    clusters = []
    for i, member_ids in enumerate(clusters_raw):
        if len(member_ids) == 0:
            continue
        # Determine cluster family and entry model
        families = [id_to_entry[m]["family"] for m in member_ids]
        entries = []
        for m in member_ids:
            entries.extend(id_to_entry[m]["entry_models"])
        dominant_family = Counter(families).most_common(1)[0][0]
        dominant_entry = Counter(entries).most_common(1)[0][0] if entries else "mixed"

        # Rank by AF score
        ranked = sorted(member_ids, key=lambda m: id_to_entry[m]["automation_fitness"], reverse=True)

        cluster_name = f"{dominant_family.upper()}-{dominant_entry}-{i+1}"
        clusters.append({
            "cluster_id": cluster_name,
            "family": dominant_family,
            "dominant_entry": dominant_entry,
            "size": len(member_ids),
            "members": ranked,
            "representative": ranked[0],
        })

    # Set cluster rank for each script
    id_to_cluster_rank = {}
    id_to_cluster = {}
    for cluster in clusters:
        for rank, mid in enumerate(cluster["members"], 1):
            id_to_cluster_rank[mid] = rank
            id_to_cluster[mid] = cluster["cluster_id"]

    # ── Phase 3: Assign labels ───────────────────────────────────────────
    for entry in triage_data:
        sid = entry["id"]
        rank = id_to_cluster_rank.get(sid, 1)
        label = determine_best_treatment(
            {"id": sid, "description": entry["description"],
             "notes": entry["notes"], "pine_file": entry["pine_file"]},
            features_map[sid],
            entry["automation_fitness"],
            entry["conversion_complexity"],
            entry["trade_frequency"],
            entry["regime_dependence"],
            rank,
        )
        entry["label"] = label
        entry["cluster"] = id_to_cluster.get(sid, "singleton")
        entry["cluster_rank"] = rank

    # ── Phase 4: Generate outputs ────────────────────────────────────────

    # Sort by label priority, then AF score
    label_order = {"convert_now": 0, "hold_for_later": 1, "component_only": 2,
                   "already_converted": 3, "reject": 4}
    triage_data.sort(key=lambda e: (label_order.get(e["label"], 5), -e["automation_fitness"]))

    # --- 1. conversion_queue.json ---
    convert_now = [e for e in triage_data if e["label"] == "convert_now"]
    hold = [e for e in triage_data if e["label"] == "hold_for_later"]

    conversion_queue = {
        "generated": "auto",
        "description": "Prioritized conversion queue — convert_now first, then hold_for_later",
        "convert_now": [
            {
                "id": e["id"],
                "title": e["title"],
                "family": e["family"],
                "cluster": e["cluster"],
                "automation_fitness": e["automation_fitness"],
                "conversion_complexity": e["conversion_complexity"],
                "entry_models": e["entry_models"],
                "trade_frequency": e["trade_frequency"],
                "regime_dependence": e["regime_dependence"],
                "url": e["url"],
                "rationale": _conversion_rationale(e),
            }
            for e in convert_now
        ],
        "hold_for_later": [
            {
                "id": e["id"],
                "title": e["title"],
                "family": e["family"],
                "cluster": e["cluster"],
                "automation_fitness": e["automation_fitness"],
                "conversion_complexity": e["conversion_complexity"],
                "url": e["url"],
            }
            for e in hold
        ],
    }
    with open(OUTPUT_DIR / "conversion_queue.json", "w") as f:
        json.dump(conversion_queue, f, indent=2)

    # --- 2. component_queue.json ---
    # Include component_only AND hold_for_later scripts that have extractable parts
    components_primary = [e for e in triage_data if e["label"] == "component_only"]
    components_secondary = [
        e for e in triage_data
        if e["label"] == "hold_for_later"
        and len(_identify_components(e)) > 0
        and any(c not in ["breakout entry logic", "mean_reversion entry logic",
                           "crossover entry logic", "sweep_reversal entry logic",
                           "pullback entry logic"]
                for c in _identify_components(e))
    ]
    component_queue = {
        "generated": "auto",
        "description": "Strategies with extractable components — primary (component_only) and secondary (hold scripts with unique parts)",
        "primary": [
            {
                "id": e["id"],
                "title": e["title"],
                "family": e["family"],
                "extractable_components": _identify_components(e),
                "automation_fitness": e["automation_fitness"],
                "url": e["url"],
            }
            for e in components_primary
        ],
        "secondary": [
            {
                "id": e["id"],
                "title": e["title"],
                "family": e["family"],
                "extractable_components": _identify_components(e),
                "automation_fitness": e["automation_fitness"],
                "label": e["label"],
                "url": e["url"],
            }
            for e in components_secondary
        ],
    }
    with open(OUTPUT_DIR / "component_queue.json", "w") as f:
        json.dump(component_queue, f, indent=2)

    # --- 3. similarity_clusters.json ---
    clusters_output = {
        "generated": "auto",
        "description": "Strategy similarity clusters — near-duplicates grouped together",
        "similarity_threshold": 0.55,
        "total_clusters": len(clusters),
        "clusters": [
            {
                "cluster_id": c["cluster_id"],
                "family": c["family"],
                "dominant_entry": c["dominant_entry"],
                "size": c["size"],
                "representative": c["representative"],
                "representative_title": id_to_entry[c["representative"]]["title"],
                "members": [
                    {
                        "id": mid,
                        "title": id_to_entry[mid]["title"],
                        "rank": rank,
                        "label": id_to_entry[mid]["label"],
                        "automation_fitness": id_to_entry[mid]["automation_fitness"],
                    }
                    for rank, mid in enumerate(c["members"], 1)
                ],
            }
            for c in sorted(clusters, key=lambda c: c["size"], reverse=True)
        ],
    }
    with open(OUTPUT_DIR / "similarity_clusters.json", "w") as f:
        json.dump(clusters_output, f, indent=2)

    # --- 4. research_gap_map.md ---
    _write_gap_map(triage_data, clusters, OUTPUT_DIR / "research_gap_map.md")

    # --- 5. strategy_triage_report.md ---
    _write_report(triage_data, clusters, convert_now, hold, components_primary,
                  OUTPUT_DIR / "strategy_triage_report.md")

    # ── Summary ──────────────────────────────────────────────────────────
    label_counts = Counter(e["label"] for e in triage_data)
    print(f"\nTriage complete:")
    print(f"  Total scripts:       {len(triage_data)}")
    print(f"  Convert now:         {label_counts.get('convert_now', 0)}")
    print(f"  Hold for later:      {label_counts.get('hold_for_later', 0)}")
    print(f"  Component only:      {label_counts.get('component_only', 0)}")
    print(f"  Already converted:   {label_counts.get('already_converted', 0)}")
    print(f"  Reject:              {label_counts.get('reject', 0)}")
    print(f"  Clusters:            {len(clusters)}")
    print(f"\nOutputs:")
    print(f"  {OUTPUT_DIR / 'strategy_triage_report.md'}")
    print(f"  {OUTPUT_DIR / 'conversion_queue.json'}")
    print(f"  {OUTPUT_DIR / 'component_queue.json'}")
    print(f"  {OUTPUT_DIR / 'similarity_clusters.json'}")
    print(f"  {OUTPUT_DIR / 'research_gap_map.md'}")


def _conversion_rationale(entry: dict) -> str:
    """Generate a short rationale for why this should be converted."""
    parts = []
    if entry["automation_fitness"] >= 5:
        parts.append("highest automation fitness")
    elif entry["automation_fitness"] >= 4:
        parts.append("high automation fitness")
    if entry["cluster_rank"] == 1:
        parts.append("best in cluster")
    if entry["conversion_complexity"] == "easy":
        parts.append("low conversion effort")
    if entry["regime_dependence"] != "mixed":
        parts.append(f"{entry['regime_dependence']} regime specialist")
    if entry.get("pine_file"):
        parts.append("source code available")
    return "; ".join(parts) if parts else "meets conversion threshold"


def _identify_components(entry: dict) -> list[str]:
    """Identify extractable components from a strategy."""
    text = f"{entry['description']} {entry['notes']} {' '.join(entry['tags'])}".lower()
    components = []

    if "confidence scoring" in text or "confidence score" in text:
        components.append("confidence scoring system")
    if "flat filter" in text or "chop filter" in text:
        components.append("chop/flat market filter")
    if "cycle zone" in text or "round number" in text:
        components.append("cycle zone / round number detection")
    if "laddered" in text or "pyramid" in text:
        components.append("laddered/pyramid entry system")
    if "rsi of vwap" in text or "rsi(vwap)" in text:
        components.append("RSI-of-VWAP indicator")
    if "obv rsi" in text:
        components.append("OBV-RSI confirmation filter")
    if "pivot trailing" in text or "pivot stop" in text:
        components.append("pivot-based trailing stop")
    if "partial" in text or "multi-target" in text or "scale out" in text:
        components.append("multi-target exit system")
    if "dca" in text:
        components.append("DCA/position averaging")
    if "retest" in text:
        components.append("retest confirmation entry")
    if "supertrend" in text:
        components.append("SuperTrend filter")
    if "anchored vwap" in text or "avwap" in text:
        components.append("anchored VWAP calculation")
    if "trendline" in text:
        components.append("trendline breakout detection")
    if "market profile" in text or "open drive" in text:
        components.append("market profile open drive detection")
    if "minervini" in text or "trend template" in text:
        components.append("Minervini trend template qualifier")
    if "candle pattern" in text:
        components.append("candle pattern detection")

    if not components:
        # Fallback: use entry models
        for em in entry["entry_models"]:
            components.append(f"{em} entry logic")

    return components


def _write_gap_map(triage_data: list, clusters: list, path: Path):
    """Write research gap map."""
    # Family coverage
    families = defaultdict(list)
    for e in triage_data:
        families[e["family"]].append(e)

    # Desired families vs what we have
    desired_families = {
        "orb": "Opening Range Breakout — session-specific range breakout strategies",
        "vwap": "VWAP-based — mean reversion, breakout, and trend strategies using VWAP",
        "ict": "ICT/SMC — Smart Money Concepts, liquidity sweeps, FVG, order blocks",
        "pb": "Pullback — trend pullback entries (validated via pb_trend)",
        "rev": "Mean Reversion — non-VWAP reversion strategies (Bollinger, RSI extremes)",
        "trend": "Trend Following — pure trend strategies (MA crossovers, momentum)",
        "session": "Session-based — strategies tied to specific market sessions",
        "opening_drive": "Opening Drive — market profile open drive strategies",
    }

    # Entry model coverage
    all_entries = Counter()
    for e in triage_data:
        for em in e["entry_models"]:
            all_entries[em] += 1

    lines = [
        "# Research Gap Map — Algo Lab",
        "",
        "## Current Family Coverage",
        "",
        "| Family | Harvested | Converted | Convert Queue | Status |",
        "|--------|-----------|-----------|---------------|--------|",
    ]

    for fam_id, fam_desc in desired_families.items():
        harvested = len(families.get(fam_id, []))
        converted_count = sum(1 for e in triage_data if e["family"] == fam_id
                              and e["label"] == "already_converted")
        queue_count = sum(1 for e in triage_data if e["family"] == fam_id
                          and e["label"] == "convert_now")
        if fam_id == "pb":
            status = "VALIDATED"
        elif harvested == 0:
            status = "GAP"
        elif converted_count > 0:
            status = "IN PROGRESS"
        elif queue_count > 0:
            status = "QUEUED"
        else:
            status = "HARVESTED ONLY"
        lines.append(f"| {fam_id} | {harvested} | {converted_count} | {queue_count} | {status} |")

    lines.extend([
        "",
        "## Entry Model Coverage",
        "",
        "| Entry Model | Count | Families |",
        "|-------------|-------|----------|",
    ])

    for model, count in sorted(all_entries.items(), key=lambda x: -x[1]):
        fams = set(e["family"] for e in triage_data if model in e["entry_models"])
        lines.append(f"| {model} | {count} | {', '.join(sorted(fams))} |")

    lines.extend([
        "",
        "## Identified Gaps",
        "",
    ])

    # Gaps
    gaps = []
    if "pb" not in families or len(families.get("pb", [])) == 0:
        gaps.append("- **Pullback family**: Validated internally (pb_trend) but no external harvest for comparison/diversification")
    if "rev" not in families or len(families.get("rev", [])) == 0:
        gaps.append("- **Pure Mean Reversion**: No non-VWAP reversion strategies (Bollinger band, RSI extremes, etc.)")
    if "trend" not in families or len(families.get("trend", [])) == 0:
        gaps.append("- **Pure Trend Following**: No MA crossover / momentum strategies in harvest (only SMA-crossover in lab)")
    if "session" not in families or len(families.get("session", [])) == 0:
        gaps.append("- **Session-specific**: No London/Asia session strategies — all US-focused")
    if "opening_drive" not in families or len(families.get("opening_drive", [])) == 0:
        gaps.append("- **Opening Drive**: Market profile open drive (only ORB-002 partially covers this)")

    # Check for missing entry models
    if all_entries.get("fvg", 0) < 3:
        gaps.append(f"- **FVG entry model**: Only {all_entries.get('fvg', 0)} strategies — underrepresented")
    if all_entries.get("gap", 0) < 2:
        gaps.append(f"- **Gap momentum**: Only {all_entries.get('gap', 0)} strategy — rare entry model worth exploring")

    # Overrepresentation
    overreps = []
    vwap_mr = sum(1 for e in triage_data if e["family"] == "vwap" and "mean_reversion" in e["entry_models"])
    if vwap_mr > 5:
        overreps.append(f"- **VWAP Mean Reversion**: {vwap_mr} strategies — heavily duplicated, cluster aggressively")
    orb_breakout = sum(1 for e in triage_data if e["family"] == "orb" and "breakout" in e["entry_models"])
    if orb_breakout > 5:
        overreps.append(f"- **ORB Breakout**: {orb_breakout} strategies — standard pattern, pick best 2-3 representatives")

    if gaps:
        lines.extend(gaps)
    else:
        lines.append("- No major gaps identified")

    lines.extend([
        "",
        "## Overrepresented Areas",
        "",
    ])
    if overreps:
        lines.extend(overreps)
    else:
        lines.append("- No major overrepresentation issues")

    lines.extend([
        "",
        "## Recommended Next Harvest Targets",
        "",
        "1. **Pure Mean Reversion** (non-VWAP) — Bollinger band squeeze, RSI extremes, Keltner channels",
        "2. **London/Asia Session** strategies — diversify away from US-only trading hours",
        "3. **Momentum/Trend** — pure breakout-continuation or momentum factor strategies",
        "4. **Gap strategies** — overnight gap fade/continuation for index futures",
        "5. **Market profile** — opening drive, value area, POC-based strategies",
        "",
    ])

    with open(path, "w") as f:
        f.write("\n".join(lines))


def _write_report(triage_data, clusters, convert_now, hold, components, path):
    """Write the full triage report."""
    label_counts = Counter(e["label"] for e in triage_data)
    family_counts = Counter(e["family"] for e in triage_data)
    id_to_entry = {e["id"]: e for e in triage_data}

    lines = [
        "# Strategy Triage Report — Algo Lab",
        "",
        "## Harvest Summary",
        "",
        f"- **Total harvested scripts:** {len(triage_data)}",
        f"- **Families:** {', '.join(f'{fam} ({cnt})' for fam, cnt in family_counts.most_common())}",
        f"- **With Pine source:** {sum(1 for e in triage_data if e.get('pine_file'))}",
        "",
        "## Triage Results",
        "",
        f"| Label | Count |",
        f"|-------|-------|",
        f"| Convert Now | {label_counts.get('convert_now', 0)} |",
        f"| Hold for Later | {label_counts.get('hold_for_later', 0)} |",
        f"| Component Only | {label_counts.get('component_only', 0)} |",
        f"| Already Converted | {label_counts.get('already_converted', 0)} |",
        f"| Reject | {label_counts.get('reject', 0)} |",
        "",
        "## Cluster Map",
        "",
        f"Total clusters: {len(clusters)}",
        "",
    ]

    for c in sorted(clusters, key=lambda c: c["size"], reverse=True):
        rep = id_to_entry[c["representative"]]
        lines.append(f"### {c['cluster_id']} ({c['size']} members)")
        lines.append(f"- **Representative:** {rep['title']} (AF={rep['automation_fitness']})")
        lines.append(f"- **Entry model:** {c['dominant_entry']}")
        if c["size"] > 1:
            lines.append(f"- **Members:**")
            for rank, mid in enumerate(c["members"], 1):
                m = id_to_entry[mid]
                lines.append(f"  {rank}. {m['title']} — AF={m['automation_fitness']}, label={m['label']}")
        lines.append("")

    lines.extend([
        "## Top Conversion Candidates (convert_now)",
        "",
    ])
    if convert_now:
        lines.append("| # | ID | Title | Family | AF | Complexity | Entry | Regime | Freq |")
        lines.append("|---|-------|-------|--------|----|------------|-------|--------|------|")
        for i, e in enumerate(convert_now, 1):
            entries = ", ".join(e["entry_models"][:2]) if e["entry_models"] else "—"
            lines.append(
                f"| {i} | {e['id'][:40]} | {e['title'][:35]} | {e['family']} | "
                f"{e['automation_fitness']} | {e['conversion_complexity']} | "
                f"{entries} | {e['regime_dependence']} | {e['trade_frequency']} |"
            )
        lines.append("")
    else:
        lines.append("No immediate conversion candidates identified.")
        lines.append("")

    lines.extend([
        "## Component-Only Candidates",
        "",
    ])
    if components:
        for e in components:
            comps = _identify_components(e)
            lines.append(f"- **{e['title']}** ({e['family']}) — Extract: {', '.join(comps)}")
        lines.append("")
    else:
        lines.append("No component-only candidates identified.")
        lines.append("")

    lines.extend([
        "## Family Coverage Summary",
        "",
        "| Family | Total | Convert Now | Hold | Component | Converted | Reject |",
        "|--------|-------|-------------|------|-----------|-----------|--------|",
    ])
    for fam, _ in family_counts.most_common():
        fam_entries = [e for e in triage_data if e["family"] == fam]
        cn = sum(1 for e in fam_entries if e["label"] == "convert_now")
        hl = sum(1 for e in fam_entries if e["label"] == "hold_for_later")
        co = sum(1 for e in fam_entries if e["label"] == "component_only")
        ac = sum(1 for e in fam_entries if e["label"] == "already_converted")
        rj = sum(1 for e in fam_entries if e["label"] == "reject")
        lines.append(f"| {fam} | {len(fam_entries)} | {cn} | {hl} | {co} | {ac} | {rj} |")

    lines.extend([
        "",
        "## Recommended Next Conversion Round",
        "",
        "Based on triage results, the next conversion round should target:",
        "",
    ])

    # Pick top 3 convert_now candidates from different families
    seen_families = set()
    recs = []
    for e in convert_now:
        if e["family"] not in seen_families and len(recs) < 3:
            recs.append(e)
            seen_families.add(e["family"])

    for i, e in enumerate(recs, 1):
        lines.append(f"{i}. **{e['title']}** ({e['family']}) — {_conversion_rationale(e)}")

    if not recs:
        lines.append("- No strong candidates beyond already-converted strategies.")

    lines.extend([
        "",
        "---",
        "*Generated by research/triage/run_triage.py*",
        "",
    ])

    with open(path, "w") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
