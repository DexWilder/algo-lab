#!/usr/bin/env python3
"""FQL Live Drift Monitor — Detect divergence between expected and forward behavior.

Compares rolling forward-test metrics against backtest reference baselines
to detect edge drift before major damage occurs.

Drift Dimensions:
    1. Win Rate Drift         — entry edge weakening
    2. Expectancy Drift       — payoff distribution changing
    3. Trade Frequency Drift  — regime shift or signal degradation
    4. Sharpe Drift           — overall edge quality
    5. Regime-Specific Drift  — environment-dependent performance change
    6. Session Drift          — intraday structural changes

Alert Tiers:
    NORMAL   — within 1σ of baseline
    DRIFT    — >1σ deviation sustained 2+ weeks
    ALARM    — >2σ deviation or structural break

Usage:
    python3 research/live_drift_monitor.py                # Full drift report
    python3 research/live_drift_monitor.py --json         # JSON output
    python3 research/live_drift_monitor.py --save         # Save to reports/
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ── Paths ────────────────────────────────────────────────────────────────────
#
# 2026-04-14 REPOINT: the previous paths under research/phase17_paper_trading
# went stale on 2026-03-06 when production forward trading moved to the
# current runner. The monitor ran for ~39 days emitting identical NORMAL
# verdicts because its inputs were frozen. Live sources are now:
#   trade_log       -> logs/trade_log.csv        (written by run_forward_paper)
#   daily_report    -> logs/daily_report.csv     (equity + regime + pnl)
# See also STRATEGY_PROMOTED_DATES below for the replay-contamination filter.

TRADE_LOG_PATH = ROOT / "logs" / "trade_log.csv"
DAILY_REPORT_PATH = ROOT / "logs" / "daily_report.csv"
DRIFT_LOG_PATH = ROOT / "research" / "data" / "live_drift_log.json"
REPORTS_DIR = ROOT / "research" / "reports"

# ── Required CSV columns (fail loudly if missing) ────────────────────────────

REQUIRED_TRADE_COLS = {"strategy", "entry_time", "pnl"}
REQUIRED_DAILY_COLS = {"date", "equity", "daily_pnl", "rv_regime",
                       "trades_raw", "trades_controlled"}

# ── Promotion dates for probation strategies ─────────────────────────────────
# Used to filter replayed/backfilled trades from forward evidence. A trade
# whose entry_time predates its strategy's promoted_date is a historical
# replay, not forward evidence, and must not count. Keep in sync with
# docs/XB_ORB_PROBATION_FRAMEWORK.md and the CLAUDE.md Probation Portfolio.

STRATEGY_PROMOTED_DATES = {
    "XB-ORB-EMA-Ladder-MNQ": "2026-04-06",
    "XB-ORB-EMA-Ladder-MCL": "2026-04-08",
    "XB-ORB-EMA-Ladder-MYM": "2026-04-13",
}

# ── Backtest Reference Baselines ─────────────────────────────────────────────
#
# 2026-04-14 refresh. Replaces the Phase 17 6-strategy baseline with the
# current live/probation universe. Tier conventions:
#   full            >= 300 backtest trades, trade-shaped. ALARM permitted.
#   reference-only  50-299 BT trades, or smaller/sparse but still trade-shaped.
#                   Severity capped at DRIFT (never ALARM).
#   observational   < 50 BT trades, or sparse event/carry, or non-trade-shaped.
#                   Metrics recorded, NO severity classification.
#
# Portfolio-level baseline is RETAINED BUT ANNOTATED STALE. Portfolio status
# is force-capped at DRIFT until a deliberate portfolio-construction exercise
# rebuilds `portfolio` with the current 3 core + 7 probation composition.
# See compute_portfolio_drift.
#
# Strategies explicitly excluded from per-trade drift (different shape):
#   VolManaged-EquityIndex-Futures — daily always-long sizing regime, needs a
#   weight-replication metric rather than per-trade WR/PF. FOLLOW-UP required.

BASELINE = {
    "_meta": {
        "strategy_baseline_refreshed": "2026-04-14",
        "portfolio_baseline_status": "STALE_PENDING_REFRESH",
        "portfolio_baseline_source": "Phase 17 6-strategy portfolio (2026-03-06)",
        "portfolio_status_cap": "DRIFT",
        "portfolio_refresh_note": (
            "Portfolio baseline reflects a 6-strategy Phase 17 composition no "
            "longer representative. Refresh requires a combined backtest over "
            "the current 3 core + 7 probation portfolio with agreed weights."
        ),
    },
    "portfolio": {
        "trades_per_day": 1.1,
        "win_rate": 0.499,
        "daily_win_rate": 0.526,
        "sharpe": 4.04,
        "avg_pnl_per_trade": 41.89,
        "profit_factor": 2.11,
        "avg_winner": 159.38,
        "avg_loser": -75.01,
        "max_dd": 2007,
        "trade_retention": 0.70,
        "monthly_positive_rate": 0.84,
    },
    "strategies": {
        # ── Full tier (>= 300 BT trades, ALARM permitted) ────────────────
        "XB-ORB-EMA-Ladder-MNQ": {
            "tier": "full", "asset": "MNQ",
            "trades": 1183, "backtest_days": 1700, "win_rate": 0.61,
            "avg_pnl": 42.93, "trade_share": None, "pnl_share": None,
            "entered_forward_date": "2026-04-06",
            "source": "research/data/xb_orb_family_sweep_results.json + docs/XB_ORB_PROBATION_FRAMEWORK.md",
        },
        "XB-ORB-EMA-Ladder-MCL": {
            "tier": "full", "asset": "MCL",
            "trades": 898, "backtest_days": 1175, "win_rate": 0.57,
            "avg_pnl": 7.06, "trade_share": None, "pnl_share": None,
            "entered_forward_date": "2026-04-08",
            "source": "research/data/xb_orb_mcl_stop_sweep_results.json + framework WR",
        },
        "XB-ORB-EMA-Ladder-MYM": {
            "tier": "full", "asset": "MYM",
            "trades": 340, "backtest_days": 500, "win_rate": 0.56,
            "avg_pnl": 30.0, "trade_share": None, "pnl_share": None,
            "entered_forward_date": "2026-04-13",
            "source": "docs/XB_ORB_PROBATION_FRAMEWORK.md (avg_pnl estimated from family)",
        },
        "ZN-Afternoon-Reversion": {
            "tier": "full", "asset": "ZN",
            "trades": 300, "backtest_days": 1500, "win_rate": None,
            "avg_pnl": None, "trade_share": None, "pnl_share": None,
            "entered_forward_date": "2026-03-20",
            "source": "docs/PROBATION_REVIEW_CRITERIA.md (PF 1.32; WR/avg not published)",
        },
        # ── Reference-only (50-299 BT trades, severity capped at DRIFT) ─
        "XB-PB-EMA-MES-Short": {
            "tier": "reference-only", "asset": "MES",
            "trades": 88, "backtest_days": 355, "win_rate": 0.557,
            "avg_pnl": 28.86, "trade_share": 0.225, "pnl_share": 0.155,
            "source": "Phase 17 baseline (registry PF 1.31, still core)",
        },
        "ORB-MGC-Long": {
            "tier": "reference-only", "asset": "MGC",
            "trades": 62, "backtest_days": 355, "win_rate": 0.565,
            "avg_pnl": 44.63, "trade_share": 0.159, "pnl_share": 0.169,
            "source": "Phase 17 baseline (registry PF 1.99, still core)",
        },
        # Treasury-Rolldown-Carry-Spread removed 2026-04-14: registry
        # shows status=archived as of 2026-03-20. Strategy is not in
        # the live/probation path. Historical entry preserved in
        # docs/PROBATION_REVIEW_CRITERIA.md §6 (struck).
        # FXBreak-6J-Short-London removed 2026-04-14: registry shows
        # status=rejected as of 2026-03-18. Historical entry preserved
        # in docs/PROBATION_REVIEW_CRITERIA.md §3 (struck).
        # ── Observational (<50 BT trades or sparse/event, no severity) ──
        "PB-MGC-Short": {
            "tier": "observational", "asset": "MGC",
            "trades": 9, "backtest_days": 355, "win_rate": 0.667,
            "avg_pnl": 86.76, "trade_share": 0.023, "pnl_share": 0.048,
            "source": "Phase 17 baseline (registry PF 2.36, still core but sparse)",
        },
        "DailyTrend-MGC-Long": {
            "tier": "observational", "asset": "MGC",
            "trades": 15, "backtest_days": 1000, "win_rate": None,
            "avg_pnl": None, "trade_share": None, "pnl_share": None,
            "source": "docs/PROBATION_REVIEW_CRITERIA.md (sparse daily, PF 3.65)",
        },
        "TV-NFP-High-Low-Levels": {
            "tier": "observational", "asset": "MNQ",
            "trades": None, "backtest_days": None, "win_rate": None,
            "avg_pnl": None, "trade_share": None, "pnl_share": None,
            "source": "docs/PROBATION_REVIEW_CRITERIA.md (sparse event, vitality-adjusted)",
        },
        # PreFOMC-Drift-Equity removed 2026-04-14: registry shows
        # status=rejected as of 2026-03-17. Historical reference in
        # docs/PROBATION_REVIEW_CRITERIA.md sparse-event note (struck).
        # MomPB-6J-Long-US removed 2026-04-14: registry shows
        # status=archived as of 2026-03-18. Historical entry preserved
        # in docs/PROBATION_REVIEW_CRITERIA.md §2 (struck).
    },
    # Strategies that should not participate in per-trade drift severity.
    # Recorded here so future engineers can see the exclusion is intentional.
    "excluded_from_strategy_drift": {
        "VolManaged-EquityIndex-Futures": {
            "reason": (
                "Daily always-long vol-scaled sizing regime. No per-trade WR/PF "
                "in the normal sense; the right drift metric compares live "
                "position weight to the weight the backtest would produce on "
                "the same realized-vol inputs. Requires a dedicated metric. "
                "FOLLOW-UP: design VolManaged weight-replication drift."
            ),
        },
    },
}

# ── Drift Thresholds ─────────────────────────────────────────────────────────

THRESHOLDS = {
    "win_rate": {
        "drift": 0.08,     # 8pp deviation = DRIFT
        "alarm": 0.15,     # 15pp = ALARM
    },
    "expectancy": {
        "drift": 0.40,     # 40% below baseline avg_pnl = DRIFT
        "alarm": 0.70,     # 70% below = ALARM
    },
    "trade_frequency": {
        "drift": 0.40,     # 40% fewer/more trades = DRIFT
        "alarm": 0.60,     # 60% = ALARM
    },
    "sharpe": {
        "drift": 1.5,      # Sharpe below 1.5 = DRIFT (baseline 4.04)
        "alarm": 0.5,      # Below 0.5 = ALARM
    },
    "profit_factor": {
        "drift": 1.3,      # PF below 1.3 = DRIFT
        "alarm": 1.0,      # PF below 1.0 = ALARM (losing money)
    },
}


# ── Data Loading ─────────────────────────────────────────────────────────────

def _require_columns(df: pd.DataFrame, required: set, source: str):
    """Fail loudly if a CSV is missing expected columns."""
    missing = required - set(df.columns)
    if missing:
        raise RuntimeError(
            f"Drift monitor input {source} is missing required columns: "
            f"{sorted(missing)}. Present: {sorted(df.columns)}. "
            f"Refusing to emit a status to avoid silent-NORMAL regressions."
        )


def _filter_replay_trades(df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows whose entry_time predates the strategy's promoted_date.

    Backfilled / replay rows are not forward evidence. Without this
    filter, e.g. XB-ORB-EMA-Ladder-MYM picks up 2026-03-09 / 2026-03-11
    replay rows logged on 2026-04-13 and crosses its 20-trade review
    gate artificially early.
    """
    if df.empty:
        return df
    keep = pd.Series(True, index=df.index)
    for strat, promoted in STRATEGY_PROMOTED_DATES.items():
        cutoff = pd.Timestamp(promoted)
        mask = (df["strategy"] == strat) & (df["entry_time"] < cutoff)
        keep &= ~mask
    return df[keep].copy()


