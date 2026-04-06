#!/usr/bin/env python3
"""Strategy Digest Lead Fetcher — curated strategy summaries from digest databases.

Fetches from Quantpedia RSS and other strategy-digest sources where every
entry IS a documented strategy or systematic concept. Highest expected
conversion rate of any source — these are pre-filtered for testability.

Writes to ~/openclaw-intake/inbox/source_leads/digest_leads.md

This is a THIN FETCHER. Claw does the analysis and note writing.

Usage: python3 scripts/fetch_digest_leads.py
"""

import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

LEADS_DIR = Path.home() / "openclaw-intake" / "inbox" / "source_leads"
OUTPUT = LEADS_DIR / "digest_leads.md"
TIMESTAMP = datetime.now().strftime("%Y-%m-%d %H:%M")

MAX_LEADS = 20
MAX_PER_FEED = 10

USER_AGENT = "FQL-Harvest-Helper/1.0 (research tool)"

# ── Strategy digest RSS feeds ──────────────────────────────────────────────
# These sources specialize in curated, documented strategy summaries.
# Every entry is a strategy concept, not general market commentary.
FEEDS = [
    {
        "url": "https://quantpedia.com/feed/",
        "name": "Quantpedia",
        "category": "strategy_digest",
        "note": "Curated strategy database. Most entries are documented with performance data."
    },
    {
        "url": "https://investresolve.com/feed/",
        "name": "ReSolve Asset Management",
        "category": "strategy_digest",
        "note": "Managed futures / CTA research. Carry, trend, risk parity, portable alpha."
    },
    # QuantifiedStrategies does not have a working RSS — Claw searches
    # their site directly during academic_scan tasks.
]

# Strategy-relevance keywords (higher score = more likely a strategy concept)
STRATEGY_KEYWORDS = [
    "strategy", "trading", "momentum", "carry", "value", "mean reversion",
    "trend following", "volatility", "seasonality", "anomaly", "premium",
    "factor", "systematic", "backtest", "portfolio", "hedge", "spread",
    "futures", "commodities", "treasury", "rates", "equity",
    "cross-sectional", "time series", "roll yield", "term structure",
]

# Filter out non-strategy content (monthly updates, promotional, etc.)
NOISE_KEYWORDS = [
    "premium update", "monthly update", "in january", "in february",
    "in march", "in april", "in may", "in june", "in july",
    "in august", "in september", "in october", "in november", "in december",
    "quantpedia in ", "webinar", "discount", "subscription",
]


def fetch_rss(feed_url, max_items=10):
    """Fetch and parse RSS feed."""
    req = Request(feed_url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=10) as resp:
            tree = ET.parse(resp)
    except Exception as e:
        print(f"  Warning: failed to fetch {feed_url}: {e}", file=sys.stderr)
        return []

    root = tree.getroot()
    posts = []

    for item in root.iter("item"):
        title = item.findtext("title", "")
        link = item.findtext("link", "")
        description = item.findtext("description", "")

        if description:
            description = re.sub(r"<[^>]+>", " ", description)
            description = re.sub(r"\s+", " ", description).strip()[:600]

        posts.append({"title": title, "url": link, "excerpt": description})
        if len(posts) >= max_items:
            break

    return posts


def score_post(title, excerpt):
    """Score a post by strategy relevance. Filter out noise."""
    text = f"{title} {excerpt}".lower()

    # Check for noise
    for kw in NOISE_KEYWORDS:
        if kw in text:
            return -1  # Reject

    # Score by strategy keywords
    score = sum(1 for kw in STRATEGY_KEYWORDS if kw in text)
    return score


def main():
    LEADS_DIR.mkdir(parents=True, exist_ok=True)

    all_leads = []
    seen_urls = set()

    for feed in FEEDS:
        posts = fetch_rss(feed["url"], max_items=MAX_PER_FEED + 5)

        for post in posts:
            if not post["url"] or post["url"] in seen_urls:
                continue
            seen_urls.add(post["url"])

            score = score_post(post["title"], post.get("excerpt", ""))
            if score < 1:
                continue  # Noise or non-strategy

            post["source"] = feed["name"]
            post["category"] = feed["category"]
            post["relevance_score"] = score
            all_leads.append(post)

        time.sleep(0.5)

    # Sort by relevance
    all_leads.sort(key=lambda x: x["relevance_score"], reverse=True)
    all_leads = all_leads[:MAX_LEADS]

    # Write leads
    lines = [
        "# Strategy Digest Source Leads",
        f"# Generated: {TIMESTAMP}",
        "# For Claw to review during harvest tasks.",
        "#",
        "# These are CURATED STRATEGY SUMMARIES from strategy-digest databases.",
        "# Every entry is likely a documented strategy concept, not general commentary.",
        "# Claw should read each URL, extract the systematic/mechanical concept,",
        "# and write a standard harvest note if it translates to testable futures logic.",
        "#",
        "# Expected conversion rate: HIGH — these sources pre-filter for testability.",
        "",
    ]

    for lead in all_leads:
        lines.append(f"- title: {lead['title']}")
        lines.append(f"  url: {lead['url']}")
        lines.append(f"  source: {lead['source']}")
        lines.append(f"  relevance_score: {lead['relevance_score']}")
        if lead.get("excerpt"):
            excerpt = lead["excerpt"][:400].replace("\n", " ").replace("|", " ")
            lines.append(f"  excerpt: {excerpt}")
        lines.append("")

    lines.append(f"# Total leads: {len(all_leads)}")
    lines.append(f"# Feeds scanned: {len(FEEDS)}")
    lines.append(f"# Fetched: {TIMESTAMP}")

    OUTPUT.write_text("\n".join(lines))
    print(f"Digest leads: {len(all_leads)} strategies written to {OUTPUT}")


if __name__ == "__main__":
    main()
