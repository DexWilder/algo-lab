"""Tests for fail-closed cost parameter resolution.

Per feedback_evidence_integrity_failsafe.md: any missing assumption that can
change a trading decision must fail closed. Cost defaults were silently
returning zero for 11 of 17 assets — these tests prove the new fail-closed
path catches that class of bug.
"""

import pandas as pd
import pytest

from engine.backtest import (
    InvalidCostAssumption,
    SYMBOL_DEFAULTS,
    get_cost_params,
    run_backtest,
)


# ── get_cost_params: fail-closed path ─────────────────────────────────────────

def test_raises_when_symbol_unknown_and_no_overrides():
    """Asset with no SYMBOL_DEFAULTS entry must raise — the original bug class."""
    with pytest.raises(InvalidCostAssumption) as exc_info:
        get_cost_params(symbol="NOT_A_REAL_ASSET")
    assert "NOT_A_REAL_ASSET" in str(exc_info.value)
    assert "commission_per_side" in str(exc_info.value)


def test_raises_when_no_symbol_and_no_overrides():
    """No symbol + no explicit overrides = nothing to resolve from. Fail closed."""
    with pytest.raises(InvalidCostAssumption):
        get_cost_params()


def test_raises_lists_all_missing_fields():
    """Error message identifies which specific fields are unresolved."""
    with pytest.raises(InvalidCostAssumption) as exc_info:
        get_cost_params(symbol="UNKNOWN_ASSET")
    msg = str(exc_info.value)
    assert "commission_per_side" in msg
    assert "slippage_ticks" in msg
    assert "tick_size" in msg


# ── get_cost_params: happy path ───────────────────────────────────────────────

def test_known_symbol_resolves_cleanly():
    """Configured asset returns VALIDATED tier with no raise."""
    costs = get_cost_params(symbol="MES")
    assert costs["cost_tier"] == "VALIDATED"
    assert costs["commission_per_side"] == 0.62
    assert costs["slippage_ticks"] == 1
    assert costs["tick_size"] == 0.25


def test_full_explicit_overrides_resolve_without_symbol():
    """All three params explicit = no symbol lookup needed, no raise."""
    costs = get_cost_params(
        commission_per_side=1.50, slippage_ticks=2, tick_size=0.01,
    )
    assert costs["cost_tier"] == "VALIDATED"
    assert costs["commission_per_side"] == 1.50
    assert costs["slippage_ticks"] == 2
    assert costs["tick_size"] == 0.01


def test_partial_override_with_known_symbol():
    """Override commission, take slippage+tick from known symbol defaults."""
    costs = get_cost_params(symbol="MES", commission_per_side=2.00)
    assert costs["cost_tier"] == "VALIDATED"
    assert costs["commission_per_side"] == 2.00
    assert costs["slippage_ticks"] == 1  # from MES default
    assert costs["tick_size"] == 0.25    # from MES default


def test_partial_override_with_unknown_symbol_still_raises():
    """Partial override + unknown symbol = still missing some fields. Raise."""
    with pytest.raises(InvalidCostAssumption) as exc_info:
        get_cost_params(symbol="NOT_A_REAL_ASSET", commission_per_side=2.00)
    # commission resolved, but slippage_ticks and tick_size still missing
    msg = str(exc_info.value)
    assert "slippage_ticks" in msg
    assert "tick_size" in msg
    assert "commission_per_side" not in msg


# ── get_cost_params: exploration-tier opt-in ──────────────────────────────────

def test_allow_uncosted_returns_exploration_tier_for_unknown_symbol():
    """Explicit opt-in: missing config falls back to zero, tagged for downstream refusal."""
    costs = get_cost_params(symbol="NOT_A_REAL_ASSET", allow_uncosted=True)
    assert costs["cost_tier"] == "EXPLORATION_TIER"
    assert costs["commission_per_side"] == 0.0
    assert costs["slippage_ticks"] == 0
    assert costs["tick_size"] == 0.25


def test_allow_uncosted_with_no_symbol():
    """No symbol + allow_uncosted = exploration-tier zero-cost run."""
    costs = get_cost_params(allow_uncosted=True)
    assert costs["cost_tier"] == "EXPLORATION_TIER"