def load_forward_trades() -> pd.DataFrame:
    """Load live forward trades from logs/trade_log.csv.

    Returns a DataFrame with `date` set to the trade's actual entry
    date (not the log-capture date), `entry_time` as a Timestamp, and
    replay rows filtered out via STRATEGY_PROMOTED_DATES.
    """
    if not TRADE_LOG_PATH.exists():
        return pd.DataFrame()

    df = pd.read_csv(TRADE_LOG_PATH)
    if df.empty:
        return df

    _require_columns(df, REQUIRED_TRADE_COLS, TRADE_LOG_PATH.name)

    df["entry_time"] = pd.to_datetime(df["entry_time"])
    df = _filter_replay_trades(df)
    # `date` downstream = the trade's entry date, not the log-capture date.
    df["date"] = df["entry_time"].dt.normalize()
    return df


def load_daily_states() -> list:
    """Synthesize per-day state dicts from logs/daily_report.csv.

    Maps the daily_report columns to the dict shape the regime and
    retention calculations expect:
        {
          "date": "YYYY-MM-DD",
          "regime": {"vol_regime": <rv_regime>},
          "portfolio_daily_pnl": <daily_pnl>,
          "signals_generated": <trades_raw>,
          "signals_taken":     <trades_controlled>,
        }
    """
    if not DAILY_REPORT_PATH.exists():
        return []

    df = pd.read_csv(DAILY_REPORT_PATH)
    if df.empty:
        return []

    _require_columns(df, REQUIRED_DAILY_COLS, DAILY_REPORT_PATH.name)

    states = []
    for _, row in df.iterrows():
        states.append({
            "date": str(row["date"]),
            "regime": {"vol_regime": row.get("rv_regime", "NORMAL")},
            "portfolio_daily_pnl": float(row.get("daily_pnl", 0) or 0),
            "signals_generated": int(row.get("trades_raw", 0) or 0),
            "signals_taken":     int(row.get("trades_controlled", 0) or 0),
        })
    return states


