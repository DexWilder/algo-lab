# Strategy Spec: Treasury-12M-TSM

## Hypothesis
Treasury futures exhibit persistent time-series momentum driven by macro regime persistence (Fed policy cycles, inflation trends, growth expectations). When a Treasury contract's trailing 12-month return is positive, it tends to continue positive; when negative, it tends to continue negative. This is one of the most documented systematic factors in the academic literature (Moskowitz, Ooi, Pedersen 2012) and Treasury futures are a core asset class in the original research.

The signal is pure trailing return — no discretionary macro interpretation needed. Monthly rebalance captures the slow-moving policy/inflation regime without overtrading.

## Signal Logic
- **Trailing return:** Compute the 252-trading-day (12-month) return for each Treasury contract
- **Direction signal:**
  - 12-month return > 0 → long (rates falling / bonds rallying)
  - 12-month return < 0 → short (rates rising / bonds selling off)
- **Rebalance:** End of each month, evaluate signal and adjust position
- **Position held until next rebalance** (no intra-month exits except stop)

## Rebalance Timing
- **Frequency:** Monthly (last trading day of each month)
- **Signal evaluation:** 12-month return computed on rebalance day
- **Position change:** at next day's open after rebalance signal
- **No intra-month trading** — hold through the month regardless of short-term moves
- **Stop:** toggle (none vs 2.0x ATR from entry)

## Target Assets
- Primary: ZN (10-Year Note — benchmark, most liquid)
- Secondary: ZF (5-Year Note — shorter duration, different rate sensitivity)
- Tertiary: ZB (30-Year Bond — longer duration, higher vol per move)
- Test each independently, not as a basket (keep it simple for v1)

## Parameters (initial)
- LOOKBACK_DAYS: 252 (12-month trailing return)
- REBALANCE: monthly (last trading day)
- USE_STOP: toggle (True/False)
- ATR_LEN: 20
- SL_ATR_MULT: 2.0

## Source
- Moskowitz, Ooi, Pedersen (2012): "Time Series Momentum" — Journal of Financial Economics
- Quantpedia: Time-Series Momentum Effect
- OpenClaw harvest note: 07_treasury_12m_time_series_momentum.md

## Key Failure Mode to Watch
- **Regime transitions:** The 12-month lookback is slow to react to sharp regime changes (e.g., the 2022 rate shock from near-zero to 5%). The signal may stay long while bonds crash, generating a large drawdown at the turning point.
- **Momentum high-bar:** This IS momentum on rates. It passes the high-bar rule because it's a new asset class with no existing momentum coverage. But the portfolio's 54% momentum factor concentration means this adds to the MOMENTUM factor, not a new one.
- **Monthly rebalance = low trade count:** ~12 signal evaluations per year, but position may not change every month. Expect 6-10 actual trades per year. With 6.7 years of data: ~40-65 trades. Adequate for first-pass.

## Important Notes
- This is the simplest possible rates macro strategy. If 12-month TSM doesn't work on treasuries, more complex rates strategies are unlikely to work either.
- The backfill just extended ZN/ZF/ZB to 2019, covering both the low-rate era (2019-2021) and the tightening cycle (2022-2024). This provides the regime diversity needed for a fair test.
- The 2022 rate shock is THE critical test: the signal should have been long going into 2022 (rates were low/falling) and should have flipped to short after bonds crashed. The transition period will show the maximum drawdown.

## Diversification Role
- **Factor:** MOMENTUM (high-bar pass — new asset class without momentum coverage)
- **Asset class:** Rates — the #1 missing asset class (0 active strategies)
- **Horizon:** Monthly rebalance (longest signal horizon in FQL)
- **Correlation to existing portfolio:** Should be low — rate momentum is driven by macro policy cycles, not equity price patterns
- **Expected contribution:** If it works, this is the first rates strategy in the portfolio. Even a modest PF (1.2-1.5) would be highly valuable because rates are genuinely uncorrelated to equities.
