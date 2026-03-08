#!/usr/bin/env python3
"""
Intake Manager v1.1 — TradingView script intake pipeline (portfolio-aware).

Usage:
  python3 intake/manage.py add --title "..." --url "..." --author "..." --family ict [--tags "tag1,tag2"]
  python3 intake/manage.py list [--family ict] [--status raw] [--sort score|date]
  python3 intake/manage.py update <id> --status reviewed [--notes "..."]
  python3 intake/manage.py review <id>
  python3 intake/manage.py score <id> --clarity 7 --testability 8 --futures-fit 6 ...
  python3 intake/manage.py search <query>
  python3 intake/manage.py stats
  python3 intake/manage.py export [--status raw] [--family ict]
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

INTAKE_DIR = Path(__file__).parent
MANIFEST = INTAKE_DIR / "manifest.json"
TV_DIR = INTAKE_DIR / "tradingview"
REPO_ROOT = INTAKE_DIR.parent
REVIEW_LOGS = REPO_ROOT / "research" / "review_logs"

VALID_STATUSES = [
    "raw", "reviewed", "cleaned", "standardized",
    "converted", "backtested", "validated", "portfolio_tested",
    "rejected", "deployed",
]
VALID_FAMILIES = ["ict", "orb", "vwap", "trend", "mean_reversion", "breakout", "opening_drive", "session"]
VALID_TYPES = ["strategy", "indicator", "library"]
VALID_STRATEGY_CLASSES = ["trend", "breakout", "mean_reversion", "liquidity", "continuation"]
VALID_ENTRY_STYLES = ["market", "limit_retrace", "stop_breakout"]
VALID_RISK_MODELS = ["fixed_stop", "atr", "structure_based"]
VALID_EXIT_MODELS = ["fixed_R", "liquidity_target", "trail", "hybrid"]
VALID_FREQUENCIES = ["low", "medium", "high"]
VALID_PORTFOLIO_ROLES = ["core", "enhancer", "stack_component"]
VALID_LAYERS = ["A", "B", "C"]

# Weighted composite scoring — tuned for prop survival + portfolio value
SCORE_WEIGHTS = {
    "testability": 0.25,
    "futures_fit": 0.20,
    "prop_fit": 0.20,
    "clarity": 0.15,
    "conversion_difficulty": 0.10,
    "diversification_potential": 0.10,
}
SCORE_FIELDS = list(SCORE_WEIGHTS.keys())


def load_manifest():
    with open(MANIFEST) as f:
        return json.load(f)


def save_manifest(data):
    with open(MANIFEST, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Manifest saved ({len(data['scripts'])} scripts)")


def generate_id(title, author):
    """Generate a slug-based ID from title and author."""
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    author_slug = re.sub(r"[^a-z0-9]+", "-", author.lower()).strip("-")
    return f"{author_slug}--{slug}"[:80]


def compute_composite_score(scores):
    """Weighted composite score (1-10 scale). Only uses non-null scores, re-normalizing weights."""
    active = {k: v for k, v in scores.items() if v is not None and k in SCORE_WEIGHTS}
    if not active:
        return None
    total_weight = sum(SCORE_WEIGHTS[k] for k in active)
    weighted_sum = sum(v * SCORE_WEIGHTS[k] / total_weight for k, v in active.items())
    return round(weighted_sum, 1)


def make_empty_entry(script_id, title, url, author, script_type, description,
                     pine_version, family, tags, pine_file, notes):
    """Create a new manifest entry with all fields initialized."""
    return {
        "id": script_id,
        "title": title,
        "url": url,
        "author": author,
        "type": script_type,
        "description": description,
        "pine_version": pine_version,
        "family": family,
        "tags": tags,
        "status": "raw",
        "pine_file": pine_file,
        "cleaned_file": None,
        "notes": notes,
        "repaint_risk": None,
        # Quality scores
        "scores": {k: None for k in SCORE_FIELDS},
        "composite_score": None,
        # Portfolio-aware metadata
        "asset_candidates": [],
        "preferred_timeframes": [],
        "session_window": None,
        "strategy_class": None,
        "entry_style": None,
        "risk_model": None,
        "exit_model": None,
        "trade_frequency_estimate": None,
        "notes_market_behavior": "",
        # Role in the lab
        "portfolio_role": None,
        "layer": None,
        "roster_target": None,
        # Tracking
        "review_log": None,
        "imported_date": datetime.now().strftime("%Y-%m-%d"),
        "reviewed_date": None,
        "reviewed_by": None,
    }


def cmd_add(args):
    manifest = load_manifest()

    script_id = generate_id(args.title, args.author)

    # Check for duplicates
    existing_ids = {s["id"] for s in manifest["scripts"]}
    existing_urls = {s["url"] for s in manifest["scripts"] if s.get("url")}
    if script_id in existing_ids:
        print(f"ERROR: Script already exists with id '{script_id}'")
        sys.exit(1)
    if args.url and args.url in existing_urls:
        print(f"ERROR: Script already exists with url '{args.url}'")
        sys.exit(1)

    if args.family not in VALID_FAMILIES:
        print(f"ERROR: Invalid family '{args.family}'. Valid: {VALID_FAMILIES}")
        sys.exit(1)

    script_type = getattr(args, "type", "strategy") or "strategy"
    if script_type not in VALID_TYPES:
        print(f"ERROR: Invalid type '{script_type}'. Valid: {VALID_TYPES}")
        sys.exit(1)

    tags = [t.strip() for t in args.tags.split(",")] if args.tags else []

    pine_file = args.pine_file if args.pine_file else f"tradingview/{args.family}/{script_id}.pine"

    entry = make_empty_entry(
        script_id=script_id,
        title=args.title,
        url=args.url or "",
        author=args.author,
        script_type=script_type,
        description=args.description or "",
        pine_version=args.pine_version or "5",
        family=args.family,
        tags=tags,
        pine_file=pine_file,
        notes=args.notes or "",
    )

    manifest["scripts"].append(entry)
    save_manifest(manifest)
    print(f"Added: {script_id}")
    print(f"  Family: {args.family}")
    print(f"  Pine file: {pine_file}")
    print(f"  Drop the .pine source code into: intake/{pine_file}")


def cmd_list(args):
    manifest = load_manifest()
    scripts = manifest["scripts"]

    if args.family:
        scripts = [s for s in scripts if s["family"] == args.family]
    if args.status:
        scripts = [s for s in scripts if s["status"] == args.status]

    if not scripts:
        print("No scripts found matching filters.")
        return

    # Sort by composite score (highest first), nulls last
    scripts.sort(key=lambda s: s.get("composite_score") or -1, reverse=True)

    print(f"{'ID':<40} {'FAMILY':<14} {'STATUS':<16} {'SCORE':<7} {'AUTHOR':<18} {'TITLE'}")
    print("-" * 134)
    for s in scripts:
        title = s["title"][:36]
        score = s.get("composite_score")
        score_str = f"{score:.1f}" if score is not None else "—"
        print(f"{s['id']:<40} {s['family']:<14} {s['status']:<16} {score_str:<7} {s['author']:<18} {title}")
    print(f"\nTotal: {len(scripts)}")


def cmd_update(args):
    manifest = load_manifest()

    script = next((s for s in manifest["scripts"] if s["id"] == args.id), None)
    if not script:
        print(f"ERROR: No script found with id '{args.id}'")
        sys.exit(1)

    if args.status:
        if args.status not in VALID_STATUSES:
            print(f"ERROR: Invalid status '{args.status}'. Valid: {VALID_STATUSES}")
            sys.exit(1)
        old = script["status"]
        script["status"] = args.status
        print(f"Status: {old} → {args.status}")
        if args.status == "reviewed":
            script["reviewed_date"] = datetime.now().strftime("%Y-%m-%d")
            script["reviewed_by"] = args.reviewed_by or "claude"

    if args.notes:
        script["notes"] = args.notes
        print("Notes updated")

    if args.repaint_risk is not None:
        script["repaint_risk"] = args.repaint_risk
        print(f"Repaint risk: {args.repaint_risk}")

    if args.family:
        if args.family not in VALID_FAMILIES:
            print(f"ERROR: Invalid family. Valid: {VALID_FAMILIES}")
            sys.exit(1)
        script["family"] = args.family
        print(f"Family: {args.family}")

    if args.cleaned_file:
        script["cleaned_file"] = args.cleaned_file
        print(f"Cleaned file: {args.cleaned_file}")

    if args.review_log:
        script["review_log"] = args.review_log
        print(f"Review log: {args.review_log}")

    # Portfolio-aware fields
    if args.assets:
        script["asset_candidates"] = [a.strip() for a in args.assets.split(",")]
        print(f"Asset candidates: {script['asset_candidates']}")

    if args.timeframes:
        script["preferred_timeframes"] = [t.strip() for t in args.timeframes.split(",")]
        print(f"Preferred timeframes: {script['preferred_timeframes']}")

    if args.session_window:
        script["session_window"] = args.session_window
        print(f"Session window: {args.session_window}")

    if args.strategy_class:
        if args.strategy_class not in VALID_STRATEGY_CLASSES:
            print(f"ERROR: Invalid strategy_class. Valid: {VALID_STRATEGY_CLASSES}")
            sys.exit(1)
        script["strategy_class"] = args.strategy_class
        print(f"Strategy class: {args.strategy_class}")

    if args.entry_style:
        if args.entry_style not in VALID_ENTRY_STYLES:
            print(f"ERROR: Invalid entry_style. Valid: {VALID_ENTRY_STYLES}")
            sys.exit(1)
        script["entry_style"] = args.entry_style
        print(f"Entry style: {args.entry_style}")

    if args.risk_model:
        if args.risk_model not in VALID_RISK_MODELS:
            print(f"ERROR: Invalid risk_model. Valid: {VALID_RISK_MODELS}")
            sys.exit(1)
        script["risk_model"] = args.risk_model
        print(f"Risk model: {args.risk_model}")

    if args.exit_model:
        if args.exit_model not in VALID_EXIT_MODELS:
            print(f"ERROR: Invalid exit_model. Valid: {VALID_EXIT_MODELS}")
            sys.exit(1)
        script["exit_model"] = args.exit_model
        print(f"Exit model: {args.exit_model}")

    if args.frequency:
        if args.frequency not in VALID_FREQUENCIES:
            print(f"ERROR: Invalid frequency. Valid: {VALID_FREQUENCIES}")
            sys.exit(1)
        script["trade_frequency_estimate"] = args.frequency
        print(f"Trade frequency: {args.frequency}")

    if args.market_notes:
        script["notes_market_behavior"] = args.market_notes
        print("Market behavior notes updated")

    # Lab role fields
    if args.portfolio_role:
        if args.portfolio_role not in VALID_PORTFOLIO_ROLES:
            print(f"ERROR: Invalid portfolio_role. Valid: {VALID_PORTFOLIO_ROLES}")
            sys.exit(1)
        script["portfolio_role"] = args.portfolio_role
        print(f"Portfolio role: {args.portfolio_role}")

    if args.layer:
        if args.layer not in VALID_LAYERS:
            print(f"ERROR: Invalid layer. Valid: {VALID_LAYERS}")
            sys.exit(1)
        script["layer"] = args.layer
        print(f"Layer: {args.layer}")

    if args.roster_target:
        script["roster_target"] = args.roster_target
        print(f"Roster target: {args.roster_target}")

    save_manifest(manifest)


def cmd_score(args):
    """Set granular quality scores for a script (weighted composite)."""
    manifest = load_manifest()

    script = next((s for s in manifest["scripts"] if s["id"] == args.id), None)
    if not script:
        print(f"ERROR: No script found with id '{args.id}'")
        sys.exit(1)

    # Ensure scores dict has all fields (backwards compat)
    if "scores" not in script:
        script["scores"] = {k: None for k in SCORE_FIELDS}
    for k in SCORE_FIELDS:
        if k not in script["scores"]:
            script["scores"][k] = None

    changed = False
    for field in SCORE_FIELDS:
        val = getattr(args, field, None)
        if val is not None:
            if not 1 <= val <= 10:
                print(f"ERROR: {field} must be 1-10, got {val}")
                sys.exit(1)
            script["scores"][field] = val
            changed = True

    if changed:
        script["composite_score"] = compute_composite_score(script["scores"])
        print(f"Scores for {args.id}:")
        print(f"  {'Field':<28} {'Score':<7} {'Weight'}")
        print(f"  {'-'*50}")
        for k in SCORE_FIELDS:
            v = script["scores"].get(k)
            w = SCORE_WEIGHTS[k]
            label = k.replace("_", " ").title()
            score_str = str(v) if v is not None else "—"
            print(f"  {label:<28} {score_str:<7} {w:.0%}")
        print(f"  {'-'*50}")
        print(f"  {'Weighted Composite':<28} {script['composite_score']}")
        save_manifest(manifest)
    else:
        print("No scores provided. Available flags:")
        for k in SCORE_FIELDS:
            flag = f"--{k.replace('_', '-')}"
            print(f"  {flag:<30} (weight: {SCORE_WEIGHTS[k]:.0%})")


def cmd_review(args):
    """Show full details for a single script."""
    manifest = load_manifest()

    script = next((s for s in manifest["scripts"] if s["id"] == args.id), None)
    if not script:
        print(f"ERROR: No script found with id '{args.id}'")
        sys.exit(1)

    print(f"=== {script['title']} ===\n")
    print(f"  ID:           {script['id']}")
    print(f"  Author:       {script['author']}")
    print(f"  URL:          {script['url'] or '—'}")
    print(f"  Family:       {script['family']}")
    print(f"  Type:         {script['type']}")
    print(f"  Pine Version: {script['pine_version']}")
    print(f"  Status:       {script['status']}")
    print(f"  Tags:         {', '.join(script.get('tags', [])) or '—'}")
    print(f"  Imported:     {script['imported_date']}")
    print(f"  Reviewed:     {script.get('reviewed_date') or '—'} by {script.get('reviewed_by') or '—'}")
    print(f"  Repaint Risk: {script['repaint_risk'] if script.get('repaint_risk') is not None else '—'}")

    print(f"\n  Files:")
    print(f"    Pine:    intake/{script['pine_file']}")
    print(f"    Cleaned: {script.get('cleaned_file') or '—'}")
    print(f"    Review:  {script.get('review_log') or '—'}")

    # Portfolio-aware metadata
    print(f"\n  Portfolio Metadata:")
    assets = script.get("asset_candidates", [])
    print(f"    Assets:         {', '.join(assets) if assets else '—'}")
    tfs = script.get("preferred_timeframes", [])
    print(f"    Timeframes:     {', '.join(tfs) if tfs else '—'}")
    print(f"    Session:        {script.get('session_window') or '—'}")
    print(f"    Strategy Class: {script.get('strategy_class') or '—'}")
    print(f"    Entry Style:    {script.get('entry_style') or '—'}")
    print(f"    Risk Model:     {script.get('risk_model') or '—'}")
    print(f"    Exit Model:     {script.get('exit_model') or '—'}")
    print(f"    Frequency:      {script.get('trade_frequency_estimate') or '—'}")
    if script.get("notes_market_behavior"):
        print(f"    Market Notes:   {script['notes_market_behavior']}")

    # Lab role
    print(f"\n  Lab Role:")
    print(f"    Portfolio Role: {script.get('portfolio_role') or '—'}")
    print(f"    Layer:          {script.get('layer') or '—'}")
    print(f"    Roster Target:  {script.get('roster_target') or '—'}")

    # Scores
    scores = script.get("scores", {})
    print(f"\n  Quality Scores (1-10, weighted):")
    for k in SCORE_FIELDS:
        v = scores.get(k)
        w = SCORE_WEIGHTS[k]
        label = k.replace("_", " ").title()
        print(f"    {label:<28} {v if v is not None else '—':<5} (w={w:.0%})")
    print(f"    {'Composite':<28} {script.get('composite_score') or '—'}")

    if script.get("description"):
        print(f"\n  Description:\n    {script['description']}")
    if script.get("notes"):
        print(f"\n  Notes:\n    {script['notes']}")


def cmd_search(args):
    manifest = load_manifest()
    query = args.query.lower()

    matches = [
        s for s in manifest["scripts"]
        if query in s["title"].lower()
        or query in s["description"].lower()
        or query in s["author"].lower()
        or query in " ".join(s.get("tags", [])).lower()
        or query in s.get("notes", "").lower()
        or query in s.get("family", "").lower()
        or query in " ".join(s.get("asset_candidates", [])).lower()
        or query in (s.get("strategy_class") or "").lower()
    ]

    if not matches:
        print(f"No scripts matching '{args.query}'")
        return

    print(f"{'ID':<40} {'FAMILY':<14} {'STATUS':<16} {'SCORE':<7} {'TITLE'}")
    print("-" * 114)
    for s in matches:
        score = s.get("composite_score")
        score_str = f"{score:.1f}" if score is not None else "—"
        print(f"{s['id']:<40} {s['family']:<14} {s['status']:<16} {score_str:<7} {s['title'][:36]}")
    print(f"\nFound: {len(matches)}")


def cmd_stats(args):
    manifest = load_manifest()
    scripts = manifest["scripts"]

    if not scripts:
        print("No scripts in manifest.")
        return

    print("=== Intake Pipeline Stats ===\n")

    # By status
    print("By Status:")
    for status in VALID_STATUSES:
        count = sum(1 for s in scripts if s["status"] == status)
        if count > 0:
            bar = "#" * count
            print(f"  {status:<18} {count:>4}  {bar}")

    print()

    # By family
    print("By Family:")
    for family in VALID_FAMILIES:
        count = sum(1 for s in scripts if s["family"] == family)
        if count > 0:
            bar = "#" * count
            print(f"  {family:<18} {count:>4}  {bar}")

    # By strategy class
    classes = set(s.get("strategy_class") for s in scripts if s.get("strategy_class"))
    if classes:
        print("\nBy Strategy Class:")
        for cls in sorted(classes):
            count = sum(1 for s in scripts if s.get("strategy_class") == cls)
            bar = "#" * count
            print(f"  {cls:<18} {count:>4}  {bar}")

    # Asset coverage
    all_assets = set()
    for s in scripts:
        all_assets.update(s.get("asset_candidates", []))
    if all_assets:
        print("\nAsset Coverage:")
        for asset in sorted(all_assets):
            count = sum(1 for s in scripts if asset in s.get("asset_candidates", []))
            bar = "#" * count
            print(f"  {asset:<18} {count:>4}  {bar}")

    # By layer
    layers = {"A": 0, "B": 0, "C": 0}
    for s in scripts:
        l = s.get("layer")
        if l in layers:
            layers[l] += 1
    if any(v > 0 for v in layers.values()):
        print("\nBy Layer:")
        layer_labels = {"A": "Core Killers", "B": "Enhancers", "C": "Master Stack"}
        for layer, count in layers.items():
            if count > 0:
                bar = "#" * count
                print(f"  {layer} ({layer_labels[layer]:<14}) {count:>4}  {bar}")

    # Scored scripts
    scored = [s for s in scripts if s.get("composite_score") is not None]
    if scored:
        print(f"\nScored: {len(scored)}/{len(scripts)}")
        avg = sum(s["composite_score"] for s in scored) / len(scored)
        top = max(scored, key=lambda s: s["composite_score"])
        print(f"  Average composite: {avg:.1f}")
        print(f"  Top script:        {top['id']} ({top['composite_score']:.1f})")

    print(f"\nTotal scripts: {len(scripts)}")


def cmd_export(args):
    """Export filtered scripts as JSON (for passing to other tools)."""
    manifest = load_manifest()
    scripts = manifest["scripts"]

    if args.family:
        scripts = [s for s in scripts if s["family"] == args.family]
    if args.status:
        scripts = [s for s in scripts if s["status"] == args.status]

    print(json.dumps(scripts, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Intake Manager v1.1 — TradingView script pipeline (portfolio-aware)")
    sub = parser.add_subparsers(dest="command")

    # add
    p_add = sub.add_parser("add", help="Add a new script to the manifest")
    p_add.add_argument("--title", required=True)
    p_add.add_argument("--url", default="")
    p_add.add_argument("--author", required=True)
    p_add.add_argument("--type", default="strategy", choices=VALID_TYPES)
    p_add.add_argument("--description", default="")
    p_add.add_argument("--pine-version", default="5")
    p_add.add_argument("--family", required=True, choices=VALID_FAMILIES)
    p_add.add_argument("--tags", default="")
    p_add.add_argument("--notes", default="")
    p_add.add_argument("--pine-file", default="")

    # list
    p_list = sub.add_parser("list", help="List scripts (sorted by composite score)")
    p_list.add_argument("--family", choices=VALID_FAMILIES)
    p_list.add_argument("--status", choices=VALID_STATUSES)

    # update
    p_update = sub.add_parser("update", help="Update a script's status or metadata")
    p_update.add_argument("id")
    p_update.add_argument("--status", choices=VALID_STATUSES)
    p_update.add_argument("--notes")
    p_update.add_argument("--family", choices=VALID_FAMILIES)
    p_update.add_argument("--repaint-risk", type=bool)
    p_update.add_argument("--reviewed-by", default="claude")
    p_update.add_argument("--cleaned-file")
    p_update.add_argument("--review-log")
    # Portfolio-aware update flags
    p_update.add_argument("--assets", help="Comma-separated asset candidates (MNQ,YM,MGC,MES)")
    p_update.add_argument("--timeframes", help="Comma-separated timeframes (1m,3m,5m,15m)")
    p_update.add_argument("--session-window", help="Session window (e.g. '08:30-11:00 ET')")
    p_update.add_argument("--strategy-class", choices=VALID_STRATEGY_CLASSES)
    p_update.add_argument("--entry-style", choices=VALID_ENTRY_STYLES)
    p_update.add_argument("--risk-model", choices=VALID_RISK_MODELS)
    p_update.add_argument("--exit-model", choices=VALID_EXIT_MODELS)
    p_update.add_argument("--frequency", choices=VALID_FREQUENCIES)
    p_update.add_argument("--market-notes", help="Market behavior notes")
    # Lab role flags
    p_update.add_argument("--portfolio-role", choices=VALID_PORTFOLIO_ROLES, help="core | enhancer | stack_component")
    p_update.add_argument("--layer", choices=VALID_LAYERS, help="A (killer) | B (enhancer) | C (stack)")
    p_update.add_argument("--roster-target", help="Roster target ID (e.g. ALGO-CORE-ORB-001)")

    # score
    p_score = sub.add_parser("score", help="Set quality scores (1-10, weighted composite)")
    p_score.add_argument("id")
    p_score.add_argument("--clarity", type=int, help="Code clarity (1-10, weight 15%%)")
    p_score.add_argument("--testability", type=int, help="Has entries/exits, backtestable (1-10, weight 25%%)")
    p_score.add_argument("--futures-fit", type=int, help="Suitable for MES/futures (1-10, weight 20%%)")
    p_score.add_argument("--conversion-difficulty", type=int, help="Ease of Pine→Python, 1=hard 10=easy (weight 10%%)")
    p_score.add_argument("--prop-fit", type=int, help="Prop firm viability (1-10, weight 20%%)")
    p_score.add_argument("--diversification-potential", type=int, help="Portfolio diversification value (1-10, weight 10%%)")

    # review (detailed view)
    p_review = sub.add_parser("review", help="Show full details for a script")
    p_review.add_argument("id")

    # search
    p_search = sub.add_parser("search", help="Search scripts by keyword")
    p_search.add_argument("query")

    # stats
    sub.add_parser("stats", help="Show pipeline statistics")

    # export
    p_export = sub.add_parser("export", help="Export filtered scripts as JSON")
    p_export.add_argument("--family", choices=VALID_FAMILIES)
    p_export.add_argument("--status", choices=VALID_STATUSES)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "add": cmd_add,
        "list": cmd_list,
        "update": cmd_update,
        "score": cmd_score,
        "review": cmd_review,
        "search": cmd_search,
        "stats": cmd_stats,
        "export": cmd_export,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
