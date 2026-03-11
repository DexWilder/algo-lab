"""
Forward Paper Trading Monitor — READ-ONLY Dashboard
Usage: streamlit run scripts/dashboard.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Forward Trading Monitor",
    layout="wide",
    initial_sidebar_state="expanded",
)

ROOT = Path(__file__).resolve().parent.parent

TRADE_LOG = ROOT / "logs" / "trade_log.csv"
DAILY_REPORT = ROOT / "logs" / "daily_report.csv"
SIGNAL_LOG = ROOT / "logs" / "signal_log.csv"
ACCOUNT_STATE = ROOT / "state" / "account_state.json"
KILL_SWITCH_EVENTS = ROOT / "logs" / "kill_switch_events.csv"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_csv_safe(path: Path) -> pd.DataFrame | None:
    """Return a DataFrame or None if the file is missing / empty."""
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path)
        return df if not df.empty else None
    except Exception:
        return None


def read_json_safe(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def color_pnl(val):
    """Style helper — green for positive PnL, red for negative."""
    try:
        v = float(val)
    except (ValueError, TypeError):
        return ""
    return "color: #4caf50" if v >= 0 else "color: #f44336"

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

st.sidebar.title("Controls")
if st.sidebar.button("Refresh"):
    st.rerun()
st.sidebar.caption(f"Last update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

daily_df = read_csv_safe(DAILY_REPORT)
trade_df = read_csv_safe(TRADE_LOG)
signal_df = read_csv_safe(SIGNAL_LOG)
account = read_json_safe(ACCOUNT_STATE)

# ---------------------------------------------------------------------------
# Title
# ---------------------------------------------------------------------------

st.title("Forward Paper Trading Monitor")

# ---------------------------------------------------------------------------
# Top row — Key metrics
# ---------------------------------------------------------------------------

if daily_df is not None:
    latest = daily_df.iloc[-1]
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Current Equity", f"${latest.get('equity', 0):,.2f}")
    c2.metric("Cumulative PnL", f"${latest.get('cumulative_pnl', 0):,.2f}")
    c3.metric("Today's PnL", f"${latest.get('daily_pnl', 0):,.2f}")
    c4.metric("Trailing DD", f"${latest.get('trailing_dd', 0):,.2f}")

    kill = latest.get("kill_switch", False)
    kill_label = "TRIGGERED" if kill else "OK"
    c5.metric("Kill Switch", kill_label)
elif account is not None:
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Current Equity", f"${account.get('equity', 0):,.2f}")
    c2.metric("Cumulative PnL", f"${account.get('cumulative_pnl', 0):,.2f}")
    c3.metric("Today's PnL", f"${account.get('daily_pnl', 0):,.2f}")
    c4.metric("Trailing DD", f"${account.get('trailing_dd', 0):,.2f}")
    kill = account.get("kill_switch", False)
    c5.metric("Kill Switch", "TRIGGERED" if kill else "OK")
else:
    st.info("No daily report or account state data yet.")

# ---------------------------------------------------------------------------
# Section 1 — Equity Curve
# ---------------------------------------------------------------------------

st.header("Equity Curve")

if daily_df is not None and "equity" in daily_df.columns:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily_df["date"],
        y=daily_df["equity"],
        mode="lines",
        line=dict(color="#00bcd4", width=2),
        name="Equity",
    ))
    fig.update_layout(
        template="plotly_dark",
        xaxis_title="Date",
        yaxis_title="Equity ($)",
        height=400,
        margin=dict(l=40, r=20, t=20, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No equity data yet.")

# ---------------------------------------------------------------------------
# Section 2 — Today's Trades
# ---------------------------------------------------------------------------

st.header("Today's Trades")

if trade_df is not None and "date" in trade_df.columns:
    latest_date = trade_df["date"].iloc[-1]
    today_trades = trade_df[trade_df["date"] == latest_date][["strategy", "side", "pnl"]].copy()
    if today_trades.empty:
        st.info("No trades on the most recent date.")
    else:
        styled = today_trades.style.applymap(color_pnl, subset=["pnl"]).format({"pnl": "${:,.2f}"})
        st.dataframe(styled, use_container_width=True, hide_index=True)
else:
    st.info("No trade log data yet.")

# ---------------------------------------------------------------------------
# Section 3 — Strategy Contributions
# ---------------------------------------------------------------------------

st.header("Strategy Contributions")

if trade_df is not None and "strategy" in trade_df.columns and "pnl" in trade_df.columns:
    col_a, col_b = st.columns(2)

    # Cumulative PnL per strategy bar chart
    strat_pnl = trade_df.groupby("strategy")["pnl"].sum().reset_index()
    strat_pnl.columns = ["strategy", "cumulative_pnl"]
    colors = ["#4caf50" if v >= 0 else "#f44336" for v in strat_pnl["cumulative_pnl"]]

    fig2 = go.Figure(go.Bar(
        x=strat_pnl["strategy"],
        y=strat_pnl["cumulative_pnl"],
        marker_color=colors,
    ))
    fig2.update_layout(
        template="plotly_dark",
        yaxis_title="Cumulative PnL ($)",
        height=350,
        margin=dict(l=40, r=20, t=20, b=40),
    )
    col_a.plotly_chart(fig2, use_container_width=True)

    # Trade count and win rate table
    strat_stats = trade_df.groupby("strategy")["pnl"].agg(
        trades="count",
        wins=lambda x: (x > 0).sum(),
        total_pnl="sum",
        avg_pnl="mean",
    ).reset_index()
    strat_stats["win_rate"] = (strat_stats["wins"] / strat_stats["trades"] * 100).round(1)
    strat_stats["total_pnl"] = strat_stats["total_pnl"].round(2)
    strat_stats["avg_pnl"] = strat_stats["avg_pnl"].round(2)
    strat_stats["share"] = (strat_stats["trades"] / strat_stats["trades"].sum() * 100).round(1)
    strat_stats = strat_stats[["strategy", "trades", "share", "win_rate", "avg_pnl", "total_pnl"]]
    strat_stats.columns = ["Strategy", "Trades", "Share (%)", "Win Rate (%)", "Avg PnL ($)", "Total PnL ($)"]
    col_b.dataframe(strat_stats, use_container_width=True, hide_index=True)
else:
    st.info("No trade data yet.")

# ---------------------------------------------------------------------------
# Section 4 — Regime Detection
# ---------------------------------------------------------------------------

st.header("Regime Detection")

if daily_df is not None and "regime" in daily_df.columns:
    col_r1, col_r2 = st.columns(2)

    latest_regime = daily_df["regime"].iloc[-1]
    col_r1.subheader("Current Regime")
    col_r1.markdown(f"### `{latest_regime}`")

    if "rv_regime" in daily_df.columns:
        col_r1.markdown(f"**RV Regime:** `{daily_df['rv_regime'].iloc[-1]}`")
    if "persistence" in daily_df.columns:
        col_r1.markdown(f"**Persistence:** `{daily_df['persistence'].iloc[-1]}`")

    # Regime distribution — donut chart + percentage table
    regime_counts = daily_df["regime"].value_counts().reset_index()
    regime_counts.columns = ["regime", "days"]
    fig3 = px.pie(
        regime_counts,
        names="regime",
        values="days",
        template="plotly_dark",
        hole=0.4,
    )
    fig3.update_layout(height=350, margin=dict(l=20, r=20, t=20, b=20))
    col_r2.plotly_chart(fig3, use_container_width=True)

    # Regime percentage table
    total_days = regime_counts["days"].sum()
    regime_counts["pct"] = (regime_counts["days"] / total_days * 100).round(1)
    regime_counts.columns = ["Regime", "Days", "Share (%)"]
    col_r1.dataframe(regime_counts, use_container_width=True, hide_index=True)
else:
    st.info("No regime data yet.")

# ---------------------------------------------------------------------------
# Section 5 — Signal Filtering
# ---------------------------------------------------------------------------

st.header("Signal Filtering")

if signal_df is not None and not signal_df.empty:
    latest_date = signal_df["date"].iloc[-1]
    today_signals = signal_df[signal_df["date"] == latest_date]

    if today_signals.empty:
        st.info("No signal data for the latest date.")
    else:
        totals = today_signals[["signals_total", "signals_kept", "regime_blocked", "timing_blocked"]].sum()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Signals", int(totals["signals_total"]))
        c2.metric("Kept", int(totals["signals_kept"]))
        c3.metric("Regime Blocked", int(totals["regime_blocked"]))
        c4.metric("Timing Blocked", int(totals["timing_blocked"]))

        st.dataframe(
            today_signals[["strategy", "signals_total", "signals_kept",
                           "regime_blocked", "timing_blocked", "conviction_override"]],
            use_container_width=True,
            hide_index=True,
        )
else:
    st.info("No signal log data yet.")

# ---------------------------------------------------------------------------
# Section 6 — Kill Switch
# ---------------------------------------------------------------------------

st.header("Kill Switch")

if daily_df is not None and "kill_switch" in daily_df.columns:
    kill_active = bool(daily_df["kill_switch"].iloc[-1])
    if kill_active:
        st.error("KILL SWITCH TRIGGERED — trading halted.")
    else:
        st.success("Kill switch OK — trading active.")
else:
    st.info("No kill switch status available.")

kill_events = read_csv_safe(KILL_SWITCH_EVENTS)
if kill_events is not None:
    st.subheader("Recent Kill Switch Events")
    st.dataframe(kill_events.tail(20), use_container_width=True, hide_index=True)
