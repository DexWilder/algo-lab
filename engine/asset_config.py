"""Canonical Asset Configuration — single source of truth for all asset metadata.

Replaces the ASSET_CONFIG dicts scattered across 5+ files. All modules should
import from here instead of maintaining their own copies.

Usage:
    from engine.asset_config import ASSETS, get_asset, get_asset_family

    mes = get_asset("MES")
    # mes["point_value"] == 5.0, mes["tick_size"] == 0.25, etc.
"""

# ── Asset Definitions ────────────────────────────────────────────────────────
# Every tradeable asset with its execution parameters and metadata.
#
# Fields:
#   point_value:        Dollar value per minimum price increment
#   tick_size:          Minimum price increment
#   commission_per_side: Commission per contract per side
#   slippage_ticks:     Expected slippage in ticks
#   name:               Human-readable name
#   asset_class:        equity_index, metal, energy, rate, fx, agriculture
#   databento_symbol:   Continuous contract symbol for Databento feed
#   exchange:           Exchange abbreviation
#   session:            Primary trading session hours (ET)
#   status:             active (data flowing, strategies possible),
#                       available (data exists, no active strategies),
#                       planned (data not yet onboarded)

ASSETS = {
    # ── Equity Index Micros ──────────────────────────────────────────────
    "MES": {
        "name": "Micro E-mini S&P 500",
        "asset_class": "equity_index",
        "point_value": 5.0,
        "tick_size": 0.25,
        "commission_per_side": 0.62,
        "slippage_ticks": 1,
        "databento_symbol": "MES.c.0",
        "exchange": "CME",
        "session": ("09:30", "16:00"),
        "status": "active",
    },
    "MNQ": {
        "name": "Micro E-mini Nasdaq-100",
        "asset_class": "equity_index",
        "point_value": 2.0,
        "tick_size": 0.25,
        "commission_per_side": 0.62,
        "slippage_ticks": 1,
        "databento_symbol": "MNQ.c.0",
        "exchange": "CME",
        "session": ("09:30", "16:00"),
        "status": "active",
    },
    "M2K": {
        "name": "Micro E-mini Russell 2000",
        "asset_class": "equity_index",
        "point_value": 5.0,
        "tick_size": 0.10,
        "commission_per_side": 0.62,
        "slippage_ticks": 1,
        "databento_symbol": "M2K.c.0",
        "exchange": "CME",
        "session": ("09:30", "16:00"),
        "status": "available",
    },
    "MYM": {
        "name": "Micro E-mini Dow Jones",
        "asset_class": "equity_index",
        "point_value": 0.50,
        "tick_size": 1.0,
        "commission_per_side": 0.62,
        "slippage_ticks": 1,
        "databento_symbol": "MYM.c.0",
        "exchange": "CBOT",
        "session": ("09:30", "16:00"),
        "status": "available",
    },

    # ── Metals ───────────────────────────────────────────────────────────
    "MGC": {
        "name": "Micro Gold",
        "asset_class": "metal",
        "point_value": 10.0,
        "tick_size": 0.10,
        "commission_per_side": 0.62,
        "slippage_ticks": 1,
        "databento_symbol": "MGC.c.0",
        "exchange": "COMEX",
        "session": ("08:30", "13:00"),
        "status": "active",
    },
    "SI": {
        "name": "Silver",
        "asset_class": "metal",
        "point_value": 5000.0,
        "tick_size": 0.005,
        "commission_per_side": 1.50,
        "slippage_ticks": 1,
        "databento_symbol": "SI.c.0",
        "exchange": "COMEX",
        "session": ("08:30", "13:00"),
        "status": "planned",
    },
    "HG": {
        "name": "Copper",
        "asset_class": "metal",
        "point_value": 25000.0,
        "tick_size": 0.0005,
        "commission_per_side": 1.50,
        "slippage_ticks": 1,
        "databento_symbol": "HG.c.0",
        "exchange": "COMEX",
        "session": ("08:30", "13:00"),
        "status": "planned",
    },

    # ── Energy ───────────────────────────────────────────────────────────
    "MCL": {
        "name": "Micro Crude Oil",
        "asset_class": "energy",
        "point_value": 100.0,
        "tick_size": 0.01,
        "commission_per_side": 0.62,
        "slippage_ticks": 1,
        "databento_symbol": "MCL.c.0",
        "exchange": "NYMEX",
        "session": ("09:00", "14:30"),
        "status": "available",
    },

    # ── Rates / Treasuries ───────────────────────────────────────────────
    "ZN": {
        "name": "10-Year Treasury Note",
        "asset_class": "rate",
        "point_value": 1000.0,
        "tick_size": 0.015625,
        "commission_per_side": 1.25,
        "slippage_ticks": 1,
        "databento_symbol": "ZN.c.0",
        "exchange": "CBOT",
        "session": ("08:20", "15:00"),
        "status": "available",
    },
    "ZF": {
        "name": "5-Year Treasury Note",
        "asset_class": "rate",
        "point_value": 1000.0,
        "tick_size": 0.0078125,
        "commission_per_side": 1.25,
        "slippage_ticks": 1,
        "databento_symbol": "ZF.c.0",
        "exchange": "CBOT",
        "session": ("08:20", "15:00"),
        "status": "planned",
    },
    "ZB": {
        "name": "30-Year Treasury Bond",
        "asset_class": "rate",
        "point_value": 1000.0,
        "tick_size": 0.03125,
        "commission_per_side": 1.25,
        "slippage_ticks": 1,
        "databento_symbol": "ZB.c.0",
        "exchange": "CBOT",
        "session": ("08:20", "15:00"),
        "status": "available",
    },

    # ── FX Futures ───────────────────────────────────────────────────────
    "6E": {
        "name": "Euro FX",
        "asset_class": "fx",
        "point_value": 125000.0,
        "tick_size": 0.00005,
        "commission_per_side": 1.25,
        "slippage_ticks": 1,
        "databento_symbol": "6E.c.0",
        "exchange": "CME",
        "session": ("08:30", "15:00"),
        "status": "planned",
    },
    "6J": {
        "name": "Japanese Yen",
        "asset_class": "fx",
        "point_value": 12500000.0,
        "tick_size": 0.0000005,
        "commission_per_side": 1.25,
        "slippage_ticks": 1,
        "databento_symbol": "6J.c.0",
        "exchange": "CME",
        "session": ("08:30", "15:00"),
        "status": "planned",
    },
    "6B": {
        "name": "British Pound",
        "asset_class": "fx",
        "point_value": 62500.0,
        "tick_size": 0.0001,
        "commission_per_side": 1.25,
        "slippage_ticks": 1,
        "databento_symbol": "6B.c.0",
        "exchange": "CME",
        "session": ("08:30", "15:00"),
        "status": "planned",
    },

    # ── Agriculture ──────────────────────────────────────────────────────
    "ZC": {
        "name": "Corn",
        "asset_class": "agriculture",
        "point_value": 50.0,
        "tick_size": 0.25,
        "commission_per_side": 1.50,
        "slippage_ticks": 1,
        "databento_symbol": "ZC.c.0",
        "exchange": "CBOT",
        "session": ("09:30", "14:20"),
        "status": "planned",
    },
    "ZS": {
        "name": "Soybeans",
        "asset_class": "agriculture",
        "point_value": 50.0,
        "tick_size": 0.25,
        "commission_per_side": 1.50,
        "slippage_ticks": 1,
        "databento_symbol": "ZS.c.0",
        "exchange": "CBOT",
        "session": ("09:30", "14:20"),
        "status": "planned",
    },
    "ZW": {
        "name": "Wheat",
        "asset_class": "agriculture",
        "point_value": 50.0,
        "tick_size": 0.25,
        "commission_per_side": 1.50,
        "slippage_ticks": 1,
        "databento_symbol": "ZW.c.0",
        "exchange": "CBOT",
        "session": ("09:30", "14:20"),
        "status": "planned",
    },
}

