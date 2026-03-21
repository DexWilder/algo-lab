#!/usr/bin/env python3
"""FQL Alert Engine — active operational intelligence.

Moves from passive reporting to action alerts. Scans for anomalies
across the entire platform and surfaces only what needs attention.

Design principle: high signal, low noise. Every alert must be actionable.
If an alert fires every day without action taken, it should be removed
or its threshold adjusted.

Usage:
    python3 scripts/fql_alerts.py              # Print alerts
    python3 scripts/fql_alerts.py --save       # Print + save to inbox
"""

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TRADE_LOG = ROOT / "logs" / "trade_log.csv"
SIGNAL_LOG = ROOT / "logs" / "signal_log.csv"
REGISTRY_PATH = ROOT / "research" / "data" / "strategy_registry.json"
HARVEST_DIR = Path.home() / "openclaw-intake" / "inbox" / "harvest"
LEADS_DIR = Path.home() / "openclaw-intake" / "inbox" / "source_leads"
MANIFEST_PATH = LEADS_DIR / "_manifest.json"
RECOVERY_LOG = ROOT / "research" / "logs" / "recovery_actions.log"
OUTPUT_PATH = Path.home() / "openclaw-intake" / "inbox" / "_alerts.md"

NOW = datetime.now()
TODAY = NOW.strftime("%Y-%m-%d")
TIMESTAMP = NOW.strftime("%Y-%m-%d %H:%M")

# Import aging logic
sys.path.insert(0, str(ROOT / "scripts"))
try:
    from probation_scoreboard import compute_aging, TARGETS, EXPECTED_FREQ, compute_forward_stats
except ImportError:
    compute_aging = None

FAMILY_TO_FACTOR = {
    "pullback": "MOMENTUM", "breakout": "MOMENTUM", "trend": "MOMENTUM",
    "mean_reversion": "MEAN_REVERSION", "event_driven": "EVENT",
    "carry": "CARRY", "afternoon_rates_reversion": "STRUCTURAL",
    "vol_expansion": "VOLATILITY", "structural": "STRUCTURAL",
    "volatility": "VOLATILITY",
}


def _load_json(path):
    try:
        return json.load(open(path))
    except Exception:
        return {}


def _load_csv(path):
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


# ── Alert checks ──────────────────────────────────────────────────────────

def check_helper_failures():
    """Flag source helpers that produced 0 leads on last run."""
    alerts = []
    if not MANIFEST_PATH.exists():
        return alerts
    manifest = _load_json(str(MANIFEST_PATH))
    runs = manifest.get("runs", [])
    if not runs:
        return alerts
    last = runs[-1]
    for source in ["github_leads", "reddit_leads", "youtube_leads", "blog_leads", "digest_leads"]:
        count = last.get(source, -1)
        if count == 0:
            name = source.replace("_leads", "")
            alerts.append({
                "level": "WARN",
                "category": "harvest",
                "message": f"{name} helper produced 0 leads on last run ({last.get('timestamp', '?')[:10]})",
                "action": f"Check scripts/fetch_{name}_leads.* for errors",
            })
    return alerts


def check_source_diversity():
    """Flag if one source type dominates recent harvest notes."""
    alerts = []
    if not HARVEST_DIR.exists():
        return alerts
    cutoff = (NOW - timedelta(days=7)).strftime("%Y-%m-%d")
    sources = Counter()
    total = 0
    for f in HARVEST_DIR.glob("*.md"):
        if f.name[:10] < cutoff:
            continue
        total += 1
        try:
            text = f.read_text()
            for line in text.split("\n"):
                if line.startswith("- source URL:"):
                    url = line.split(":", 1)[-1].strip()
                    if "tradingview" in url.lower():
                        sources["TradingView"] += 1
                    elif any(s in url.lower() for s in ["ssrn", "quantpedia", "doi.org", "arxiv"]):
                        sources["Academic"] += 1
                    elif "youtube" in url.lower():
                        sources["YouTube"] += 1
                    elif "github" in url.lower():
                        sources["GitHub"] += 1
                    elif "reddit" in url.lower():
                        sources["Reddit"] += 1
                    elif "internal" in url.lower():
                        sources["Claw"] += 1
                    else:
                        sources["Other"] += 1
                    break
        except Exception:
            pass

    if total > 10 and len(sources) < 3:
        alerts.append({
            "level": "WARN",
            "category": "harvest",
            "message": f"Source monoculture: only {len(sources)} source type(s) in {total} notes this week",
            "action": "Check that all helper lanes are running and Claw is using source_leads/",
        })
    if total > 0:
        dominant = sources.most_common(1)[0] if sources else ("?", 0)
        if dominant[1] / total > 0.6:
            alerts.append({
                "level": "INFO",
                "category": "harvest",
                "message": f"{dominant[0]} dominates at {dominant[1]}/{total} ({dominant[1]/total*100:.0f}%) this week",
                "action": "Consider adjusting lane caps or search diversity",
            })
    return alerts