def load_equity_curve() -> pd.DataFrame:
    """Load live equity curve from logs/daily_report.csv.

    compute_portfolio_drift uses only the `date` and `daily_pnl`
    columns, so we return that projection.
    """
    if not DAILY_REPORT_PATH.exists():
        return pd.DataFrame()
    df = pd.read_csv(DAILY_REPORT_PATH)
    if df.empty:
        return df
    _require_columns(df, REQUIRED_DAILY_COLS, DAILY_REPORT_PATH.name)
    df = df[["date", "equity", "daily_pnl"]].copy()
    df["date"] = pd.to_datetime(df["date"])
    return df


# ── Drift Computation ────────────────────────────────────────────────────────

def compute_portfolio_drift(trades: pd.DataFrame, equity: pd.DataFrame,
                            daily_states: list) -> dict:
    """Compute portfolio-level drift metrics."""
    if trades.empty:
        return {"status": "NO_DATA", "message": "No forward trades available"}

    n_days = len(trades["date"].unique())
    n_trades = len(trades)

    # Win rate
    wins = trades[trades["pnl"] > 0]
    live_wr = len(wins) / n_trades if n_trades > 0 else 0
    wr_delta = live_wr - BASELINE["portfolio"]["win_rate"]

    # Trade frequency
    live_tpd = n_trades / max(n_days, 1)
    tpd_ratio = live_tpd / BASELINE["portfolio"]["trades_per_day"]

    # Expectancy
    live_avg_pnl = trades["pnl"].mean()
    exp_ratio = live_avg_pnl / BASELINE["portfolio"]["avg_pnl_per_trade"] if BASELINE["portfolio"]["avg_pnl_per_trade"] != 0 else 0

    # Profit factor
    gross_profit = trades[trades["pnl"] > 0]["pnl"].sum()
    gross_loss = abs(trades[trades["pnl"] <= 0]["pnl"].sum())
    live_pf = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    # Avg winner / loser
    live_avg_win = wins["pnl"].mean() if len(wins) > 0 else 0
    losses = trades[trades["pnl"] <= 0]
    live_avg_loss = losses["pnl"].mean() if len(losses) > 0 else 0

    # Sharpe (annualized from daily PnL)
    if not equity.empty and "daily_pnl" in equity.columns:
        daily_pnl = equity["daily_pnl"].dropna()
        if len(daily_pnl) > 1 and daily_pnl.std() > 0:
            live_sharpe = (daily_pnl.mean() / daily_pnl.std()) * np.sqrt(252)
        else:
            live_sharpe = 0.0
    else:
        live_sharpe = 0.0

    # Trade retention
    total_signals = sum(s.get("signals_generated", 0) for s in daily_states)
    total_taken = sum(s.get("signals_taken", 0) for s in daily_states)
    live_retention = total_taken / total_signals if total_signals > 0 else 0

    # Classify drift levels
    metrics = {
        "win_rate": {
            "baseline": BASELINE["portfolio"]["win_rate"],
            "live": round(live_wr, 3),
            "delta": round(wr_delta, 3),
            "severity": _classify_drift_abs(abs(wr_delta),
                                            THRESHOLDS["win_rate"]["drift"],
                                            THRESHOLDS["win_rate"]["alarm"]),
        },
        "trade_frequency": {
            "baseline_tpd": BASELINE["portfolio"]["trades_per_day"],
            "live_tpd": round(live_tpd, 2),
            "ratio": round(tpd_ratio, 2),
            "severity": _classify_drift_ratio(tpd_ratio,
                                              THRESHOLDS["trade_frequency"]["drift"],
                                              THRESHOLDS["trade_frequency"]["alarm"]),
        },
        "expectancy": {
            "baseline_avg_pnl": BASELINE["portfolio"]["avg_pnl_per_trade"],
            "live_avg_pnl": round(live_avg_pnl, 2),
            "ratio": round(exp_ratio, 2),
            "severity": _classify_drift_degradation(exp_ratio,
                                                    1 - THRESHOLDS["expectancy"]["drift"],
                                                    1 - THRESHOLDS["expectancy"]["alarm"]),
        },
        "profit_factor": {
            "baseline": BASELINE["portfolio"]["profit_factor"],
            "live": round(live_pf, 2),
            "severity": _classify_drift_floor(live_pf,
                                              THRESHOLDS["profit_factor"]["drift"],
                                              THRESHOLDS["profit_factor"]["alarm"]),
        },
        "sharpe": {
            "baseline": BASELINE["portfolio"]["sharpe"],
            "live": round(live_sharpe, 2),
            "severity": _classify_drift_floor(live_sharpe,
                                              THRESHOLDS["sharpe"]["drift"],
                                              THRESHOLDS["sharpe"]["alarm"]),
        },
        "avg_winner": {
            "baseline": BASELINE["portfolio"]["avg_winner"],
            "live": round(live_avg_win, 2),
        },
        "avg_loser": {
            "baseline": BASELINE["portfolio"]["avg_loser"],
            "live": round(live_avg_loss, 2),
        },
        "trade_retention": {
            "baseline": BASELINE["portfolio"]["trade_retention"],
            "live": round(live_retention, 2),
        },
    }

    # Overall severity
    severities = [m.get("severity", "NORMAL") for m in metrics.values() if "severity" in m]
    if "ALARM" in severities:
        overall = "ALARM"
    elif "DRIFT" in severities:
        overall = "DRIFT"
    else:
        overall = "NORMAL"

    # Portfolio baseline is stale (Phase 17 6-strategy composition). Cap
    # the overall portfolio verdict at DRIFT until BASELINE["portfolio"]
    # is refreshed against the current 3 core + 7 probation portfolio.
    cap = BASELINE.get("_meta", {}).get("portfolio_status_cap")
    if cap == "DRIFT" and overall == "ALARM":
        overall = "DRIFT"

    return {
        "status": overall,
        "forward_days": n_days,
        "forward_trades": n_trades,
        "metrics": metrics,
        "baseline_status": BASELINE.get("_meta", {}).get("portfolio_baseline_status"),
        "baseline_note": BASELINE.get("_meta", {}).get("portfolio_refresh_note"),
    }


