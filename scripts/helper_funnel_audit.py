#!/usr/bin/env python3
"""Helper Funnel Audit — find exactly where good ideas are being lost.

Runs each helper in debug mode, tracks every candidate at every stage,
and reports rejection reasons, tier distribution, and leak points.

Usage:
    python3 scripts/helper_funnel_audit.py              # Full audit
    python3 scripts/helper_funnel_audit.py --helper reddit  # Single helper
    python3 scripts/helper_funnel_audit.py --save       # Save to inbox
"""

import argparse
import json
import sys
import time
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from lead_scorer import score_lead, tier_lead

INBOX = Path.home() / "openclaw-intake" / "inbox"
HARVEST_DIR = INBOX / "harvest"
OUTPUT = INBOX / "_helper_funnel_audit.md"
NOW = datetime.now().strftime("%Y-%m-%d %H:%M")
USER_AGENT = "FQL-Harvest-Helper/1.0 (research tool)"

JUNK_KEYWORDS = ["crypto", "bitcoin", "ethereum", "defi", "nft", "web3",
                  "solana", "binance", "uniswap"]


def audit_reddit():
    """Audit Reddit helper funnel with expanded search."""
    subreddits = ["algotrading", "quant", "FuturesTrading",
                  "quantfinance", "options", "RealDayTrading"]
    queries = [
        "futures strategy systematic",
        "volatility targeting futures",
        "carry trade futures",
        "value investing systematic",
        "crude oil futures strategy",
        "treasury futures",
        "session microstructure",
        "mean reversion futures",
        "backtest results",
        "entry exit rules",
        "stop loss strategy",
        "intraday strategy rules",
    ]

    funnel = {
        "raw_seen": 0,
        "junk_filtered": 0,
        "low_upvotes": 0,
        "duplicate": 0,
        "scored": 0,
        "tier_A": 0, "tier_B": 0, "tier_C": 0, "tier_R": 0,
        "rejection_reasons": Counter(),
        "top_leads": [],
        "sample_rejects": [],
    }

    seen = set()
    all_candidates = []

    for sub in subreddits:
        for query in queries:
            url = (f"https://www.reddit.com/r/{sub}/search.json"
                   f"?q={quote(query)}&sort=top&t=year&limit=5&restrict_sr=on")
            req = Request(url, headers={"User-Agent": USER_AGENT})
            try:
                with urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read())
                for child in data.get("data", {}).get("children", []):
                    d = child.get("data", {})
                    funnel["raw_seen"] += 1

                    title = d.get("title", "")
                    permalink = d.get("permalink", "")
                    post_url = f"https://reddit.com{permalink}"
                    ups = d.get("ups", 0)
                    selftext = d.get("selftext", "")[:500]

                    # Junk filter
                    if any(kw in title.lower() for kw in JUNK_KEYWORDS):
                        funnel["junk_filtered"] += 1
                        funnel["rejection_reasons"]["crypto/junk keyword"] += 1
                        continue

                    # Upvote filter
                    if ups < 3:
                        funnel["low_upvotes"] += 1
                        funnel["rejection_reasons"]["low upvotes (<3)"] += 1
                        continue

                    # Duplicate
                    if post_url in seen:
                        funnel["duplicate"] += 1
                        funnel["rejection_reasons"]["duplicate"] += 1
                        continue
                    seen.add(post_url)

                    # Score
                    full_text = f"{title} {selftext}"
                    result = score_lead(full_text, title)
                    tier = tier_lead(result)
                    funnel["scored"] += 1
                    funnel[f"tier_{tier}"] += 1

                    candidate = {
                        "title": title[:80],
                        "url": post_url,
                        "ups": ups,
                        "tier": tier,
                        "mechanism": result["mechanism_score"],
                        "noise": result["noise_score"],
                        "components": result["component_hints"],
                        "sub": sub,
                    }

                    if tier == "R":
                        funnel["rejection_reasons"]["noise dominates (tier R)"] += 1
                        if len(funnel["sample_rejects"]) < 5:
                            funnel["sample_rejects"].append(candidate)
                    else:
                        all_candidates.append(candidate)

                    if tier == "A" and len(funnel["top_leads"]) < 5:
                        funnel["top_leads"].append(candidate)

            except Exception:
                pass
            time.sleep(0.8)

    funnel["kept"] = len(all_candidates)
    return funnel