def test_allow_uncosted_does_not_downgrade_known_symbol():
    """Known symbol still resolves as VALIDATED even if allow_uncosted=True."""
    costs = get_cost_params(symbol="MES", allow_uncosted=True)
    assert costs["cost_tier"] == "VALIDATED"


# ── run_backtest: integration with fail-closed path ───────────────────────────

@pytest.fixture
def minimal_data():
    """Two-bar dataset just sufficient to call run_backtest."""
    df = pd.DataFrame({
        "datetime": pd.to_datetime(["2026-01-01 09:30", "2026-01-01 09:35"]),
        "open":  [100.0, 100.5],
        "high":  [100.5, 101.0],
        "low":   [99.5,  100.0],
        "close": [100.5, 100.5],
    })
    signals = pd.DataFrame({"signal": [0, 0], "exit_signal": [0, 0]})
    return df, signals


def test_run_backtest_raises_for_unknown_symbol(minimal_data):
    """The integration point: unknown-asset backtests must fail loudly."""
    df, signals = minimal_data
    with pytest.raises(InvalidCostAssumption):
        run_backtest(df, signals, symbol="NOT_A_REAL_ASSET")


def test_run_backtest_succeeds_with_known_symbol(minimal_data):
    """Sanity: known asset still runs cleanly and tags VALIDATED."""
    df, signals = minimal_data
    result = run_backtest(df, signals, symbol="MES")
    assert result["stats"]["costs"]["cost_tier"] == "VALIDATED"
    assert result["stats"]["costs"]["symbol"] == "MES"


def test_run_backtest_allow_uncosted_tags_exploration(minimal_data):
    """Exploration opt-in: result is tagged so downstream consumers can refuse."""
    df, signals = minimal_data
    result = run_backtest(df, signals, symbol="NOT_A_REAL_ASSET", allow_uncosted=True)
    assert result["stats"]["costs"]["cost_tier"] == "EXPLORATION_TIER"


# ── Coverage assertion: the asset-config / cost-defaults gap ──────────────────

def test_every_trading_universe_asset_has_cost_defaults():
    """Standing test: the failure mode of 2026-05-19 cannot silently recur.

    Every asset declared in engine/asset_config.py::ASSETS (the trading
    universe) must have a SYMBOL_DEFAULTS entry. If a new asset is added
    to the universe without cost defaults, this test fails immediately —
    preventing another instance of the silent zero-cost bug.
    """
    from engine.asset_config import ASSETS
    universe = set(ASSETS.keys())
    configured = set(SYMBOL_DEFAULTS.keys())
    missing = universe - configured
    assert not missing, (
        f"Trading-universe assets without cost defaults: {sorted(missing)}. "
        f"Add to SYMBOL_DEFAULTS in engine/backtest.py with documented "
        f"conservative assumptions, or remove from asset_config if not actively traded."
    )


def test_cost_defaults_resolve_validated_tier_for_universe():
    """Every universe asset must resolve as VALIDATED (not EXPLORATION_TIER)."""
    from engine.asset_config import ASSETS
    for sym in ASSETS:
        costs = get_cost_params(symbol=sym)
        assert costs["cost_tier"] == "VALIDATED", (
            f"{sym} resolves but at non-VALIDATED tier — check SYMBOL_DEFAULTS entry"
        )


def test_cost_defaults_match_asset_config_for_all_fields():
    """All three cost fields in SYMBOL_DEFAULTS must match asset_config exactly.

    asset_config.py is the single source of truth for execution-cost
    assumptions (Piece I 2026-05-20). SYMBOL_DEFAULTS derives from it; this
    test prevents anyone from reintroducing a manual cost table that drifts
    silently — the failure mode that overstated Forge/correlation/forward-paper
    PFs prior to the consolidation.
    """
    from engine.asset_config import ASSETS
    for sym, asset_cfg in ASSETS.items():
        assert sym in SYMBOL_DEFAULTS, f"{sym} missing from SYMBOL_DEFAULTS"
        bt = SYMBOL_DEFAULTS[sym]
        for field in ("commission_per_side", "slippage_ticks", "tick_size"):
            assert bt[field] == asset_cfg[field], (
                f"{sym} {field} mismatch: backtest={bt[field]}, "
                f"asset_config={asset_cfg[field]} — SYMBOL_DEFAULTS must derive "
                f"from asset_config (no separate manual table)."
            )