def _apply_tier_clamp(severity: str, tier: str) -> str:
    """Clamp severity per tier rules.

    observational  -> OBSERVATIONAL (no severity classification)
    reference-only -> ALARM demoted to DRIFT
    full           -> unchanged
    """
    if tier == "observational":
        return "OBSERVATIONAL"
    if tier == "reference-only" and severity == "ALARM":
        return "DRIFT"
    return severity


# Minimum forward trades before any DRIFT/ALARM severity is emitted.
# Below this, the severity is INSUFFICIENT_DATA regardless of how
# extreme the point estimate looks — point estimates on n<20 are noise.
# Aligns with XB_ORB_PROBATION_FRAMEWORK.md's 20/30-trade gates.
MIN_TRADES_FOR_SEVERITY = {"full": 30, "reference-only": 20,
                           "observational": float("inf")}


def _missing_signals_severity(tier: str, baseline: dict, n_days: int) -> str:
    """For a strategy with 0 live trades, decide whether zero is drift.

    Compare expected trades over the elapsed forward window (using the
    backtest trade cadence) to zero. The elapsed window is capped by
    the strategy's own `entered_forward_date` — a strategy promoted
    yesterday has not had 27 days to produce signals, so its missing-
    signal severity should reflect its 1-day window, not the portfolio
    window. Without `entered_forward_date` the full n_days is used
    (legacy strategies trading since the runner began).
    """
    if tier == "observational":
        return "OBSERVATIONAL"
    bt_trades = baseline.get("trades")
    bt_days = baseline.get("backtest_days")
    if not bt_trades or not bt_days:
        return "NORMAL"

    entered = baseline.get("entered_forward_date")
    if entered:
        days_since_entry = max(
            0, (datetime.now().date() - datetime.fromisoformat(entered).date()).days
        )
        elapsed = min(n_days, days_since_entry)
    else:
        elapsed = n_days

    if elapsed < 5:
        return "NORMAL"
    expected = (bt_trades / bt_days) * elapsed
    if expected >= 20:
        return _apply_tier_clamp("ALARM", tier)
    if expected >= 5:
        return _apply_tier_clamp("DRIFT", tier)
    return "NORMAL"