def audit_youtube():
    """Audit YouTube helper funnel."""
    import re

    queries = [
        "futures trading strategy systematic",
        "volatility managed portfolio",
        "commodity futures carry trade",
        "mean reversion futures intraday",
        "algorithmic trading futures backtest",
        "treasury bond futures strategy",
        "crude oil futures systematic",
        "session microstructure trading",
        "trading strategy rules mechanical",
        "backtest results futures",
    ]

    funnel = {
        "raw_seen": 0,
        "junk_filtered": 0,
        "no_transcript": 0,
        "low_quality_title": 0,
        "scored": 0,
        "tier_A": 0, "tier_B": 0, "tier_C": 0, "tier_R": 0,
        "rejection_reasons": Counter(),
        "top_leads": [],
        "sample_rejects": [],
    }

    seen = set()

    for query in queries:
        url = f"https://www.youtube.com/results?search_query={quote(query)}&sp=EgIQAQ%253D%253D"
        req = Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urlopen(req, timeout=10) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
        except Exception:
            continue

        video_ids = []
        for vid in re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', html):
            if vid not in seen:
                seen.add(vid)
                video_ids.append(vid)
            if len(video_ids) >= 5:
                break

        titles = re.findall(r'"title":\{"runs":\[\{"text":"([^"]+)"\}', html)

        for i, vid in enumerate(video_ids):
            title = titles[i] if i < len(titles) else "Unknown"
            funnel["raw_seen"] += 1

            if any(kw in title.lower() for kw in JUNK_KEYWORDS + ["scam", "motivation"]):
                funnel["junk_filtered"] += 1
                funnel["rejection_reasons"]["junk keyword"] += 1
                continue

            # Try transcript
            excerpt = None
            try:
                from youtube_transcript_api import YouTubeTranscriptApi
                transcript = YouTubeTranscriptApi.get_transcript(vid)
                full_text = " ".join(e["text"] for e in transcript)
                excerpt = full_text[:500]
            except Exception:
                funnel["no_transcript"] += 1

            # Score with whatever we have
            score_text = f"{title} {excerpt or ''}"
            result = score_lead(score_text, title)
            tier = tier_lead(result)

            # Quality gate: no transcript AND low mechanism = reject
            if excerpt is None and result["mechanism_score"] < 4:
                funnel["low_quality_title"] += 1
                funnel["rejection_reasons"]["no transcript + low mechanism"] += 1
                continue

            funnel["scored"] += 1
            funnel[f"tier_{tier}"] += 1

            candidate = {
                "title": title[:80],
                "vid": vid,
                "tier": tier,
                "mechanism": result["mechanism_score"],
                "has_transcript": excerpt is not None,
                "components": result["component_hints"],
            }

            if tier == "R":
                funnel["rejection_reasons"]["noise dominates (tier R)"] += 1
                if len(funnel["sample_rejects"]) < 3:
                    funnel["sample_rejects"].append(candidate)
            elif tier == "A" and len(funnel["top_leads"]) < 3:
                funnel["top_leads"].append(candidate)

        time.sleep(2)

    funnel["kept"] = funnel["tier_A"] + funnel["tier_B"] + funnel["tier_C"]
    return funnel