def check_component_tagging():
    """Flag if new harvest notes lack component_type tags."""
    alerts = []
    if not HARVEST_DIR.exists():
        return alerts
    cutoff = (NOW - timedelta(days=7)).strftime("%Y-%m-%d")
    total = 0
    tagged = 0
    for f in HARVEST_DIR.glob("*.md"):
        if f.name[:10] < cutoff:
            continue
        total += 1
        try:
            text = f.read_text()
            if "component_type:" in text:
                tagged += 1
        except Exception:
            pass

    if total >= 10 and tagged == 0:
        alerts.append({
            "level": "WARN",
            "category": "harvest",
            "message": f"No component_type tags in {total} recent notes — fragment capture not working",
            "action": "Check _note_template.md and Claw task instructions for component_type guidance",
        })
    return alerts


def check_closed_family_violations():
    """Flag harvest notes that match closed families."""
    alerts = []
    # Load closed families from harvest config
    config_path = ROOT / "research" / "harvest_config.yaml"
    if not config_path.exists():
        return alerts
    try:
        import yaml
        config = yaml.safe_load(open(config_path))
    except Exception:
        return alerts

    closed = config.get("targeting", {}).get("high_bar_families", [])
    closed_names = [f.get("family", "").lower() for f in closed]

    if not HARVEST_DIR.exists():
        return alerts
    cutoff = (NOW - timedelta(days=7)).strftime("%Y-%m-%d")

    # Build specific match patterns for each closed family
    # Only match on distinctive multi-word phrases, not single common words
    match_phrases = []
    for fam in closed:
        name = fam.get("family", "").lower()
        # Skip families with generic words like "any"
        if " x any" in name:
            # For "ict x any", match on ICT-specific terminology only
            # Must be unambiguous — "ict" alone matches "verdict", "predict", etc.
            match_phrases.append(("ict concepts", name, ["order block", "fair value gap", " fvg ", "smart money concept", " ict "]))
        elif "overnight" in name and "equity" in name:
            match_phrases.append(("overnight equity", name, ["overnight drift", "overnight premium", "overnight continuation"]))
        elif "gap_fade" in name or "gap_reversal" in name:
            match_phrases.append(("gap fade", name, ["gap fade", "gap reversal", "gap fill"]))
        elif "breakout x morning" in name:
            match_phrases.append(("morning breakout", name, ["morning breakout", "opening range breakout"]))
        elif "cash_close_reversion" in name:
            match_phrases.append(("cash close reversion", name, ["cash close", "15:00 reversion", "close reversion"]))

    for f in HARVEST_DIR.glob("*.md"):
        if f.name[:10] < cutoff:
            continue
        try:
            text = f.read_text().lower()
            for _, family_name, search_terms in match_phrases:
                if any(term in text for term in search_terms):
                    alerts.append({
                        "level": "WARN",
                        "category": "harvest",
                        "message": f"Possible closed-family match in {f.name}: '{family_name}'",
                        "action": "Review note — reject if it doesn't address the prior failure mode",
                    })
                    break
        except Exception:
            pass
    return alerts


def check_probation_aging():
    """Flag probation strategies that are stale, under-evidenced, or at gate."""
    alerts = []
    if compute_aging is None:
        return alerts

    reg = _load_json(str(REGISTRY_PATH))
    if not reg:
        return alerts
    trades = _load_csv(str(TRADE_LOG))
    registry_map = {s["strategy_id"]: s for s in reg.get("strategies", []) if s.get("status") == "probation"}

    for sid in TARGETS:
        if sid not in registry_map:
            continue
        a = compute_aging(sid, trades, registry_map)
        status = a["aging_status"]

        if status == "STALE":
            alerts.append({
                "level": "ALERT",
                "category": "probation",
                "message": f"{sid}: STALE — {a['days_in_probation']}d, {a['actual_trades']} trades (expected {a['expected_by_now']:.0f})",
                "action": "Investigate: controller blocking? Data feed? Strategy logic?",
            })
        elif status == "UNDER_EVIDENCED":
            alerts.append({
                "level": "WARN",
                "category": "probation",
                "message": f"{sid}: under-evidenced — ratio {a['evidence_ratio']:.2f} ({a['actual_trades']} vs {a['expected_by_now']:.0f} expected)",
                "action": "Monitor — may need investigation if ratio stays low",
            })
        elif status == "FAILING":
            alerts.append({
                "level": "ALERT",
                "category": "probation",
                "message": f"{sid}: FAILING — {a['actual_trades']} trades, PF {a.get('pf', '?')}",
                "action": "Downgrade decision needed",
            })
        elif status in ("GATE_REACHED", "REVIEW_READY"):
            alerts.append({
                "level": "ACTION",
                "category": "probation",
                "message": f"{sid}: reached review gate — {a['actual_trades']} trades",
                "action": "Promotion/continuation/downgrade decision needed",
            })

        # Time pressure
        if a["pct_time_used"] > 75:
            alerts.append({
                "level": "INFO",
                "category": "probation",
                "message": f"{sid}: {a['pct_time_used']:.0f}% of probation window used ({a['weeks_in_probation']:.0f}w/{a['max_weeks']}w)",
                "action": "Approaching deadline — ensure evidence is accumulating",
            })

    return alerts