def compute_strategy_drift(trades: pd.DataFrame) -> dict:
    """Compute per-strategy drift vs baseline.

    Baseline strategies have a `tier` field controlling severity behavior.
    Live strategies present in trades but not in the baseline and not in
    excluded_from_strategy_drift are recorded with tier='uncatalogued' —
    no severity, but surfaced so coverage gaps are visible.
    """
    if trades.empty:
        return {}

    results = {}
    n_total = len(trades)
    n_days = len(trades["date"].unique())
    baseline_strats = BASELINE["strategies"]
    excluded = BASELINE.get("excluded_from_strategy_drift", {})

    for strat_name, baseline in baseline_strats.items():
        tier = baseline.get("tier", "full")
        strat_trades = trades[trades["strategy"] == strat_name]
        n = len(strat_trades)

        if n == 0:
            sev = _missing_signals_severity(tier, baseline, n_days)
            msg = {
                "OBSERVATIONAL": "No trades yet (observational — no severity)",
                "NORMAL": "No trades yet; expected frequency is too low to flag",
                "DRIFT": "Missing signals vs backtest cadence",
                "ALARM": "Zero trades well below expected frequency",
            }.get(sev, "")
            results[strat_name] = {
                "trades": 0, "tier": tier, "severity": sev, "message": msg,
            }
            continue

        # Sample-size guard: below tier minimum, do not classify severity.
        min_trades = MIN_TRADES_FOR_SEVERITY[tier]
        if n < min_trades:
            results[strat_name] = {
                "trades": n, "tier": tier, "severity": "INSUFFICIENT_DATA",
                "message": f"{n} trades < {min_trades} required for {tier} severity classification",
                "win_rate": {"live": round(len(strat_trades[strat_trades["pnl"] > 0]) / n, 3)},
                "avg_pnl": {"live": round(strat_trades["pnl"].mean(), 2)},
                "total_pnl": round(strat_trades["pnl"].sum(), 2),
            }
            continue

        # Win rate
        bt_wr = baseline.get("win_rate")
        live_wr = len(strat_trades[strat_trades["pnl"] > 0]) / n
        wr_delta = (live_wr - bt_wr) if bt_wr is not None else None
        wr_sev = _classify_drift_abs(abs(wr_delta), 0.10, 0.20) if wr_delta is not None else "NORMAL"

        # Trade share (display only, no severity)
        bt_share = baseline.get("trade_share")
        live_share = n / n_total if n_total > 0 else 0
        share_delta = (live_share - bt_share) if bt_share is not None else None

        # Avg PnL
        bt_avg = baseline.get("avg_pnl")
        live_avg = strat_trades["pnl"].mean()
        pnl_ratio = (live_avg / bt_avg) if (bt_avg and bt_avg != 0) else None
        pnl_sev = _classify_drift_degradation(pnl_ratio, 0.50, 0.20) if pnl_ratio is not None else "NORMAL"

        # Trade frequency vs strategy-specific backtest cadence.
        bt_trades = baseline.get("trades")
        bt_days = baseline.get("backtest_days") or 355
        baseline_tpd = (bt_trades / bt_days) if (bt_trades and bt_days) else None
        live_tpd = n / max(n_days, 1)
        freq_ratio = (live_tpd / baseline_tpd) if baseline_tpd else None
        freq_sev = _classify_drift_ratio(freq_ratio, 0.50, 0.70) if freq_ratio is not None else "NORMAL"

        severities = [s for s in (wr_sev, pnl_sev, freq_sev) if s]
        if "ALARM" in severities:
            overall = "ALARM"
        elif "DRIFT" in severities:
            overall = "DRIFT"
        else:
            overall = "NORMAL"

        overall = _apply_tier_clamp(overall, tier)

        results[strat_name] = {
            "trades": n,
            "tier": tier,
            "severity": overall,
            "win_rate": {"baseline": bt_wr, "live": round(live_wr, 3),
                         "delta": round(wr_delta, 3) if wr_delta is not None else None,
                         "severity": wr_sev},
            "avg_pnl": {"baseline": bt_avg, "live": round(live_avg, 2),
                        "ratio": round(pnl_ratio, 2) if pnl_ratio is not None else None,
                        "severity": pnl_sev},
            "trade_frequency": {"baseline_tpd": round(baseline_tpd, 3) if baseline_tpd else None,
                                "live_tpd": round(live_tpd, 3),
                                "ratio": round(freq_ratio, 2) if freq_ratio is not None else None,
                                "severity": freq_sev},
            "trade_share": {"baseline": bt_share, "live": round(live_share, 3),
                            "delta": round(share_delta, 3) if share_delta is not None else None},
        }

    # ── Uncatalogued live strategies ─────────────────────────────────
    # Strategies producing trades but not in baseline or excluded list.
    # Surfaced so registry/baseline gaps are visible instead of silent.
    live_names = set(trades["strategy"].unique())
    catalogued = set(baseline_strats.keys()) | set(excluded.keys())
    uncatalogued = sorted(live_names - catalogued)
    if uncatalogued:
        bucket = {}
        for name in uncatalogued:
            st = trades[trades["strategy"] == name]
            n = len(st)
            wins = len(st[st["pnl"] > 0])
            gross_profit = st[st["pnl"] > 0]["pnl"].sum()
            gross_loss = abs(st[st["pnl"] <= 0]["pnl"].sum())
            pf = (gross_profit / gross_loss) if gross_loss > 0 else float("inf")
            bucket[name] = {
                "trades": n,
                "tier": "uncatalogued",
                "severity": "UNCATALOGUED",
                "win_rate": round(wins / n, 3) if n else None,
                "avg_pnl": round(st["pnl"].mean(), 2) if n else None,
                "total_pnl": round(st["pnl"].sum(), 2),
                "profit_factor": round(pf, 2) if gross_loss > 0 else None,
            }
        results["_uncatalogued_live"] = {
            "tier": "uncatalogued",
            "severity": None,
            "strategies": bucket,
            "message": (
                f"{len(uncatalogued)} live strategies producing trades have "
                f"no baseline entry and are not explicitly excluded. Add to "
                f"BASELINE or reconcile registry."
            ),
        }

    # Note any excluded strategies that are trading (e.g., VolManaged)
    excluded_trading = sorted(live_names & set(excluded.keys()))
    if excluded_trading:
        results["_excluded_from_drift"] = {
            "tier": "excluded",
            "severity": None,
            "strategies": {n: excluded[n] for n in excluded_trading},
            "message": (
                "Tracked separately — these strategies require a dedicated "
                "drift metric. See excluded_from_strategy_drift in BASELINE."
            ),
        }

    return results


def compute_regime_drift(trades: pd.DataFrame, daily_states: list) -> dict:
    """Compute regime-specific performance drift."""
    if not daily_states:
        return {"status": "NO_DATA"}

    # Build regime-to-pnl mapping
    regime_pnl = {}
    for state in daily_states:
        date = state.get("date", "")
        regime = state.get("regime", {})
        vol = regime.get("vol_regime", "NORMAL")
        daily_pnl = state.get("portfolio_daily_pnl", 0)

        regime_pnl.setdefault(vol, []).append(daily_pnl)

    results = {}
    for vol_regime, pnls in regime_pnl.items():
        avg = np.mean(pnls) if pnls else 0
        n_days = len(pnls)
        results[vol_regime] = {
            "days": n_days,
            "avg_daily_pnl": round(avg, 2),
            "total_pnl": round(sum(pnls), 2),
            "positive_rate": round(sum(1 for p in pnls if p > 0) / max(n_days, 1), 2),
        }

    return results


# ── Session / Time-of-Day Drift ──────────────────────────────────────────────

SESSION_BUCKETS = {
    "morning":   (9, 11),    # 09:00–10:59
    "midday":    (11, 13),   # 11:00–12:59
    "afternoon": (13, 16),   # 13:00–15:59
}


def _get_session(entry_time) -> str:
    """Map entry_time (str or Timestamp) to session bucket."""
    try:
        if hasattr(entry_time, "hour"):
            hour = int(entry_time.hour)
        else:
            hour = int(str(entry_time).split(" ")[1].split(":")[0])
    except (IndexError, ValueError, TypeError):
        return "unknown"
    for session, (start, end) in SESSION_BUCKETS.items():
        if start <= hour < end:
            return session
    return "other"


