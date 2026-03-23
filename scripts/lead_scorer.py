"""FQL Lead Scorer — shared mechanism-density scoring for all source helpers.

Scores leads by extractable mechanical substance, not title appeal.
Used by all fetchers to rank and tier leads before Claw synthesis.

CORE DOCTRINE:
  source role = ranking (caps, priority, expectations)
  content quality = survival (mechanism density decides keep/reject)
  closed family / obvious junk = rejection (hard block)

  Never reject a lead just because of its source class if the content
  itself contains a testable mechanism or useful fragment. A good idea
  from an ugly place is still a good idea.

Scoring rules:
  - Rank by mechanism strength, not headline quality
  - Prefer explicit rules, entries, exits, filters, regime logic
  - Allow partial fragments through if they look reusable
  - Suppress only truly obvious junk (no rules, pure hype, crypto, ICT)
  - Bias toward portfolio usefulness and novelty

Usage:
    from lead_scorer import score_lead, tier_lead, detect_components
"""

# ── Mechanism indicators ──────────────────────────────────────────────────
# Words/phrases that indicate testable, mechanical content.
# Higher weight = stronger signal of actionable strategy logic.

STRONG_MECHANISM = [
    # Entry/exit rules (formal)
    "entry when", "enter when", "buy when", "sell when", "go long when",
    "go short when", "exit when", "exit after", "close position",
    "stop loss", "stop at", "take profit", "profit target",
    # Entry/exit rules (informal — how Reddit/YouTube actually talk)
    "i enter", "i buy", "i sell", "i short", "i exit",
    "my entry", "my exit", "my stop", "my target",
    "the rule is", "the signal is", "trigger is",
    "when price", "if price", "when it breaks", "if it crosses",
    "above the", "below the", "breaks above", "breaks below",
    # Filters and conditions
    "filter by", "only when", "only during", "only if", "condition",
    "threshold", "crosses", "breakout",
    # Specific mechanics
    "atr", "vwap", "ema", "sma", "rsi", "bollinger", "macd",
    "z-score", "percentile", "standard deviation",
    "rebalance", "lookback", "rolling", "moving average",
    # Backtest evidence
    "backtest", "backtested", "sharpe", "profit factor", "win rate",
    "drawdown", "walk forward", "out of sample", "sample size",
    "tested on", "tested over", "results show",
    # Strategy structure
    "systematic", "mechanical", "algorithmic", "quantitative",
    "rules-based", "rule-based", "rules based",
    # Timing/session (informal)
    "at the open", "at close", "first hour", "last hour",
    "overnight", "pre-market", "after hours", "london session",
    "new york session", "asian session",
]

MODERATE_MECHANISM = [
    # General strategy terms
    "strategy", "signal", "indicator", "momentum", "mean reversion",
    "carry", "volatility", "trend", "breakout", "squeeze",
    # Asset/session specificity
    "futures", "es", "nq", "gc", "cl", "zn", "zb",
    "session", "overnight", "morning", "afternoon", "close",
    "london", "tokyo", "new york",
    # Portfolio concepts
    "portfolio", "allocation", "diversification", "risk parity",
    "correlation", "hedge", "sizing",
]

NOISE_INDICATORS = [
    # Discretionary/vague
    "i think", "i believe", "in my opinion", "what do you think",
    "just my thoughts", "feel like", "gut feeling",
    # Hype/motivation
    "life changing", "quit your job", "millionaire", "get rich",
    "secret", "guru", "holy grail", "guaranteed",
    # Crypto/irrelevant
    "crypto", "bitcoin", "ethereum", "nft", "defi", "web3",
    "solana", "binance", "meme coin",
    # Pure narrative
    "my journey", "day in the life", "motivation", "mindset",
]

# ── Component detection ───────────────────────────────────────────────────

