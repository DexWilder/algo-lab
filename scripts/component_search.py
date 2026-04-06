#!/usr/bin/env python3
"""FQL Component Search — find reusable strategy building blocks.

Searches the registry for strategy components (entries, exits, filters,
overlays, timing effects) that can be reused in new combinations.

This is the query layer for the component catalog. It turns fragment
capture into an assembly advantage.

Usage:
    python3 scripts/component_search.py                          # All components
    python3 scripts/component_search.py --type exit              # Exit logic only
    python3 scripts/component_search.py --asset ZN               # ZN components
    python3 scripts/component_search.py --status validated       # Validated only
    python3 scripts/component_search.py --factor CARRY           # CARRY factor
    python3 scripts/component_search.py --salvageable            # From rejected parents
    python3 scripts/component_search.py --convergence 2          # 2+ independent sources
    python3 scripts/component_search.py --save                   # Save to inbox
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = ROOT / "research" / "data" / "strategy_registry.json"
OUTPUT_PATH = Path.home() / "openclaw-intake" / "inbox" / "_component_catalog.md"

COMPONENT_FIELDS = ["entry", "exit", "filter", "sizing", "regime", "timing"]

FAMILY_TO_FACTOR = {
    "pullback": "MOMENTUM", "breakout": "MOMENTUM", "trend": "MOMENTUM",
    "mean_reversion": "MEAN_REVERSION", "event_driven": "EVENT",
    "carry": "CARRY", "afternoon_rates_reversion": "STRUCTURAL",
    "vol_expansion": "VOLATILITY", "structural": "STRUCTURAL",
    "volatility": "VOLATILITY",
}


def load_registry():
    if not REGISTRY_PATH.exists():
        return []
    return json.load(open(REGISTRY_PATH)).get("strategies", [])


def get_factor(s):
    for t in s.get("tags", []):
        if t in ("MOMENTUM", "CARRY", "VOLATILITY", "EVENT", "STRUCTURAL", "VALUE"):
            return t
    return FAMILY_TO_FACTOR.get(s.get("family", ""), "UNKNOWN")


def search(component_type=None, asset_scope=None, factor=None,
           validation_status=None, salvageable=False, min_convergence=0):
    """Search for components matching criteria."""
    strategies = load_registry()
    results = []

    for s in strategies:
        components = s.get("components")
        if not components:
            continue

        sid = s["strategy_id"]
        status = s.get("status", "")
        s_factor = get_factor(s)
        s_asset = components.get("asset_scope", s.get("asset", ""))
        s_validation = components.get("validation_status", "untested")
        s_convergence = len(s.get("convergent_sources", []))

        # Filters
        if factor and s_factor != factor:
            continue
        if asset_scope and asset_scope.lower() not in s_asset.lower():
            continue
        if validation_status and s_validation != validation_status:
            continue
        if salvageable and status != "rejected":
            continue
        if min_convergence > 0 and s_convergence < min_convergence:
            continue

        # Extract matching component types
        for ctype in COMPONENT_FIELDS:
            comp = components.get(ctype)
            if not comp:
                continue
            if component_type and ctype != component_type:
                continue

            # Attach validation history if available
            val_history = []
            for vh in s.get("component_validation_history", []):
                if vh.get("type") == ctype or ctype in vh.get("component", ""):
                    val_history.append(vh)

            results.append({
                "strategy": sid,
                "status": status,
                "factor": s_factor,
                "component_type": ctype,
                "description": comp,
                "asset_scope": s_asset,
                "validation_status": s_validation,
                "convergent_sources": s_convergence,
                "timing": components.get("timing", ""),
                "salvageable": components.get("salvageable", ""),
                "validation_history": val_history,
            })

    return results


def format_results(results, save=False):
    lines = []
    lines.append("# FQL Component Catalog")
    lines.append(f"*Components found: {len(results)}*")
    lines.append("")

    if not results:
        lines.append("No matching components found.")
        return "\n".join(lines)

    # Group by component type
    by_type = {}
    for r in results:
        by_type.setdefault(r["component_type"], []).append(r)

    for ctype in COMPONENT_FIELDS:
        items = by_type.get(ctype, [])
        if not items:
            continue

        lines.append(f"## {ctype.upper()} Components ({len(items)})")
        lines.append("")

        for r in items:
            status_icon = {
                "validated": "+",
                "rejected_in_context": "x",
                "untested": "?",
                "salvaged": "~",
            }.get(r["validation_status"], "?")

            lines.append(f"[{status_icon}] **{r['strategy']}** ({r['factor']}, {r['asset_scope']})")
            lines.append(f"    {r['description']}")
            if r.get("timing"):
                lines.append(f"    Timing: {r['timing']}")
            if r.get("salvageable"):
                lines.append(f"    Salvageable: {r['salvageable']}")
            if r["convergent_sources"] > 0:
                lines.append(f"    Convergent sources: {r['convergent_sources']}")
            for vh in r.get("validation_history", []):
                ctx = vh.get("context", {})
                ctx_str = f"{ctx.get('asset','?')} / {ctx.get('session','?')} / {ctx.get('regime','?')}"
                lines.append(f"    Evidence [{vh['result'].upper()}]: {vh.get('evidence', '')[:80]}")
                lines.append(f"    Context: {ctx_str}")
                if vh.get("failure_contexts"):
                    lines.append(f"    Failed in: {', '.join(vh['failure_contexts'][:2])}")
                if vh.get("reusable_in"):
                    reuse = vh["reusable_in"] if isinstance(vh["reusable_in"], list) else [vh["reusable_in"]]
                    lines.append(f"    Reusable: {', '.join(reuse[:2])}")
            lines.append("")

    lines.append("---")
    lines.append("*Legend: [+] validated, [x] rejected in context, [?] untested, [~] salvaged*")

    report = "\n".join(lines)

    if save:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_PATH, "w") as f:
            f.write(report)
        print(f"\n  Saved to: {OUTPUT_PATH}")

    return report


def main():
    parser = argparse.ArgumentParser(description="FQL Component Search")
    parser.add_argument("--type", help="Component type: entry, exit, filter, sizing, regime, timing")
    parser.add_argument("--asset", help="Asset scope filter (e.g., ZN, MES, rates)")
    parser.add_argument("--factor", help="Factor filter (e.g., CARRY, VOLATILITY)")
    parser.add_argument("--status", help="Validation status: validated, rejected_in_context, untested")
    parser.add_argument("--salvageable", action="store_true", help="Only from rejected strategies")
    parser.add_argument("--convergence", type=int, default=0, help="Min convergent sources")
    parser.add_argument("--save", action="store_true", help="Save to inbox")
    args = parser.parse_args()

    results = search(
        component_type=args.type,
        asset_scope=args.asset,
        factor=args.factor,
        validation_status=args.status,
        salvageable=args.salvageable,
        min_convergence=args.convergence,
    )

    report = format_results(results, save=args.save)
    print(report)


if __name__ == "__main__":
    main()
