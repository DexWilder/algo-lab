"""Multi-factor regime engine — extends ATR classifier with trend and realized vol.

Builds on engine/regime.py (ATR percentile classifier) without modifying it.
Adds trend detection (EMA slope) and realized volatility as additional factors.

Usage:
    from engine.regime_engine import RegimeEngine

    engine = RegimeEngine()
    df = engine.classify(df)  # adds vol_regime, trend_regime, rv_regime, composite_regime
    active = engine.get_active_strategies(date, profiles)
"""

import numpy as np
import pandas as pd

from engine.regime import classify_regimes


# ── Default Thresholds ───────────────────────────────────────────────────────

DEFAULT_CONFIG = {
    # ATR volatility (reuses engine.regime thresholds)
    "atr_period": 20,
    "atr_lookback": 252,
    "atr_low_pct": 33.3,
    "atr_high_pct": 66.7,

    # Trend (20-day EMA slope)
    "trend_ema_period": 20,
    "trend_slope_threshold": 0.0005,  # min abs slope for TRENDING

    # Realized volatility (14-day rolling stdev of daily returns × √252)
    "rv_lookback": 14,
    "rv_low_pct": 33.3,
    "rv_high_pct": 66.7,
    "rv_ranking_lookback": 252,

    # Trend persistence (rolling directional consistency)
    "persistence_window": 20,
    "persistence_grind_threshold": 8,  # abs(score) >= 8 out of 20 = GRINDING (~12% of days)
}