# ── Asset Families (for robustness testing) ──────────────────────────────────
# Each asset maps to related assets for cross-asset validation.
ASSET_FAMILIES = {
    "MES": ["MNQ", "M2K"],
    "MNQ": ["MES", "M2K"],
    "M2K": ["MES", "MNQ"],
    "MGC": ["SI", "HG"],
    "MCL": ["HG", "MGC"],
    "ZN": ["ZF", "ZB"],
    "ZF": ["ZN", "ZB"],
    "ZB": ["ZN", "ZF"],
    "6E": ["6B", "6J"],
    "6J": ["6E", "6B"],
    "6B": ["6E", "6J"],
    "ZC": ["ZS", "ZW"],
    "ZS": ["ZC", "ZW"],
    "ZW": ["ZC", "ZS"],
    "SI": ["MGC", "HG"],
    "HG": ["SI", "MGC"],
}


# ── Helper Functions ─────────────────────────────────────────────────────────

def get_asset(symbol: str) -> dict:
    """Get asset config by symbol. Raises KeyError if not found."""
    if symbol not in ASSETS:
        raise KeyError(f"Unknown asset: {symbol}. Available: {list(ASSETS.keys())}")
    return ASSETS[symbol]


def get_asset_family(symbol: str) -> list:
    """Get related assets for cross-asset robustness testing."""
    return ASSET_FAMILIES.get(symbol, [])


def get_assets_by_class(asset_class: str) -> dict:
    """Get all assets in a given class."""
    return {k: v for k, v in ASSETS.items() if v["asset_class"] == asset_class}


def get_assets_by_status(status: str) -> dict:
    """Get all assets with a given status (active/available/planned)."""
    return {k: v for k, v in ASSETS.items() if v["status"] == status}


def get_active_assets() -> dict:
    """Get assets with active trading strategies."""
    return get_assets_by_status("active")


def get_onboardable_assets() -> dict:
    """Get assets that have data but no active strategies (available + planned)."""
    return {k: v for k, v in ASSETS.items() if v["status"] in ("available", "planned")}


def get_databento_symbols() -> dict:
    """Get Databento continuous contract symbols for all assets."""
    return {k: v["databento_symbol"] for k, v in ASSETS.items()}


def get_execution_params(symbol: str) -> dict:
    """Get execution parameters for backtesting/trading.

    Returns dict compatible with existing ASSET_CONFIG usage:
        point_value, tick_size, commission_per_side, slippage_ticks
    """
    asset = get_asset(symbol)
    return {
        "point_value": asset["point_value"],
        "tick_size": asset["tick_size"],
        "commission_per_side": asset["commission_per_side"],
        "slippage_ticks": asset["slippage_ticks"],
    }


def build_legacy_asset_config(symbols: list = None) -> dict:
    """Build an ASSET_CONFIG dict matching the legacy format.

    For backward compatibility with modules that haven't migrated yet.
    """
    if symbols is None:
        symbols = list(ASSETS.keys())
    return {
        sym: get_execution_params(sym)
        for sym in symbols
        if sym in ASSETS
    }