def compute_session_drift(trades: pd.DataFrame) -> dict:
    """Compute per-session and per-strategy-per-session drift.

    Detects cases like:
        - strategy globally healthy but morning edge weakening
        - portfolio drift concentrated in one session window
    """
    if trades.empty or "entry_time" not in trades.columns:
        return {"status": "NO_DATA"}

    trades = trades.copy()
    trades["session"] = trades["entry_time"].apply(_get_session)

    # ── Portfolio-level session breakdown ─────────────────────────────
    portfolio_sessions = {}
    for session in SESSION_BUCKETS:
        sess_trades = trades[trades["session"] == session]
        n = len(sess_trades)
        if n == 0:
            portfolio_sessions[session] = {"trades": 0, "severity": "NORMAL"}
            continue

        wins = len(sess_trades[sess_trades["pnl"] > 0])
        wr = wins / n
        avg_pnl = sess_trades["pnl"].mean()
        total_pnl = sess_trades["pnl"].sum()

        # Profit factor
        gross_profit = sess_trades[sess_trades["pnl"] > 0]["pnl"].sum()
        gross_loss = abs(sess_trades[sess_trades["pnl"] <= 0]["pnl"].sum())
        pf = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        portfolio_sessions[session] = {
            "trades": n,
            "trade_share": round(n / len(trades), 3),
            "win_rate": round(wr, 3),
            "avg_pnl": round(avg_pnl, 2),
            "total_pnl": round(total_pnl, 2),
            "profit_factor": round(pf, 2),
            "severity": "ALARM" if pf < 1.0 and n >= 10 else
                        "DRIFT" if wr < 0.35 and n >= 10 else "NORMAL",
        }

    # ── Per-strategy session breakdown ────────────────────────────────
    strategy_sessions = {}
    for strat_name in BASELINE["strategies"]:
        strat_trades = trades[trades["strategy"] == strat_name]
        if strat_trades.empty:
            continue

        strat_result = {}
        for session in SESSION_BUCKETS:
            sess_trades = strat_trades[strat_trades["session"] == session]
            n = len(sess_trades)
            if n < 3:
                strat_result[session] = {"trades": n, "severity": "INSUFFICIENT_DATA"}
                continue

            wins = len(sess_trades[sess_trades["pnl"] > 0])
            wr = wins / n
            avg_pnl = sess_trades["pnl"].mean()

            # Compare against strategy's overall baseline
            baseline = BASELINE["strategies"][strat_name]
            wr_delta = wr - baseline["win_rate"]
            pnl_ratio = avg_pnl / baseline["avg_pnl"] if baseline["avg_pnl"] != 0 else 0

            severity = "NORMAL"
            if n >= 10:
                if abs(wr_delta) >= 0.20 or pnl_ratio <= 0.20:
                    severity = "ALARM"
                elif abs(wr_delta) >= 0.12 or pnl_ratio <= 0.50:
                    severity = "DRIFT"
            elif n >= 5:
                # Small sample — only flag extreme deviations
                if abs(wr_delta) >= 0.25 and pnl_ratio <= 0.0:
                    severity = "ALARM"
                elif abs(wr_delta) >= 0.20 or pnl_ratio <= 0.10:
                    severity = "DRIFT"

            strat_result[session] = {
                "trades": n,
                "win_rate": round(wr, 3),
                "wr_delta": round(wr_delta, 3),
                "avg_pnl": round(avg_pnl, 2),
                "pnl_ratio": round(pnl_ratio, 2),
                "severity": severity,
            }

        strategy_sessions[strat_name] = strat_result

    # ── Session concentration check ──────────────────────────────────
    # Flag if one session is dominating trade volume
    total = len(trades)
    concentration_warnings = []
    for session, data in portfolio_sessions.items():
        share = data.get("trade_share", 0)
        if share > 0.60 and total >= 20:
            concentration_warnings.append({
                "session": session,
                "share": share,
                "message": f"{session} has {share:.0%} of all trades — concentration risk",
            })

    return {
        "portfolio_sessions": portfolio_sessions,
        "strategy_sessions": strategy_sessions,
        "concentration_warnings": concentration_warnings,
    }


# ── Classification Helpers ───────────────────────────────────────────────────

def _classify_drift_abs(delta: float, drift_thresh: float, alarm_thresh: float) -> str:
    """Classify drift by absolute deviation."""
    if delta >= alarm_thresh:
        return "ALARM"
    elif delta >= drift_thresh:
        return "DRIFT"
    return "NORMAL"


def _classify_drift_ratio(ratio: float, drift_thresh: float, alarm_thresh: float) -> str:
    """Classify drift by ratio (too high or too low)."""
    deviation = abs(1.0 - ratio)
    if deviation >= alarm_thresh:
        return "ALARM"
    elif deviation >= drift_thresh:
        return "DRIFT"
    return "NORMAL"


def _classify_drift_degradation(ratio: float, drift_floor: float, alarm_floor: float) -> str:
    """Classify drift by degradation from baseline (ratio < 1.0 = worse)."""
    if ratio <= alarm_floor:
        return "ALARM"
    elif ratio <= drift_floor:
        return "DRIFT"
    return "NORMAL"


def _classify_drift_floor(value: float, drift_floor: float, alarm_floor: float) -> str:
    """Classify drift by absolute floor value."""
    if value <= alarm_floor:
        return "ALARM"
    elif value <= drift_floor:
        return "DRIFT"
    return "NORMAL"


# ── Main Runner ──────────────────────────────────────────────────────────────