class RegimeEngine:
    """Multi-factor daily regime classification engine.

    Factors:
    - Volatility: ATR percentile rank (LOW_VOL / NORMAL / HIGH_VOL)
    - Trend: 20-day EMA slope sign + magnitude (TRENDING / RANGING)
    - Realized Vol: 14-day rolling stdev of returns × √252 (LOW_RV / NORMAL_RV / HIGH_RV)
    - Trend Persistence: rolling sum of daily direction signs (GRINDING / CHOPPY)
      Separates sustained directional grinds from breakout/reversal days.

    Composite regime is the combination of vol + trend states.
    """

    def __init__(self, config=None):
        self.config = {**DEFAULT_CONFIG, **(config or {})}

    def classify(self, df: pd.DataFrame) -> pd.DataFrame:
        """Multi-factor daily regime classification.

        Adds columns: vol_regime, trend_regime, rv_regime, composite_regime.
        Returns df with all regime columns.

        Parameters
        ----------
        df : pd.DataFrame
            OHLCV data with 'datetime', 'open', 'high', 'low', 'close' columns.
        """
        cfg = self.config
        out = df.copy()
        out["_date"] = pd.to_datetime(out["datetime"]).dt.date

        # ── Factor 1: ATR Volatility (reuse existing classifier) ─────────
        out = classify_regimes(
            out,
            atr_period=cfg["atr_period"],
            lookback=cfg["atr_lookback"],
            low_pct=cfg["atr_low_pct"],
            high_pct=cfg["atr_high_pct"],
        )
        # Map existing regime labels to standardized names
        vol_map = {"low": "LOW_VOL", "medium": "NORMAL", "high": "HIGH_VOL"}
        out["vol_regime"] = out["regime"].map(vol_map).fillna("NORMAL")

        # ── Factor 2: Trend (EMA slope) ──────────────────────────────────
        # Compute daily close for EMA
        daily_close = out.groupby("_date")["close"].last()
        ema = daily_close.ewm(span=cfg["trend_ema_period"], adjust=False).mean()

        # Slope: normalized change per day
        ema_slope = ema.pct_change()

        threshold = cfg["trend_slope_threshold"]
        trend_labels = ema_slope.map(
            lambda s: "TRENDING" if (not pd.isna(s) and abs(s) >= threshold) else "RANGING"
        )

        trend_df = pd.DataFrame({
            "_date": trend_labels.index,
            "trend_regime": trend_labels.values,
        })
        out = out.merge(trend_df, on="_date", how="left")
        out["trend_regime"] = out["trend_regime"].fillna("RANGING")

        # ── Factor 3: Realized Volatility ────────────────────────────────
        daily_returns = daily_close.pct_change()
        rolling_rv = daily_returns.rolling(
            window=cfg["rv_lookback"], min_periods=5
        ).std() * np.sqrt(252)

        # Percentile rank within lookback
        rv_pctrank = rolling_rv.rolling(
            cfg["rv_ranking_lookback"], min_periods=20
        ).apply(lambda x: (x.iloc[-1] >= x).sum() / len(x) * 100, raw=False)

        def _rv_label(pct):
            if pd.isna(pct):
                return "NORMAL_RV"
            if pct <= cfg["rv_low_pct"]:
                return "LOW_RV"
            if pct >= cfg["rv_high_pct"]:
                return "HIGH_RV"
            return "NORMAL_RV"

        rv_labels = rv_pctrank.map(_rv_label)
        rv_df = pd.DataFrame({
            "_date": rv_labels.index,
            "rv_regime": rv_labels.values,
        })
        out = out.merge(rv_df, on="_date", how="left")
        out["rv_regime"] = out["rv_regime"].fillna("NORMAL_RV")

        # ── Factor 4: Trend Persistence ────────────────────────────────
        # Rolling sum of sign(daily returns) over N days.
        # High absolute value = sustained directional grind (GRINDING)
        # Low absolute value = choppy, no directional consistency (CHOPPY)
        daily_direction = np.sign(daily_close.diff())
        persistence = daily_direction.rolling(
            window=cfg["persistence_window"], min_periods=10
        ).sum()

        grind_thresh = cfg["persistence_grind_threshold"]
        persistence_labels = persistence.map(
            lambda p: "GRINDING" if (not pd.isna(p) and abs(p) >= grind_thresh) else "CHOPPY"
        )

        persist_df = pd.DataFrame({
            "_date": persistence_labels.index,
            "trend_persistence": persistence_labels.values,
            "persistence_score": persistence.values,
        })
        out = out.merge(persist_df, on="_date", how="left")
        out["trend_persistence"] = out["trend_persistence"].fillna("CHOPPY")
        out["persistence_score"] = out["persistence_score"].fillna(0.0)

        # ── Composite Regime ─────────────────────────────────────────────
        # Combination of vol + trend (not mutually exclusive)
        out["composite_regime"] = out["vol_regime"] + "_" + out["trend_regime"]

        return out

    def get_daily_regimes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Return one row per date with all regime labels.

        Useful for merging with trade logs.
        """
        classified = self.classify(df)
        daily = classified.groupby("_date").agg(
            vol_regime=("vol_regime", "last"),
            trend_regime=("trend_regime", "last"),
            rv_regime=("rv_regime", "last"),
            trend_persistence=("trend_persistence", "last"),
            persistence_score=("persistence_score", "last"),
            composite_regime=("composite_regime", "last"),
        ).reset_index()
        return daily

    def get_active_strategies(self, date_regime: dict, profiles: dict) -> list:
        """Given a date's regime state, return which strategies should be active.

        Parameters
        ----------
        date_regime : dict
            Keys: vol_regime, trend_regime, rv_regime, composite_regime.
        profiles : dict
            Strategy regime profiles. Each key is a strategy label, each value
            has 'preferred_regimes' and 'avoid_regimes' lists.

        Returns
        -------
        list of strategy labels that are active in this regime.
        """
        active = []
        current_regimes = set()
        for key in ["vol_regime", "trend_regime", "rv_regime"]:
            if key in date_regime:
                current_regimes.add(date_regime[key])

        for strat_label, profile in profiles.items():
            avoid = set(profile.get("avoid_regimes", []))
            if avoid & current_regimes:
                continue
            active.append(strat_label)

        return active

    def regime_summary(self, df: pd.DataFrame) -> dict:
        """Compute distribution of regime states across the dataset.

        Returns dict with counts and percentages per regime factor.
        """
        classified = self.classify(df)
        daily = classified.groupby("_date").first()
        n_days = len(daily)

        summary = {}
        for col in ["vol_regime", "trend_regime", "rv_regime", "trend_persistence", "composite_regime"]:
            counts = daily[col].value_counts()
            summary[col] = {
                state: {"count": int(cnt), "pct": round(cnt / n_days * 100, 1)}
                for state, cnt in counts.items()
            }

        summary["total_days"] = n_days
        return summary
