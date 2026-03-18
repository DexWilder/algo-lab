"""FQL Carry Lookup Table v1 — Carry signal by asset, honest about quality.

Provides a unified carry score per asset for use by carry strategies,
carry-bias filters, and cross-asset ranking functions.

Signal quality labels (MUST be respected by consumers):
  REAL        — derived from published fundamental data (FX rate differentials)
  APPROXIMATE — derived from price via formula (treasury yield/rolldown)
  PROXY       — trailing return that conflates carry with momentum (commodities)
  NOT_AVAILABLE — no carry signal for this asset class yet (equities)

Usage:
    from engine.carry_lookup import get_carry_score, rank_carry, get_carry_table

    # Single asset
    score, quality = get_carry_score("6J")

    # Cross-asset ranking
    ranked = rank_carry(["6J", "6E", "ZN", "ZB", "MCL", "MGC"],
                        price_data={"ZN": zn_prices, "MCL": mcl_prices, ...})

    # Full table
    table = get_carry_table(price_data=price_dict)
"""

import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RATES_PATH = Path(__file__).resolve().parent / "carry_rates.json"

# ── Load Static Rates ────────────────────────────────────────────────────────

def _load_rates():
    """Load the static carry rates JSON."""
    with open(RATES_PATH) as f:
        return json.load(f)


# ── FX Carry (REAL) ─────────────────────────────────────────────────────────

def _fx_carry_score(asset: str, rates: dict) -> tuple:
    """Compute FX carry score from interest rate differential.

    Returns (score, quality_label).
    Score is annualized carry in decimal (e.g., 0.046 = 4.6%/year).
    Positive score = positive carry for holding long the foreign currency.

    CME FX futures convention:
      6J = JPY per USD (inverted). Long 6J = long JPY = SHORT USD.
      Carry for long 6J = JPY rate - USD rate (you earn JPY, pay USD).
      So carry_for_long = foreign_rate - domestic_rate.
    """
    fx_pairs = rates.get("fx_pairs", {})
    policy = rates.get("policy_rates", {})

    if asset not in fx_pairs:
        return None, "NOT_AVAILABLE"

    pair = fx_pairs[asset]
    dom_rate = policy.get(pair["domestic"], {}).get("rate")
    for_rate = policy.get(pair["foreign"], {}).get("rate")

    if dom_rate is None or for_rate is None:
        return None, "NOT_AVAILABLE"

    # Carry for going long the CME contract (long foreign currency)
    carry = for_rate - dom_rate
    return carry, "REAL"


# ── Rates Carry (APPROXIMATE) ───────────────────────────────────────────────

def _rates_carry_score(asset: str, price_series: pd.Series,
                       rates: dict) -> tuple:
    """Estimate directional carry score for treasury futures.

    We cannot accurately derive absolute yield from continuous contract
    prices (the 6% notional coupon is a CME delivery standard, not market
    yield, and Panama-canal roll adjustments distort the price level).

    Instead, we compute a RELATIVE carry score using two components:

    1. Rolldown proxy: steeper curve = more rolldown carry. Approximated
       by the difference in trailing returns across tenors (ZB vs ZN vs ZF).
       The longest duration benefits most from curve steepness.

    2. Slope direction: 60-day trailing return of the price series.
       This captures whether the bond is rallying (positive carry
       environment — rates falling) or selling off (negative carry —
       rates rising).

    This is NOT absolute yield. It's a directional signal for ranking
    tenors relative to each other and for determining whether rate carry
    is currently positive or negative.

    Returns (score, quality_label).
    Score is a normalized directional carry indicator.
    """
    params = rates.get("treasury_params", {})

    if asset not in params:
        return None, "NOT_AVAILABLE"

    if price_series is None or len(price_series) < 61:
        return None, "NOT_AVAILABLE"

    p = params[asset]
    maturity = p["approx_maturity_years"]

    # 60-day trailing return as directional carry indicator
    current = float(price_series.iloc[-1])
    past_60 = float(price_series.iloc[-61])

    if past_60 == 0 or np.isnan(past_60) or np.isnan(current):
        return None, "NOT_AVAILABLE"

    trailing_return = (current - past_60) / past_60

    # Duration-weight: longer duration = more carry sensitivity
    # Normalize by maturity so ZB (30y) gets ~3x the weight of ZN (10y)
    duration_factor = maturity / 10.0

    # Carry score = trailing return × duration factor
    # Positive = bonds rallying (rates falling, carry positive)
    # Negative = bonds selling off (rates rising, carry negative)
    carry = trailing_return * duration_factor

    return carry, "APPROXIMATE"


# ── Commodity Carry (PROXY) ──────────────────────────────────────────────────