def run_drift_monitor() -> dict:
    """Run full drift analysis and return structured results."""
    trades = load_forward_trades()
    daily_states = load_daily_states()
    equity = load_equity_curve()

    report_date = datetime.now().strftime("%Y-%m-%d %H:%M")

    portfolio_drift = compute_portfolio_drift(trades, equity, daily_states)
    strategy_drift = compute_strategy_drift(trades)
    regime_drift = compute_regime_drift(trades, daily_states)
    session_drift = compute_session_drift(trades)

    # Build alerts
    alerts = []

    # Portfolio-level alerts
    if portfolio_drift.get("status") == "ALARM":
        alerts.append({
            "level": "ALARM",
            "scope": "PORTFOLIO",
            "message": "Portfolio-level metrics show significant divergence from backtest baseline",
        })
    elif portfolio_drift.get("status") == "DRIFT":
        alerts.append({
            "level": "DRIFT",
            "scope": "PORTFOLIO",
            "message": "Portfolio metrics drifting from baseline — monitor closely",
        })

    # Strategy-level alerts — skip meta keys (_uncatalogued_live,
    # _excluded_from_drift). OBSERVATIONAL and UNCATALOGUED severities
    # do not produce alerts by design.
    for strat, data in strategy_drift.items():
        if strat.startswith("_"):
            continue
        if data.get("severity") == "ALARM":
            alerts.append({
                "level": "ALARM",
                "scope": strat,
                "message": f"{strat}: forward performance significantly diverges from backtest",
            })
        elif data.get("severity") == "DRIFT":
            alerts.append({
                "level": "DRIFT",
                "scope": strat,
                "message": f"{strat}: drifting from baseline metrics",
            })

    # Coverage-gap INFO alerts — visible but non-blocking.
    uncat = strategy_drift.get("_uncatalogued_live")
    if uncat and uncat.get("strategies"):
        names = sorted(uncat["strategies"].keys())
        alerts.append({
            "level": "INFO",
            "scope": "COVERAGE",
            "message": (
                f"Uncatalogued live strategies ({len(names)}): "
                f"{', '.join(names)}. Add to BASELINE or reconcile registry."
            ),
        })

    # Portfolio baseline staleness notice (non-blocking).
    pb_status = portfolio_drift.get("baseline_status")
    if pb_status == "STALE_PENDING_REFRESH":
        alerts.append({
            "level": "INFO",
            "scope": "PORTFOLIO_BASELINE",
            "message": (
                "Portfolio baseline is stale (Phase 17 composition). "
                "Portfolio status capped at DRIFT until refreshed."
            ),
        })

    # Session-level alerts
    for session, data in session_drift.get("portfolio_sessions", {}).items():
        if data.get("severity") == "ALARM":
            alerts.append({
                "level": "ALARM",
                "scope": f"SESSION:{session}",
                "message": f"{session} session: portfolio losing money (PF={data.get('profit_factor', 0):.2f})",
            })
    for strat, sessions in session_drift.get("strategy_sessions", {}).items():
        for session, data in sessions.items():
            if data.get("severity") == "ALARM":
                alerts.append({
                    "level": "ALARM",
                    "scope": f"{strat}:{session}",
                    "message": f"{strat}: {session} edge degrading (WR delta {data.get('wr_delta', 0):+.1%})",
                })
            elif data.get("severity") == "DRIFT":
                alerts.append({
                    "level": "DRIFT",
                    "scope": f"{strat}:{session}",
                    "message": f"{strat}: {session} session drifting from baseline",
                })
    for warn in session_drift.get("concentration_warnings", []):
        alerts.append({
            "level": "DRIFT",
            "scope": f"SESSION:{warn['session']}",
            "message": warn["message"],
        })

    results = {
        "report_date": report_date,
        "forward_period": {
            "days": portfolio_drift.get("forward_days", 0),
            "trades": portfolio_drift.get("forward_trades", 0),
        },
        "portfolio_drift": portfolio_drift,
        "strategy_drift": strategy_drift,
        "regime_drift": regime_drift,
        "session_drift": session_drift,
        "alerts": alerts,
        "overall_status": portfolio_drift.get("status", "NO_DATA"),
    }

    return results


# ── Terminal Report ──────────────────────────────────────────────────────────