def audit_github():
    """Audit GitHub helper funnel."""
    import subprocess

    queries = [
        "quantitative trading strategy",
        "systematic trading backtest",
        "volatility managed portfolio",
        "algorithmic trading futures",
        "backtesting framework python trading",
        "carry trade systematic",
        "mean reversion trading strategy",
        "commodity trading systematic",
        "intraday trading strategy python",
        "trading strategy backtest python",
    ]

    funnel = {
        "raw_seen": 0,
        "junk_filtered": 0,
        "low_stars": 0,
        "duplicate": 0,
        "scored": 0,
        "tier_A": 0, "tier_B": 0, "tier_C": 0, "tier_R": 0,
        "rejection_reasons": Counter(),
        "top_leads": [],
    }

    seen = set()

    for query in queries:
        try:
            result = subprocess.run(
                ["gh", "search", "repos", query,
                 "--limit", "5", "--sort", "stars", "--order", "desc",
                 "--json", "fullName,description,url,stargazersCount"],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode != 0:
                continue
            repos = json.loads(result.stdout)
        except Exception:
            continue

        for repo in repos:
            funnel["raw_seen"] += 1
            url = repo.get("url", "")
            desc = (repo.get("description") or "").lower()
            stars = repo.get("stargazersCount", 0)

            if any(junk in desc for junk in JUNK_KEYWORDS):
                funnel["junk_filtered"] += 1
                funnel["rejection_reasons"]["junk keyword"] += 1
                continue

            if stars < 5:
                funnel["low_stars"] += 1
                funnel["rejection_reasons"]["low stars (<5)"] += 1
                continue

            if url in seen:
                funnel["duplicate"] += 1
                funnel["rejection_reasons"]["duplicate"] += 1
                continue
            seen.add(url)

            result = score_lead(desc, repo.get("fullName", ""))
            tier = tier_lead(result)
            funnel["scored"] += 1
            funnel[f"tier_{tier}"] += 1

            if tier == "R":
                funnel["rejection_reasons"]["noise dominates"] += 1

            if tier in ("A", "B") and len(funnel["top_leads"]) < 5:
                funnel["top_leads"].append({
                    "name": repo.get("fullName", ""),
                    "stars": stars,
                    "tier": tier,
                    "mechanism": result["mechanism_score"],
                })

    funnel["kept"] = funnel["tier_A"] + funnel["tier_B"] + funnel["tier_C"]
    return funnel


def format_funnel(name, funnel):
    """Format a single helper's funnel results."""
    lines = []
    lines.append(f"### {name}")
    lines.append("")

    raw = funnel["raw_seen"]
    kept = funnel.get("kept", 0)
    pass_rate = kept / raw * 100 if raw > 0 else 0

    lines.append(f"| Stage | Count | % of Raw |")
    lines.append(f"|-------|-------|----------|")
    lines.append(f"| Raw candidates seen | {raw} | 100% |")

    for reason, count in sorted(funnel.get("rejection_reasons", {}).items(), key=lambda x: -x[1]):
        pct = count / raw * 100 if raw > 0 else 0
        lines.append(f"| Rejected: {reason} | {count} | {pct:.0f}% |")

    lines.append(f"| **Scored** | **{funnel.get('scored', 0)}** | **{funnel.get('scored',0)/raw*100:.0f}%** |")
    lines.append(f"| Tier A (mechanical) | {funnel['tier_A']} | {funnel['tier_A']/raw*100:.0f}% |")
    lines.append(f"| Tier B (fragment) | {funnel['tier_B']} | {funnel['tier_B']/raw*100:.0f}% |")
    lines.append(f"| Tier C (weak) | {funnel['tier_C']} | {funnel['tier_C']/raw*100:.0f}% |")
    lines.append(f"| Tier R (rejected by score) | {funnel['tier_R']} | {funnel['tier_R']/raw*100:.0f}% |")
    lines.append(f"| **Kept (A+B+C)** | **{kept}** | **{pass_rate:.0f}%** |")

    if funnel.get("top_leads"):
        lines.append("")
        lines.append(f"**Top leads found:**")
        for lead in funnel["top_leads"][:3]:
            title = lead.get("title", lead.get("name", "?"))
            tier = lead.get("tier", "?")
            mech = lead.get("mechanism", 0)
            comps = ", ".join(lead.get("components", [])) or "none"
            lines.append(f"- [{tier}] {title} (mechanism={mech}, components=[{comps}])")

    if funnel.get("sample_rejects"):
        lines.append("")
        lines.append(f"**Sample rejected (check for false negatives):**")
        for rej in funnel["sample_rejects"][:3]:
            title = rej.get("title", "?")
            mech = rej.get("mechanism", 0)
            noise = rej.get("noise", 0)
            lines.append(f"- {title} (mechanism={mech}, noise={noise})")

    lines.append("")
    return lines


def generate_report(helpers_to_run=None):
    lines = []
    lines.append("# Helper Funnel Audit")
    lines.append(f"*{NOW}*")
    lines.append("")
    lines.append("*Finding where good ideas are being lost.*")
    lines.append("")

    all_helpers = {
        "Reddit": audit_reddit,
        "YouTube": audit_youtube,
        "GitHub": audit_github,
    }

    if helpers_to_run:
        all_helpers = {k: v for k, v in all_helpers.items() if k.lower() in [h.lower() for h in helpers_to_run]}

    totals = {"raw": 0, "kept": 0, "tier_A": 0, "tier_B": 0, "tier_C": 0, "tier_R": 0}

    for name, audit_fn in all_helpers.items():
        print(f"  Auditing {name}...", flush=True)
        try:
            funnel = audit_fn()
            lines.extend(format_funnel(name, funnel))
            totals["raw"] += funnel["raw_seen"]
            totals["kept"] += funnel.get("kept", 0)
            totals["tier_A"] += funnel["tier_A"]
            totals["tier_B"] += funnel["tier_B"]
            totals["tier_C"] += funnel["tier_C"]
            totals["tier_R"] += funnel["tier_R"]
        except Exception as e:
            lines.append(f"### {name}")
            lines.append(f"Error: {e}")
            lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")
    raw = totals["raw"]
    kept = totals["kept"]
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total raw candidates | {raw} |")
    lines.append(f"| Total kept (A+B+C) | {kept} ({kept/raw*100:.0f}% pass rate) |" if raw > 0 else f"| Total kept | 0 |")
    lines.append(f"| Tier A | {totals['tier_A']} |")
    lines.append(f"| Tier B | {totals['tier_B']} |")
    lines.append(f"| Tier C | {totals['tier_C']} |")
    lines.append(f"| Tier R (rejected) | {totals['tier_R']} |")

    # Diagnosis
    lines.append("")
    lines.append("## Diagnosis")
    lines.append("")

    if raw < 30:
        lines.append("- **Under-searching:** < 30 raw candidates. Expand queries and subreddits.")
    if raw > 0 and kept / raw < 0.2:
        lines.append("- **Over-filtering:** < 20% pass rate. Loosen scoring thresholds or noise penalties.")
    if totals["tier_A"] == 0:
        lines.append("- **No Tier A leads:** scoring may be too strict, or sources lack mechanical content.")
    if totals["tier_R"] > totals["kept"]:
        lines.append("- **More rejects than keeps:** review sample_rejects for false negatives.")
    if raw > 0 and kept / raw >= 0.2 and totals["tier_A"] > 0:
        lines.append("- Funnel looks healthy. Review top leads for quality.")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Helper Funnel Audit")
    parser.add_argument("--helper", nargs="*", help="Specific helpers to audit (reddit, youtube, github)")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    report = generate_report(args.helper)
    print(report)

    if args.save:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT, "w") as f:
            f.write(report)
        print(f"\n  Saved to: {OUTPUT}")


if __name__ == "__main__":
    main()