def _commodity_carry_proxy(asset: str, price_series: pd.Series,
                           lookback: int = 60) -> tuple:
    """Compute 60-day trailing return as carry proxy.

    This is NOT real carry. It conflates carry with momentum.
    Retained for cross-asset ranking compatibility until v2 provides
    front/back contract spreads.

    Returns (score, quality_label).
    Score is the trailing return over lookback days (decimal).
    """
    if price_series is None or len(price_series) < lookback + 1:
        return None, "NOT_AVAILABLE"

    current = float(price_series.iloc[-1])
    past = float(price_series.iloc[-(lookback + 1)])

    if past == 0 or np.isnan(past) or np.isnan(current):
        return None, "NOT_AVAILABLE"

    trailing_return = (current - past) / past
    return trailing_return, "PROXY"


# ── Asset Class Router ───────────────────────────────────────────────────────

# Map assets to their carry computation method
_ASSET_CLASS = {
    "6J": "fx", "6E": "fx", "6B": "fx",
    "ZN": "rate", "ZF": "rate", "ZB": "rate",
    "MCL": "commodity", "MGC": "commodity",
    "MES": "equity", "MNQ": "equity", "M2K": "equity",
}


# ── Public API ───────────────────────────────────────────────────────────────

def get_carry_score(asset: str, price_series: pd.Series = None) -> tuple:
    """Return the carry score and quality label for a single asset.

    Args:
        asset: Symbol (e.g., "6J", "ZN", "MCL")
        price_series: Daily close prices (pd.Series). Required for rates
                      and commodities. Not needed for FX.

    Returns:
        (score, quality): score is float (annualized carry, decimal),
                          quality is one of REAL, APPROXIMATE, PROXY,
                          NOT_AVAILABLE.
    """
    rates = _load_rates()
    asset_class = _ASSET_CLASS.get(asset)

    if asset_class == "fx":
        return _fx_carry_score(asset, rates)
    elif asset_class == "rate":
        return _rates_carry_score(asset, price_series, rates)
    elif asset_class == "commodity":
        return _commodity_carry_proxy(asset, price_series)
    else:
        return None, "NOT_AVAILABLE"


def rank_carry(assets: list, price_data: dict = None) -> list:
    """Rank assets by carry score, highest to lowest.

    Args:
        assets: List of asset symbols to rank.
        price_data: Dict of {asset: pd.Series} for assets that need
                    price data (rates, commodities). FX assets don't
                    need price data.

    Returns:
        List of (asset, score, quality) tuples sorted by score descending.
        Assets with NOT_AVAILABLE are excluded from ranking.
    """
    if price_data is None:
        price_data = {}

    results = []
    for asset in assets:
        prices = price_data.get(asset)
        score, quality = get_carry_score(asset, prices)
        if score is not None:
            results.append((asset, score, quality))

    return sorted(results, key=lambda x: x[1], reverse=True)


def get_carry_table(assets: list = None, price_data: dict = None) -> dict:
    """Return full carry lookup table for all supported assets.

    Args:
        assets: List of symbols. Defaults to all known assets.
        price_data: Dict of {asset: pd.Series}.

    Returns:
        Dict of {asset: {"score": float, "quality": str, "direction": str}}
        direction is "carry_positive", "carry_negative", or "neutral".
    """
    if assets is None:
        assets = list(_ASSET_CLASS.keys())
    if price_data is None:
        price_data = {}

    table = {}
    for asset in assets:
        prices = price_data.get(asset)
        score, quality = get_carry_score(asset, prices)

        if score is None:
            direction = "not_available"
        elif score > 0.005:
            direction = "carry_positive"
        elif score < -0.005:
            direction = "carry_negative"
        else:
            direction = "neutral"

        table[asset] = {
            "score": score,
            "quality": quality,
            "direction": direction,
        }

    return table


def check_staleness() -> dict:
    """Check if the carry rates file is stale (>100 days old).

    Returns dict with staleness info and warnings.
    """
    rates = _load_rates()
    updated = rates.get("_updated", "unknown")
    warnings = []

    if updated != "unknown":
        try:
            updated_date = datetime.strptime(updated, "%Y-%m-%d")
            days_old = (datetime.now() - updated_date).days
            if days_old > 100:
                warnings.append(
                    f"Carry rates are {days_old} days old (updated {updated}). "
                    f"Check for central bank rate changes."
                )
        except ValueError:
            warnings.append(f"Cannot parse rates update date: {updated}")

    # Check individual policy rates
    for ccy, info in rates.get("policy_rates", {}).items():
        as_of = info.get("as_of", "unknown")
        if as_of != "unknown":
            try:
                as_of_date = datetime.strptime(as_of, "%Y-%m-%d")
                days = (datetime.now() - as_of_date).days
                if days > 100:
                    warnings.append(f"{ccy} rate is {days} days old (as_of {as_of})")
            except ValueError:
                pass

    return {
        "last_updated": updated,
        "warnings": warnings,
        "stale": len(warnings) > 0,
    }
