#!/usr/bin/env python3
"""Practitioner Blog/Substack Lead Fetcher — RSS-based quant blog scanner.

Fetches recent posts from curated list of high-quality quant blogs via RSS.
Filters for strategy-relevant content using keyword scoring.
Writes leads to ~/openclaw-intake/inbox/source_leads/blog_leads.md

This is the highest-value missing source class: long-form practitioner
writing where unusual, implementation-ready ideas live. Signal/noise
ratio is much higher than Reddit or YouTube because authors self-select
for depth and specificity.

This is a THIN FETCHER. It gathers URLs, titles, and excerpts.
Claw does the analysis, factor tagging, and note writing.

Usage: python3 scripts/fetch_blog_leads.py
"""

import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

LEADS_DIR = Path.home() / "openclaw-intake" / "inbox" / "source_leads"
OUTPUT = LEADS_DIR / "blog_leads.md"
TIMESTAMP = datetime.now().strftime("%Y-%m-%d %H:%M")

MAX_LEADS = 20
MAX_PER_FEED = 4
MAX_AGE_DAYS = 30  # Only posts from last 30 days

USER_AGENT = "FQL-Harvest-Helper/1.0 (research tool)"

# ── Curated feed list ──────────────────────────────────────────────────────
# High-signal practitioner blogs with RSS feeds. Organized by primary
# contribution to FQL portfolio gaps.
#
# To add a new feed: append to this list with a category tag.
# To disable a feed: comment it out.
FEEDS = [
    # Quantitative strategy research (broad)
    {"url": "https://alphaarchitect.com/feed/", "name": "Alpha Architect", "category": "quant_research"},
    {"url": "https://robotwealth.com/feed/", "name": "Robot Wealth", "category": "quant_research"},
    {"url": "https://blog.thinknewfound.com/feed/", "name": "Newfound Research (Flirting with Models)", "category": "quant_research"},

    # Managed futures / CTA / carry / vol
    {"url": "https://www.returnstacked.com/feed/", "name": "Return Stacked", "category": "managed_futures"},

    # Managed futures / CTA / carry / vol (additional)
    {"url": "https://investresolve.com/feed/", "name": "ReSolve Asset Management", "category": "managed_futures"},
    # Verdad Capital — no working RSS feed (custom CMS). Claw searches directly.

    # Vol / options / market structure
    {"url": "https://moontowermeta.com/feed/", "name": "Moontower (Kris Abdelmessih)", "category": "vol_structure"},

    # Value / macro / portfolio construction
    {"url": "https://www.philosophicaleconomics.com/feed/", "name": "Philosophical Economics", "category": "value_macro"},
    {"url": "https://mutinyfund.com/feed/", "name": "Mutiny Fund", "category": "portfolio_construction"},
]

# Strategy-relevance keywords (scored by specificity)
HIGH_KEYWORDS = [
    "backtest", "systematic", "futures", "carry trade", "volatility managed",
    "mean reversion", "momentum", "trend following", "risk parity",
    "time series momentum", "cross-sectional", "factor", "roll yield",
    "term structure", "value", "rebalance", "drawdown", "sharpe",
    "walk forward", "out of sample", "signal", "entry", "exit",
]
LOW_KEYWORDS = [
    "strategy", "trading", "portfolio", "returns", "performance",
    "allocation", "diversification", "hedge", "exposure",
]