def check_short_side_dependence():
    """Flag if ZN-Afternoon-Reversion's short side stops carrying."""
    alerts = []
    trades = _load_csv(str(TRADE_LOG))
    if trades.empty or "strategy" not in trades.columns:
        return alerts

    zn_trades = trades[trades["strategy"] == "ZN-Afternoon-Reversion"]
    if len(zn_trades) < 10:
        return alerts

    if "side" not in zn_trades.columns:
        return alerts

    shorts = zn_trades[zn_trades["side"] == "short"]
    total_pnl = zn_trades["pnl"].sum()
    short_pnl = shorts["pnl"].sum() if not shorts.empty else 0

    if total_pnl != 0:
        short_pct = short_pnl / total_pnl * 100
        if short_pnl <= 0:
            alerts.append({
                "level": "ALERT",
                "category": "probation",
                "message": f"ZN-Afternoon-Reversion: short side NOT carrying (short PnL ${short_pnl:+,.0f})",
                "action": "Investigate — backtest was 89% short PnL. Edge may have shifted.",
            })
        elif short_pct < 50:
            alerts.append({
                "level": "WARN",
                "category": "probation",
                "message": f"ZN-Afternoon-Reversion: short bias weaker than expected ({short_pct:.0f}% vs 89% backtest)",
                "action": "Monitor — may be normal variance or regime shift",
            })

    return alerts


def check_recovery_activity():
    """Flag if too many recovery actions happened today."""
    alerts = []
    if not Path(RECOVERY_LOG).exists():
        return alerts
    today_count = 0
    try:
        for line in open(RECOVERY_LOG):
            if TODAY in line:
                today_count += 1
    except Exception:
        pass

    if today_count >= 5:
        alerts.append({
            "level": "ALERT",
            "category": "infrastructure",
            "message": f"{today_count} recovery actions today — system may be unstable",
            "action": "Check watchdog logs and service health",
        })
    return alerts


# ── Main ──────────────────────────────────────────────────────────────────

def generate_alerts():
    """Run all alert checks and return sorted alerts."""
    all_alerts = []
    all_alerts.extend(check_helper_failures())
    all_alerts.extend(check_source_diversity())
    all_alerts.extend(check_component_tagging())
    all_alerts.extend(check_closed_family_violations())
    all_alerts.extend(check_probation_aging())
    all_alerts.extend(check_short_side_dependence())
    all_alerts.extend(check_recovery_activity())

    # Sort by severity
    level_order = {"ALERT": 0, "ACTION": 1, "WARN": 2, "INFO": 3}
    all_alerts.sort(key=lambda a: level_order.get(a["level"], 99))

    return all_alerts


def format_report(alerts):
    lines = []
    lines.append("# FQL Alerts")
    lines.append(f"*{TIMESTAMP}*")
    lines.append("")

    if not alerts:
        lines.append("No alerts. All systems nominal.")
        return "\n".join(lines)

    # Count by level
    counts = Counter(a["level"] for a in alerts)
    summary_parts = []
    for level in ["ALERT", "ACTION", "WARN", "INFO"]:
        if counts.get(level, 0) > 0:
            summary_parts.append(f"{counts[level]} {level}")
    lines.append(f"**{' | '.join(summary_parts)}**")
    lines.append("")

    # Group by category
    by_cat = {}
    for a in alerts:
        by_cat.setdefault(a["category"], []).append(a)

    for cat in ["probation", "harvest", "infrastructure"]:
        items = by_cat.get(cat, [])
        if not items:
            continue
        lines.append(f"## {cat.title()}")
        lines.append("")
        for a in items:
            icon = {"ALERT": "!!", "ACTION": ">>", "WARN": "**", "INFO": "--"}.get(a["level"], "--")
            lines.append(f"{icon} [{a['level']}] {a['message']}")
            lines.append(f"   Action: {a['action']}")
            lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="FQL Alert Engine")
    parser.add_argument("--save", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    alerts = generate_alerts()

    if args.json:
        print(json.dumps(alerts, indent=2))
    else:
        report = format_report(alerts)
        print(report)

    if args.save:
        report = format_report(alerts)
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_PATH, "w") as f:
            f.write(report)
        print(f"\n  Saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