def print_drift_report(results: dict):
    """Print formatted drift report to terminal."""
    W = 75
    SEP = "=" * W
    THIN = "-" * 55

    print()
    print(SEP)
    print("  FQL LIVE DRIFT MONITOR")
    print(f"  {results['report_date']}")
    print(f"  Overall: {results['overall_status']}")
    print(SEP)

    period = results["forward_period"]
    print(f"\n  Forward period: {period['days']} days, {period['trades']} trades")

    # ── Portfolio Drift ──
    pd_data = results["portfolio_drift"]
    if pd_data.get("status") == "NO_DATA":
        print(f"\n  {pd_data.get('message', 'No data')}")
        return

    print(f"\n  PORTFOLIO DRIFT")
    print(f"  {THIN}")
    print(f"  {'Metric':<22s} {'Baseline':>10s} {'Live':>10s} {'Delta':>10s} {'Status':>8s}")
    print(f"  {'-' * 62}")

    metrics = pd_data["metrics"]
    for key in ["win_rate", "trade_frequency", "expectancy", "profit_factor", "sharpe"]:
        m = metrics.get(key, {})
        if "baseline" in m:
            baseline_val = f"{m['baseline']:.3f}" if isinstance(m["baseline"], float) else str(m["baseline"])
            live_val = f"{m['live']:.3f}" if isinstance(m["live"], float) else str(m["live"])
        elif "baseline_tpd" in m:
            baseline_val = f"{m['baseline_tpd']:.2f}"
            live_val = f"{m['live_tpd']:.2f}"
        elif "baseline_avg_pnl" in m:
            baseline_val = f"${m['baseline_avg_pnl']:.2f}"
            live_val = f"${m['live_avg_pnl']:.2f}"
        else:
            continue

        delta = m.get("delta", m.get("ratio", ""))
        if isinstance(delta, float):
            delta_str = f"{delta:+.3f}"
        else:
            delta_str = str(delta)

        severity = m.get("severity", "—")
        indicator = {"NORMAL": "  ", "DRIFT": "! ", "ALARM": "!!"}
        ind = indicator.get(severity, "  ")

        print(f"  {ind}{key:<20s} {baseline_val:>10s} {live_val:>10s} {delta_str:>10s} {severity:>8s}")

    # Payoff structure
    print(f"\n  PAYOFF STRUCTURE")
    print(f"  {THIN}")
    aw = metrics.get("avg_winner", {})
    al = metrics.get("avg_loser", {})
    if aw:
        print(f"  Avg winner:  baseline ${aw['baseline']:.2f}  |  live ${aw['live']:.2f}")
    if al:
        print(f"  Avg loser:   baseline ${al['baseline']:.2f}  |  live ${al['live']:.2f}")

    # ── Strategy Drift ──
    strat_drift = results["strategy_drift"]
    if strat_drift:
        print(f"\n  STRATEGY DRIFT")
        print(f"  {THIN}")
        print(f"  {'Strategy':<28s} {'Trades':>6s} {'WR Δ':>8s} {'PnL ratio':>10s} {'Status':>8s}")
        print(f"  {'-' * 62}")

        def _sev_rank(s):
            return {"ALARM": 0, "DRIFT": 1, "OBSERVATIONAL": 2,
                    "NORMAL": 3, "INSUFFICIENT_DATA": 4,
                    "UNCATALOGUED": 5, None: 6}.get(s, 6)

        catalogued = [(k, v) for k, v in strat_drift.items() if not k.startswith("_")]
        for strat, data in sorted(catalogued, key=lambda x: _sev_rank(x[1].get("severity"))):
            n = data.get("trades", 0)
            wr = data.get("win_rate", {}) or {}
            pnl = data.get("avg_pnl", {}) or {}
            sev = data.get("severity", "—") or "—"
            tier = data.get("tier", "—")

            wr_delta = f"{wr.get('delta'):+.3f}" if isinstance(wr.get("delta"), (int, float)) else "—"
            pnl_ratio = f"{pnl.get('ratio'):.2f}x" if isinstance(pnl.get("ratio"), (int, float)) else "—"

            indicator = {"ALARM": "!!", "DRIFT": "! ", "NORMAL": "  ",
                         "OBSERVATIONAL": "· ", "INSUFFICIENT_DATA": "· ",
                         "UNCATALOGUED": "? "}
            ind = indicator.get(sev, "  ")
            print(f"  {ind}{strat:<26s} {n:>6d} {wr_delta:>8s} {pnl_ratio:>10s} {sev:>14s}  [{tier}]")

        uncat = strat_drift.get("_uncatalogued_live")
        if uncat and uncat.get("strategies"):
            print(f"\n  UNCATALOGUED LIVE (no baseline — coverage gap)")
            print(f"  {THIN}")
            for name, data in sorted(uncat["strategies"].items()):
                pf = data.get("profit_factor")
                pf_str = f"{pf:.2f}" if isinstance(pf, (int, float)) else "—"
                print(f"  ? {name:<34s} trades={data['trades']:>3d}  "
                      f"WR={data.get('win_rate',0):.0%}  PF={pf_str}  "
                      f"total_pnl=${data.get('total_pnl', 0):+.0f}")

        exc = strat_drift.get("_excluded_from_drift")
        if exc and exc.get("strategies"):
            print(f"\n  EXCLUDED FROM STRATEGY DRIFT (tracked separately)")
            print(f"  {THIN}")
            for name in sorted(exc["strategies"].keys()):
                print(f"  ~ {name}")

    # ── Regime Drift ──
    regime_drift = results.get("regime_drift", {})
    if regime_drift and regime_drift.get("status") != "NO_DATA":
        print(f"\n  REGIME-SPECIFIC PERFORMANCE")
        print(f"  {THIN}")
        for regime, data in sorted(regime_drift.items()):
            if isinstance(data, dict) and "days" in data:
                print(f"  {regime:<15s} {data['days']}d  avg ${data['avg_daily_pnl']:>8.2f}/day  "
                      f"total ${data['total_pnl']:>8.2f}  pos_rate {data['positive_rate']:.0%}")

    # ── Session Drift ──
    session_drift = results.get("session_drift", {})
    if session_drift and session_drift.get("status") != "NO_DATA":
        port_sess = session_drift.get("portfolio_sessions", {})
        if port_sess:
            print(f"\n  SESSION / TIME-OF-DAY DRIFT")
            print(f"  {THIN}")
            print(f"  {'Session':<12s} {'Trades':>6s} {'Share':>7s} {'WR':>7s} {'Avg PnL':>10s} {'PF':>7s} {'Status':>8s}")
            print(f"  {'-' * 59}")
            for session in ["morning", "midday", "afternoon"]:
                data = port_sess.get(session, {})
                n = data.get("trades", 0)
                if n == 0:
                    print(f"  {session:<12s} {'0':>6s}")
                    continue
                sev = data.get("severity", "NORMAL")
                ind = {"NORMAL": "  ", "DRIFT": "! ", "ALARM": "!!"}
                print(f"  {ind.get(sev, '  ')}{session:<10s} {n:>6d} {data.get('trade_share', 0):>6.0%} "
                      f"{data.get('win_rate', 0):>6.1%} ${data.get('avg_pnl', 0):>8.2f} "
                      f"{data.get('profit_factor', 0):>6.2f} {sev:>8s}")

        # Per-strategy session breakdown (only show non-NORMAL)
        strat_sess = session_drift.get("strategy_sessions", {})
        flagged = []
        for strat, sessions in strat_sess.items():
            for session, data in sessions.items():
                if data.get("severity") in ("DRIFT", "ALARM"):
                    flagged.append((strat, session, data))

        if flagged:
            print(f"\n  Strategy session drift flags:")
            for strat, session, data in flagged:
                sev = data["severity"]
                ind = "!!" if sev == "ALARM" else "! "
                print(f"  {ind}{strat} [{session}]: WR {data.get('win_rate', 0):.0%} "
                      f"(delta {data.get('wr_delta', 0):+.1%}), "
                      f"avg ${data.get('avg_pnl', 0):.2f}, {data.get('trades', 0)} trades — {sev}")

        # Concentration warnings
        for warn in session_drift.get("concentration_warnings", []):
            print(f"  ! {warn['message']}")

    # ── Alerts ──
    alerts = results.get("alerts", [])
    if alerts:
        print(f"\n  DRIFT ALERTS")
        print(f"  {THIN}")
        for a in alerts:
            level = a["level"]
            indicator = "!!" if level == "ALARM" else "! "
            print(f"  {indicator}[{level}] {a['message']}")
    else:
        print(f"\n  No drift alerts.")

    print()
    print(SEP)


# ── Persistence ──────────────────────────────────────────────────────────────

def save_drift_log(results: dict):
    """Append drift results to persistent log."""
    log = []
    if DRIFT_LOG_PATH.exists():
        try:
            with open(DRIFT_LOG_PATH) as f:
                log = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            log = []

    log.append({
        "date": results["report_date"],
        "overall_status": results["overall_status"],
        "forward_days": results["forward_period"]["days"],
        "forward_trades": results["forward_period"]["trades"],
        "alerts_count": len(results.get("alerts", [])),
        "portfolio_status": results["portfolio_drift"].get("status", "NO_DATA"),
        "session_drift": results.get("session_drift", {}),
    })

    # Keep last 365 entries
    if len(log) > 365:
        log = log[-365:]

    DRIFT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    from research.utils.atomic_io import atomic_write_json
    atomic_write_json(DRIFT_LOG_PATH, log)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="FQL Live Drift Monitor")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--save", action="store_true", help="Save report + log")
    args = parser.parse_args()

    results = run_drift_monitor()

    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        print_drift_report(results)

    if args.save:
        save_drift_log(results)
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        path = REPORTS_DIR / f"drift_report_{timestamp}.json"
        with open(path, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"Drift report saved: {path}")
        print(f"Drift log updated: {DRIFT_LOG_PATH}")


if __name__ == "__main__":
    main()
