#!/usr/bin/env python3
"""FQL Registry Hardening — Enrich metadata, standardize fields, add taxonomy.

One-time migration script to bring all 65 strategies up to the v3.0 schema.
Adds structured fields for rejection reasons, source lineage categories,
batch linkage, and lifecycle tracking.

Usage:
    python3 research/registry_hardening.py              # Apply hardening
    python3 research/registry_hardening.py --dry-run    # Preview changes
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from research.utils.atomic_io import atomic_write_json, backup_rotate

REGISTRY_PATH = ROOT / "research" / "data" / "strategy_registry.json"
FIRST_PASS_DIR = ROOT / "research" / "data" / "first_pass"
VALIDATION_DIR = ROOT / "research" / "validation"

# ── Rejection Reason Taxonomy ────────────────────────────────────────────────

REJECTION_REASONS = {
    "STRUCTURAL_LOSS": "Strategy loses money across all modes and parameter variants",
    "INSUFFICIENT_EDGE": "PF 0.9-1.1 — near breakeven, not enough to overcome costs",
    "WALK_FORWARD_UNSTABLE": "Backtest profitable but walk-forward collapses",
    "REGIME_VULNERABLE": "Catastrophic loss in specific regime cells",
    "ASSET_MISMATCH": "Strategy logic does not transfer to this asset class",
    "PARAMETER_FRAGILE": "Edge depends on narrow parameter range — likely overfit",
    "SAMPLE_INSUFFICIENT": "Too few trades to determine edge (< 20)",
    "DUPLICATE_COVERAGE": "Overlaps with existing validated strategy on same edge",
    "IMPLEMENTATION_BUG": "Code bug found — hypothesis not tested, may revisit",
    "ICT_FAMILY_FAILED": "ICT-derived concepts have not produced systematic edge in FQL",
    "CLASSIC_TA_DECAY": "Well-known pattern (RSI, NR7, gap fill) shows no edge on futures 5m bars",
}

# ── Source Lineage Categories ────────────────────────────────────────────────

SOURCE_CATEGORIES = {
    "internal_research": "internal",
    "phase_harvest_ttm": "internal",
    "phase_harvest_vol": "internal",
    "phase10_discovery": "internal",
    "phase15_gold_snapback": "internal",
    "lucid_v6_extraction": "internal",
    "crossbreeding_phase12": "internal",
    "tail_engine_research": "internal",
    "tradingview_harvest_batch1": "tradingview",
    "tradingview_harvest_batch2": "tradingview",
    "tradingview_community": "tradingview",
    "tradingview_lazybear": "tradingview",
    "academic_research": "academic",
    "academic_gao_han_li_zhou_2018": "academic",
    "academic_zarattini_aziz_barbon_2024": "academic",
    "academic_orb_equity_index": "academic",
    "academic_orb_crude": "academic",
    "ny_fed_research": "academic",
    "ict_concept_translation": "ict",
    "youtube_transcript_mech_model": "ict",
    "user_mentioned": "user",
    "asset_expansion": "expansion",
    "native_prototype": "expansion",
    "cross_asset_transfer": "expansion",
    "batch_first_pass_discovery": "factory",
    "russell_microstructure_research": "academic",
    "toby_crabel_book": "academic",
    "cta_research": "academic",
    "minervini_book": "academic",
    "quant_research": "academic",
    "quantifiedstrategies": "academic",
    "quantstart_pairs": "academic",
    "quantpedia_opex": "academic",
    "practitioner_composite": "practitioner",
    "practitioner_crudele": "practitioner",
    "practitioner_crude_events": "practitioner",
}


def link_batch_reports(strategy):
    """Find and link batch_first_pass reports for a strategy."""
    if not FIRST_PASS_DIR.exists():
        return None
    name = strategy.get("strategy_name", "")
    if not name:
        return None
    for f in FIRST_PASS_DIR.glob("*.json"):
        if name in f.name:
            try:
                data = json.load(open(f))
                best = data.get("best_result", {})
                return {
                    "report_file": str(f.relative_to(ROOT)),
                    "run_date": data.get("run_date", ""),
                    "classification": data.get("overall_classification", ""),
                    "best_asset": best.get("asset", ""),
                    "best_pf": best.get("pf", 0),
                }
            except Exception:
                pass
    return None


def link_validation(strategy):
    """Find and link validation battery results."""
    if not VALIDATION_DIR.exists():
        return None
    sid = strategy["strategy_id"]
    name = strategy.get("strategy_name", "")
    for f in VALIDATION_DIR.glob("*.json"):
        if sid.lower().replace("-", "_") in f.name.lower() or (name and name in f.name):
            try:
                data = json.load(open(f))
                return {
                    "report_file": str(f.relative_to(ROOT)),
                    "verdict": data.get("verdict", ""),
                    "score": data.get("score", 0),
                    "failures": data.get("failures", 0),
                }
            except Exception:
                pass
    return None


def classify_rejection(strategy):
    """Infer structured rejection reason from notes."""
    notes = (strategy.get("notes") or "") + " " + (strategy.get("rule_summary") or "")
    notes_lower = notes.lower()

    if "structural" in notes_lower and ("loss" in notes_lower or "negative" in notes_lower):
        return "STRUCTURAL_LOSS"
    if "pf 0.9" in notes_lower or "near breakeven" in notes_lower or "pf 0.98" in notes_lower:
        return "INSUFFICIENT_EDGE"
    if "walk-forward" in notes_lower and ("unstable" in notes_lower or "collapses" in notes_lower):
        return "WALK_FORWARD_UNSTABLE"
    if "catastrophic" in notes_lower and "regime" in notes_lower:
        return "REGIME_VULNERABLE"
    if "asset_mismatch" in notes_lower or "does not transfer" in notes_lower:
        return "ASSET_MISMATCH"
    if "ict" in notes_lower and "fail" in notes_lower:
        return "ICT_FAMILY_FAILED"
    if "no edge" in notes_lower or "no current edge" in notes_lower:
        return "STRUCTURAL_LOSS"
    if "insufficient" in notes_lower and "trade" in notes_lower:
        return "SAMPLE_INSUFFICIENT"
    if "duplicate" in notes_lower or "overlap" in notes_lower:
        return "DUPLICATE_COVERAGE"
    return None


def harden(dry_run=False):
    """Apply registry hardening."""
    reg = json.load(open(REGISTRY_PATH))
    strategies = reg["strategies"]
    changes = 0

    for s in strategies:
        modified = False

        # 1. Ensure last_review_date
        if not s.get("last_review_date"):
            s["last_review_date"] = "2026-03-16"
            modified = True

        # 2. Add source_category from lineage
        if not s.get("source_category"):
            source = s.get("source", "")
            s["source_category"] = SOURCE_CATEGORIES.get(source, "other")
            modified = True

        # 3. Add structured rejection_reason for rejected strategies
        if s.get("status") == "rejected" and not s.get("rejection_reason"):
            reason = classify_rejection(s)
            if reason:
                s["rejection_reason"] = reason
                s["rejection_description"] = REJECTION_REASONS.get(reason, "")
                modified = True

        # 4. Link batch_first_pass reports
        if not s.get("batch_first_pass"):
            batch = link_batch_reports(s)
            if batch:
                s["batch_first_pass"] = batch
                modified = True

        # 5. Link validation results
        if not s.get("validation_result"):
            val = link_validation(s)
            if val:
                s["validation_result"] = val
                modified = True

        # 6. Add lifecycle_stage
        status = s.get("status", "idea")
        if not s.get("lifecycle_stage"):
            stage_map = {
                "idea": "discovery",
                "testing": "first_pass",
                "probation": "forward_validation",
                "core": "deployed",
                "rejected": "archived",
                "retired": "archived",
            }
            s["lifecycle_stage"] = stage_map.get(status, "unknown")
            modified = True

        # 7. Ensure state_history exists
        if "state_history" not in s:
            s["state_history"] = []
            modified = True

        if modified:
            changes += 1

    # Update schema version
    reg["_schema_version"] = "3.0"
    reg["_generated"] = datetime.now().strftime("%Y-%m-%d")
    reg["_rejection_taxonomy"] = REJECTION_REASONS

    if dry_run:
        print(f"DRY RUN: {changes} strategies would be modified")
        return

    backup_rotate(REGISTRY_PATH, keep=5)
    atomic_write_json(REGISTRY_PATH, reg)
    print(f"Registry hardened: {changes} strategies modified, schema v3.0")

    # Print summary
    rejection_counts = {}
    for s in strategies:
        rr = s.get("rejection_reason")
        if rr:
            rejection_counts[rr] = rejection_counts.get(rr, 0) + 1

    if rejection_counts:
        print(f"\nRejection taxonomy applied:")
        for reason, count in sorted(rejection_counts.items(), key=lambda x: -x[1]):
            print(f"  {reason}: {count}")

    batch_linked = sum(1 for s in strategies if s.get("batch_first_pass"))
    val_linked = sum(1 for s in strategies if s.get("validation_result"))
    print(f"\nBatch reports linked: {batch_linked}")
    print(f"Validation reports linked: {val_linked}")


def main():
    parser = argparse.ArgumentParser(description="FQL Registry Hardening")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    harden(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