COMPONENT_HINTS = {
    "entry_logic": ["entry", "enter", "buy when", "sell when", "go long", "go short",
                     "signal", "trigger", "breakout", "crossover"],
    "exit_logic": ["exit", "stop loss", "take profit", "trailing stop", "time stop",
                    "close position", "profit target", "exit after"],
    "filter": ["filter", "only when", "only during", "regime", "condition",
               "threshold", "above percentile", "below percentile", "gate"],
    "sizing_overlay": ["position size", "sizing", "vol target", "risk parity",
                        "kelly", "leverage", "notional", "weight"],
    "session_effect": ["session", "overnight", "morning", "afternoon", "close",
                        "london", "tokyo", "new york", "pre-market", "after hours"],
    "asset_behavior": ["term structure", "contango", "backwardation", "roll yield",
                        "carry", "convenience yield", "basis", "spread"],
    "regime_logic": ["regime", "vol regime", "trending", "ranging", "high vol",
                      "low vol", "crisis", "expansion", "contraction"],
}


def score_lead(text, title=""):
    """Score a lead by mechanism density.

    Returns a dict with:
        mechanism_score: int (0-20+, higher = more mechanical)
        noise_score: int (0-10+, higher = more noise)
        net_score: int (mechanism - noise)
        strong_hits: list of matched strong indicators
        component_hints: list of likely component types
    """
    full_text = f"{title} {text}".lower()

    # Count mechanism indicators
    strong_hits = [kw for kw in STRONG_MECHANISM if kw in full_text]
    moderate_hits = [kw for kw in MODERATE_MECHANISM if kw in full_text]
    noise_hits = [kw for kw in NOISE_INDICATORS if kw in full_text]

    mechanism_score = len(strong_hits) * 2 + len(moderate_hits)
    noise_score = len(noise_hits) * 2

    # Detect likely components
    components = detect_components(full_text)

    return {
        "mechanism_score": mechanism_score,
        "noise_score": noise_score,
        "net_score": mechanism_score - noise_score,
        "strong_hits": strong_hits[:5],  # Cap for readability
        "moderate_hits": len(moderate_hits),
        "noise_hits": noise_hits[:3],
        "component_hints": components,
    }


def detect_components(text):
    """Detect likely component types in text.

    Returns list of component type strings that appear to be present.
    """
    text = text.lower()
    found = []
    for comp_type, keywords in COMPONENT_HINTS.items():
        matches = sum(1 for kw in keywords if kw in text)
        if matches >= 2:  # Need at least 2 keyword hits to suggest a component
            found.append(comp_type)
    return found


def tier_lead(score_result):
    """Classify a lead into quality tiers.

    Returns one of:
        "A" — high-confidence mechanical content
        "B" — useful fragment or partial mechanism
        "C" — weak but potentially salvageable
        "R" — reject (obvious junk only)

    DOCTRINE: R is only for truly obvious trash — noise dominates AND
    no mechanism detected. If ANY testable mechanism or component is
    present, the lead survives at C or better. We optimize for low
    false negatives, not low volume.
    """
    net = score_result["net_score"]
    mechanism = score_result["mechanism_score"]
    noise = score_result["noise_score"]
    components = score_result["component_hints"]

    # A lead with any detected component always survives
    if len(components) >= 1:
        if mechanism >= 6:
            return "A"
        return "B"

    # High mechanism density = A
    if mechanism >= 6:
        return "A"

    # Moderate mechanism = B
    if mechanism >= 3:
        return "B"

    # Low mechanism but present = C (salvageable)
    if mechanism >= 1:
        return "C"

    # Only reject when noise truly dominates with zero mechanism
    if noise >= 4 and mechanism == 0:
        return "R"

    # Default: C (keep in the net, let Claw decide)
    return "C"


def format_score_line(score_result, tier):
    """Format a compact score summary for lead output."""
    components = ", ".join(score_result["component_hints"]) if score_result["component_hints"] else "none detected"
    return f"tier={tier}, mechanism={score_result['mechanism_score']}, noise={score_result['noise_score']}, components=[{components}]"