def fetch_rss(feed_url, max_items=5):
    """Fetch and parse RSS feed. Returns list of post dicts."""
    req = Request(feed_url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=10) as resp:
            tree = ET.parse(resp)
    except Exception as e:
        print(f"  Warning: failed to fetch {feed_url}: {e}", file=sys.stderr)
        return []

    root = tree.getroot()
    posts = []

    # Handle both RSS 2.0 and Atom formats
    # RSS 2.0: channel/item
    for item in root.iter("item"):
        title = item.findtext("title", "")
        link = item.findtext("link", "")
        pub_date = item.findtext("pubDate", "")
        description = item.findtext("description", "")

        # Clean HTML from description
        if description:
            description = re.sub(r"<[^>]+>", " ", description)
            description = re.sub(r"\s+", " ", description).strip()[:500]

        posts.append({
            "title": title,
            "url": link,
            "pub_date": pub_date,
            "excerpt": description,
        })
        if len(posts) >= max_items:
            break

    # Atom: entry
    if not posts:
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for entry in root.iter("{http://www.w3.org/2005/Atom}entry"):
            title = entry.findtext("{http://www.w3.org/2005/Atom}title", "")
            link_el = entry.find("{http://www.w3.org/2005/Atom}link")
            link = link_el.get("href", "") if link_el is not None else ""
            summary = entry.findtext("{http://www.w3.org/2005/Atom}summary", "")
            if summary:
                summary = re.sub(r"<[^>]+>", " ", summary)
                summary = re.sub(r"\s+", " ", summary).strip()[:500]

            posts.append({
                "title": title,
                "url": link,
                "pub_date": "",
                "excerpt": summary,
            })
            if len(posts) >= max_items:
                break

    return posts


def score_relevance(title, excerpt):
    """Score a post by strategy relevance. Higher = more relevant."""
    text = f"{title} {excerpt}".lower()
    high = sum(2 for kw in HIGH_KEYWORDS if kw in text)
    low = sum(1 for kw in LOW_KEYWORDS if kw in text)
    return high + low


def main():
    LEADS_DIR.mkdir(parents=True, exist_ok=True)

    all_leads = []
    seen_urls = set()

    for feed in FEEDS:
        posts = fetch_rss(feed["url"], max_items=MAX_PER_FEED + 2)

        for post in posts:
            if not post["url"] or post["url"] in seen_urls:
                continue
            seen_urls.add(post["url"])

            score = score_relevance(post["title"], post.get("excerpt", ""))
            if score < 2:
                continue  # Too generic

            post["source"] = feed["name"]
            post["category"] = feed["category"]
            post["relevance_score"] = score
            all_leads.append(post)

        time.sleep(0.5)

    # Score with shared scorer
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from lead_scorer import score_lead, tier_lead, format_score_line

    for lead in all_leads:
        full_text = f"{lead['title']} {lead.get('excerpt', '')}"
        result = score_lead(full_text, lead["title"])
        tier = tier_lead(result)
        lead["_score"] = result
        lead["_tier"] = tier
        lead["_score_line"] = format_score_line(result, tier)
        # Combine old relevance + mechanism score
        lead["relevance_score"] = lead["relevance_score"] + result["net_score"]

    # Filter rejects, sort by combined score
    all_leads = [l for l in all_leads if l.get("_tier") != "R"]
    all_leads.sort(key=lambda x: x["relevance_score"], reverse=True)
    all_leads = all_leads[:MAX_LEADS]

    # Write leads
    lines = [
        "# Practitioner Blog Source Leads (scored)",
        f"# Generated: {TIMESTAMP}",
        "# Scored by mechanism density. Tiers: A/B/C/R.",
        "",
    ]

    for lead in all_leads:
        lines.append(f"- title: {lead['title']}")
        lines.append(f"  url: {lead['url']}")
        lines.append(f"  source: {lead['source']}")
        lines.append(f"  category: {lead['category']}")
        lines.append(f"  relevance_score: {lead['relevance_score']}")
        if lead.get("_score_line"):
            lines.append(f"  score: {lead['_score_line']}")
        if lead.get("excerpt"):
            excerpt = lead["excerpt"][:300].replace("\n", " ").replace("|", " ")
            lines.append(f"  excerpt: {excerpt}")
        lines.append("")

    lines.append(f"# Total leads: {len(all_leads)}")
    lines.append(f"# Feeds scanned: {len(FEEDS)}")
    lines.append(f"# Fetched: {TIMESTAMP}")

    OUTPUT.write_text("\n".join(lines))
    print(f"Blog leads: {len(all_leads)} posts written to {OUTPUT}")


if __name__ == "__main__":
    main()
