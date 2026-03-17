# Strategy Spec: TV-Gold-Bandwidth-Squeeze

## Hypothesis
Gold futures exhibit periods of extreme volatility compression (Bollinger BandWidth squeeze) that reliably precede directional expansion. Prolonged low-volatility consolidation in gold builds energy that releases into outsized moves. Unlike equity indices where squeezes can resolve in either direction randomly, gold squeezes often resolve in the direction of the prevailing macro trend due to gold's structural role as a macro hedge.

This is a VOLATILITY factor strategy — the signal is the compression state itself, not the direction of price momentum.

## Squeeze Definition
- **Bollinger BandWidth:** (Upper Band - Lower Band) / Middle Band
- **Squeeze detected:** BandWidth drops below its 120-day rolling percentile threshold (bottom 20%)
- **Squeeze release:** BandWidth expands back above the threshold after a squeeze period
- **Minimum squeeze duration:** 5 bars (to avoid noise squeezes)

## Entry
- Condition 1: Squeeze has been active for at least 5 daily bars
- Condition 2: BandWidth expands (squeeze release detected)
- Condition 3: Direction determined by close relative to the Bollinger midline (20-SMA):
  - Close above midline at release → long
  - Close below midline at release → short
- Condition 4: Volume confirmation — release bar volume > 1.2x 20-day average (optional toggle)
- Direction: both

## Exit
- Trail: 2.0x ATR(20) trailing stop (let expansion run)
- Trend reversal: exit if price crosses back through the Bollinger midline against position
- Time stop: 20 daily bars (if no expansion materializes, thesis is wrong)
- No fixed target — vol expansion moves can be large

## Target Assets
- Primary: MGC (Micro Gold — FQL's strongest asset, already has intraday strategies)
- This is intentionally gold-only. Gold's squeeze behavior is structurally different from equities (equities have existing squeeze strategies that failed: BBKC PF 0.22-0.57, TTMSqueeze PF 0.43).

## Parameters (initial)
- BB_LEN: 20 (Bollinger Band period)
- BB_MULT: 2.0 (standard deviation multiplier)
- BW_PERCENTILE_LOOKBACK: 120 (days for percentile ranking)
- BW_SQUEEZE_THRESHOLD: 20 (bottom 20th percentile = squeeze)
- MIN_SQUEEZE_BARS: 5 (minimum squeeze duration)
- ATR_LEN: 20
- TRAIL_ATR_MULT: 2.0
- MAX_HOLD_BARS: 20 (time stop)
- VOLUME_FILTER: False (toggle)
- VOLUME_MULT: 1.2

## Source
- John Bollinger: Bollinger BandWidth squeeze framework
- StockCharts ChartSchool documentation
- OpenClaw harvest note: 40_gold_bandwidth_squeeze.md

## Key Failure Mode to Watch
- **Collapsing into generic breakout:** If the squeeze filter is too loose, this becomes just another breakout strategy (MOMENTUM, not VOLATILITY). The squeeze must be genuinely extreme (bottom 20% of 120-day BandWidth range) to differentiate.
- **Equity squeeze precedent:** BBKC Squeeze (PF 0.22-0.57) and TTM Squeeze (PF 0.43) both failed on equity indices. Gold may behave differently because gold squeezes resolve more cleanly due to macro-driven flows, but the equity precedent is cautionary.
- **Head fakes:** Initial breakout direction may reverse (false expansion). The midline cross exit and trailing stop mitigate this, but some losing trades from head fakes are expected.

## Important Notes
- This operates on DAILY bars (resampled from 5m internally), same as DailyTrend-MGC-Long.
- Gold already has 4 strategies (3 intraday + 1 daily trend). Adding a 5th requires clear factor differentiation — this is VOLATILITY, not MOMENTUM.
- The vol compression signal is fundamentally different from the trend/momentum signal that DailyTrend-MGC-Long uses. DailyTrend enters on Donchian breakouts in trending markets; this enters on BandWidth expansion after compression regardless of trend.

## Diversification Role
- **Factor:** VOLATILITY — compression → expansion regime signal, not price momentum
- **Asset:** MGC (gold) — adding vol dimension to an asset where we have momentum + mean reversion
- **Horizon:** Daily bars (multi-day hold, 5-20 days)
- **Correlation to existing MGC strategies:** Should be low — fires during compression periods when trend strategies are dormant (no trend = no Donchian breakout)
- **Expected contribution:** Fills the VOLATILITY factor gap (0 primary strategies). Adds returns during quiet gold periods when momentum strategies sit idle.
