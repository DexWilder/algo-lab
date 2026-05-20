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
        get_cost_params(symbol="MCL")  # MCL was one of the 11 silently-defaulted
    assert "MCL" in str(exc_info.value)
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
        get_cost_params(symbol="MCL", commission_per_side=2.00)
    # commission resolved, but slippage_ticks and tick_size still missing
    msg = str(exc_info.value)
    assert "slippage_ticks" in msg
    assert "tick_size" in msg
    assert "commission_per_side" not in msg


# ── get_cost_params: exploration-tier opt-in ──────────────────────────────────

def test_allow_uncosted_returns_exploration_tier_for_unknown_symbol():
    """Explicit opt-in: missing config falls back to zero, tagged for downstream refusal."""
    costs = get_cost_params(symbol="MCL", allow_uncosted=True)
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
        run_backtest(df, signals, symbol="MCL")


def test_run_backtest_succeeds_with_known_symbol(minimal_data):
    """Sanity: known asset still runs cleanly and tags VALIDATED."""
    df, signals = minimal_data
    result = run_backtest(df, signals, symbol="MES")
    assert result["stats"]["costs"]["cost_tier"] == "VALIDATED"
    assert result["stats"]["costs"]["symbol"] == "MES"


def test_run_backtest_allow_uncosted_tags_exploration(minimal_data):
    """Exploration opt-in: result is tagged so downstream consumers can refuse."""
    df, signals = minimal_data
    result = run_backtest(df, signals, symbol="MCL", allow_uncosted=True)
    assert result["stats"]["costs"]["cost_tier"] == "EXPLORATION_TIER"


# ── Coverage assertion: the asset-config / cost-defaults gap ──────────────────

def test_cost_defaults_documented_coverage():
    """Document which assets ARE configured. After Piece A this should equal 17.

    This test does not assert a count — it surfaces the current count so any
    accidental regression (removing an asset) is immediately visible.
    """
    configured = sorted(SYMBOL_DEFAULTS.keys())
    # Pre-Piece-A state captured here; update intentionally as Piece A lands.
    assert len(configured) >= 6, "Should never have fewer than the original 6 configured assets"
    for required_base in ("MES", "MNQ", "MGC"):
        assert required_base in configured, f"{required_base} must remain configured"
