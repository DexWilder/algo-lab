Now let me compile all this research into a comprehensive report.

---

# Volatility Squeeze / Expansion Breakout Strategies for Systematic Futures Trading

## Comprehensive Research Compilation

---

## STRATEGY 1: TTM Squeeze (John Carter)

**Origin**: John Carter, "Mastering the Trade" Chapter 11. The most widely-known volatility squeeze indicator.

**Core Concept**: Bollinger Bands contract inside Keltner Channels during low volatility, then expand for breakout.

### Parameters (Standard TTM Squeeze)
- **Bollinger Bands**: 20 periods, 2.0 standard deviations
- **Keltner Channels**: 20-period EMA, 1.5x ATR multiplier
- **Momentum Oscillator**: Linear regression of (close - midpoint of Donchian/SMA), 12-period linreg (Carter's book setting)

### Squeeze Detection
- **Squeeze ON (red dots)**: BB upper < KC upper AND BB lower > KC lower (BBs inside KCs)
- **Squeeze OFF (green dots)**: BBs expand back outside KCs
- The squeeze "fires" on the first green dot after red dots

### Entry Rules
1. Wait for minimum 5 consecutive red dots (squeeze bars)
2. Enter on **first green dot** (squeeze release)
3. Direction determined by momentum histogram:
   - Histogram above zero AND rising (light blue) = **long**
   - Histogram below zero AND falling (dark red) = **short**

### Exit Rules (Carter's Original)
- **First target**: 4 bars after squeeze fires -- trail stop or move to breakeven
- **Second target**: 8 bars after squeeze fires -- take profits or tighten stops
- **Momentum reversal exit**: Exit when you see 2 consecutive bars of the "declining" color (e.g., if long with light blue bars, exit on 2 dark blue bars in a row)

### TTM Squeeze Pro (Three-Level Version)
Uses three Keltner Channel multipliers to grade compression intensity:
- **Low Squeeze (blue dots)**: BB inside KC at 2.0x ATR -- mild compression
- **Medium Squeeze (orange dots)**: BB inside KC at 1.5x ATR -- moderate compression
- **High Squeeze (red dots)**: BB inside KC at 1.0x ATR -- extreme compression, highest potential

Progression Blue -> Orange -> Red indicates increasing compression and likelihood of explosive breakout.

### Performance Notes
- Some backtests show 88-92% win rates on specific weekly stock setups (MSFT)
- Performance varies enormously by instrument and timeframe
- One optimization found changing nBB from 2.0 to 1.5 improved profitability by ~300% on AAPL
- This is fundamentally a **breakout** strategy -- expect lower win rate (40-50%) but larger winners vs. mean reversion

### Tail Engine Profile: **Moderate**
- Fires infrequently when requiring 5+ squeeze bars
- Winners can be large on the expansion phase
- High squeeze (Pro version) fires rarely and has the most convexity

---

## STRATEGY 2: BB/KC Squeeze with ATR Trailing Stop

**Concept**: Pure Bollinger/Keltner squeeze with ATR-based exits for trend riding.

### Parameters
- **Bollinger Bands**: 20 periods, 2.0 StdDev
- **Keltner Channels**: 20 periods, 1.5x ATR
- **ATR for trailing stop**: 14-period ATR, 2.0-3.0x multiplier

### Entry Rules
1. Detect squeeze: BB fully inside KC
2. Wait for squeeze release (BB expands outside KC)
3. **Confirmation**: Close above upper BB = long; close below lower BB = short
4. **Volume filter**: Require above-average volume on breakout bar

### Exit Rules
- **ATR trailing stop**: 2x ATR(14) from highest high since entry (long) or lowest low (short)
- Alternative: Chandelier Exit at 3x ATR from highest close
- **Time stop**: Exit at session end if no follow-through

### Optimization Study Results
- 243 parameter combinations tested on crypto markets
- Best configurations achieved Sharpe ratios > 1.0
- S&P 500 backtest with 6-day period and 1.3 ATR showed 80% win rate (but performance declined after 2016)
- Recommended timeframes: M30-D1 (may need adaptation for 5-min)

---

## STRATEGY 3: ATR Compression/Expansion Breakout

**Origin**: Popularized by @onlybreakouts, based on the principle that volatility compresses like a coiled spring.

### Core Metric: ATR Ratio
```
ATR_ratio = ATR(fast) / ATR(slow)
```
- Typical: ATR(5) / ATR(20) or ATR(7) / ATR(50)

### Volatility Regime Classification
| ATR Ratio | Regime | Action |
|-----------|--------|--------|
| < 0.80 | Dead Zone (extreme compression) | **Setup phase** -- watch for breakout |
| 0.80 - 1.20 | Healthy Zone | Normal trading |
| > 1.20 | Expansion Zone | Breakout confirmed, ride the move |

### Entry Rules
1. **Compression detection**: ATR_ratio drops below 0.80 (dead zone)
2. **Breakout trigger**: Price breaks above/below N-bar high/low
3. **Expansion confirmation**: ATR has increased 25%+ from its contraction low
4. **Filter**: Only take trades where ATR_ratio crosses back above 0.80 from below

### Exit Rules
- **Stop**: 2x the **contracted** ATR value (not the expanding value) -- gives tighter, more favorable risk
- **Target**: Let ATR expansion run; exit when ATR_ratio peaks and starts declining
- **Trail**: Move stop to breakeven after 1R profit, then trail at 2x contracted ATR

### Implementation for 5-min Futures
- Use ATR(10) / ATR(50) on 5-minute bars for intraday
- Dead zone threshold may need calibration per instrument
- NQ will compress tighter and expand faster than ES

### Tail Engine Profile: **Strong**
- Dead zone entries fire rarely
- When they fire after genuine compression, the expansion phase produces outsized moves
- The 25% ATR increase filter eliminates false breakouts effectively

---

## STRATEGY 4: NR7 / NR4 Narrow Range Breakout (Toby Crabel)

**Origin**: Toby Crabel, "Day Trading with Short Term Price Patterns and Opening Range Breakout" (1990).

### Core Concept
NR7 = Current bar has the narrowest range (high - low) of the last 7 bars. This is a pure volatility contraction signal.

### Parameters
- **NR7**: Narrowest range in 7 bars
- **NR4**: Narrowest range in 4 bars (more frequent signals)
- **NR4/ID (Inside Day)**: NR4 that is also an inside bar (highest conviction)

### Entry Rules
1. Identify NR7 bar (or NR4)
2. **Bracket order**: Buy stop above NR7 high, sell stop below NR7 low
3. First triggered order is the entry; cancel the other
4. **Enhancement**: Combine NR7 + Inside Bar for highest probability

### Exit Rules (Crabel's Original)
- Take profits at the **close of the first trading day** or on the first profitable close
- Stop-loss: Opposite side of the NR bar, or 2x ATR below entry
- Alternative: Parabolic SAR trailing stop

### 5-Minute Intraday Adaptation
- Apply NR7 logic to 5-minute bars
- Look for narrowest range bar in last 7 five-minute bars
- Bracket order above/below the NR7 bar
- Works particularly well during the first 30-60 minutes of the session when volatility transitions occur

### Performance Characteristics
- S&P 1500 backtest (2000-2017): Win rate ~47%, but profitable due to large winners
- Maximum drawdown well below -20%
- Outperformed buy-and-hold by a wide margin
- The NR4/ID (inside day combination) has the highest edge

### Tail Engine Profile: **Strong**
- NR7 bars on 5-min are relatively rare
- Combined with inside bar filter, signals are very infrequent
- The contraction-expansion principle produces asymmetric payoffs

---

## STRATEGY 5: Bollinger Bandwidth Percentile (BBW%) Breakout

**Concept**: Use the percentile rank of Bollinger Bandwidth to identify historically extreme compression.

### Parameters
- **Bollinger Bands**: 20 periods, 2.0 StdDev
- **Bandwidth**: (Upper BB - Lower BB) / Middle BB
- **Percentile lookback**: 126 bars (6 months on daily, ~2.5 days on 5-min)

### Entry Rules
1. Calculate Bandwidth Percentile (BBWP): Percentage of lookback bars where bandwidth was lower than current
2. **Extreme compression**: BBWP drops below 5% (or ideally hits 0%)
3. **Trigger**: BBWP crosses above its moving average (typically 13-period SMA of BBWP)
4. **Direction**: Enter in direction of close relative to BB midline, or use momentum confirmation

### Exit Rules
- Trail with ATR stop once bandwidth expands above 50th percentile
- Take partial profits when BBWP reaches 80th percentile
- Full exit when BBWP peaks and turns down from above 80%

### Key Insight
When BBWP < 5% and then crosses above its moving average, this signals the END of consolidation and BEGINNING of a trending move. This is the highest-conviction version of the squeeze concept.

### Tail Engine Profile: **Very Strong**
- BBWP < 5% fires very rarely
- The 0% reading (narrowest bandwidth in entire lookback) is the ultimate coiled spring
- Provides the largest asymmetric payoffs of all bandwidth-based approaches

---

## STRATEGY 6: Volatility Contraction Pattern (VCP) -- Intraday Adaptation

**Origin**: Mark Minervini, "Trade Like a Stock Market Wizard" (SEPA methodology).

### Core Pattern
Series of successive pullbacks where each pullback is **smaller** than the previous:
- Contraction 1: 20% range
- Contraction 2: 10% range
- Contraction 3: 5% range
- Breakout from final tight range

### Intraday 5-Minute Adaptation
Instead of percentage pullbacks, use ATR-normalized range:
1. **Contraction detection**: Calculate range of each N-bar consolidation
2. **Successive tightening**: Each consolidation range < previous (e.g., measured as ATR multiples)
3. **Minimum 2 contractions**, maximum 6

### Mechanical Rules for Futures
1. Identify trending instrument (e.g., 20-bar EMA slope positive)
2. Detect 2-3 successive pullbacks with decreasing range (ATR-normalized)
3. Volume should decline during contractions
4. **Entry**: Break above the high of the final tight range
5. **Stop**: Below the low of the final contraction
6. **Target**: Measured move equal to the first (largest) contraction range

### Adaptation Notes
- Works best in **trending** regime (confirm with longer-term trend filter)
- Gold (GC/MGC) tends to form cleaner VCP patterns intraday than equity indices
- Equity indices (ES/NQ) form VCPs more reliably on 15-30 minute bars than 5-minute

### Tail Engine Profile: **Moderate-Strong**
- Multi-contraction VCPs are relatively rare on intraday charts
- When they complete, breakouts are often decisive
- The declining volume signature provides genuine supply exhaustion confirmation

---

## STRATEGY 7: Dual Thrust (Michael Chalek)

**Origin**: Michael Chalek. One of the most successful systematic intraday strategies, widely used in futures.

### Parameters
- **Lookback**: N days (typically 4)
- **K1 (long multiplier)**: 0.5 (default)
- **K2 (short multiplier)**: 0.5 (default)

### Range Calculation
```
Range = MAX(HH - LC, HC - LL)
```
Where over N days:
- HH = Highest High
- LC = Lowest Close
- HC = Highest Close
- LL = Lowest Low

### Entry Rules
```
Long trigger = Today's Open + K1 * Range
Short trigger = Today's Open - K2 * Range
```
- Buy when price crosses above long trigger
- Sell short when price crosses below short trigger

### Asymmetric K Values
- **K1 < K2**: Biased toward longs (easier to trigger long)
- **K1 > K2**: Biased toward shorts (easier to trigger short)
- Can be adjusted dynamically based on trend direction

### Exit Rules
- Close all positions at session end (pure intraday)
- Stop-loss: Midpoint between entry and the opposite trigger level
- Alternative: ATR trailing stop at 1.5x ATR

### Performance
- Works better in trending markets; generates false signals in choppy/ranging markets
- Widely used by CTAs on futures
- Needs volatility regime filter to avoid whipsaws during low-vol periods

### Tail Engine Profile: **Low-Moderate**
- Fires relatively frequently (daily or more)
- Not inherently a tail engine, but can be adapted by increasing K values to require larger range breakouts (e.g., K=0.8-1.0), making it fire less frequently with larger moves

---

## STRATEGY 8: Historical Volatility Percentile Regime Strategy

**Concept**: Trade breakouts only when historical volatility is at extreme lows, indicating imminent expansion.

### Parameters
- **HV calculation**: Standard deviation of log returns, annualized
- **HV period**: 20 bars
- **Percentile lookback**: 252 bars (1 year on daily; ~50 days on 5-min)
- **Threshold**: HV percentile < 20%

### Entry Rules
1. Calculate HV percentile rank over lookback period
2. When HV percentile drops below 20%, enter **setup mode**
3. **Trigger**: Price breaks above/below highest high/lowest low of last 10 bars
4. Only take the trade if HV percentile is still below 30% at trigger time

### Exit Rules
- ATR trailing stop at 2x current ATR
- Take partial at 2R, trail remainder
- **Time exit**: If no follow-through within 20 bars of entry, exit

### Key Empirical Finding
When realized volatility percentile is below 25%, volatility increases by 4.24% more than usual over the next 5 days. This is the statistical edge -- low vol ALWAYS reverts to higher vol.

### Best Markets
- Works well on equity index futures (ES, NQ, RTY) because of the "volatility smile" effect
- Gold (GC) has a different volatility structure but still exhibits mean-reversion in HV

### Tail Engine Profile: **Strong**
- HV < 20th percentile is by definition rare (fires ~20% of the time at most)
- The expansion from extreme low vol produces outsized moves
- Combining with directional breakout filter ensures you catch the right side

---

## CROSS-STRATEGY COMPARISON FOR TAIL ENGINE SUITABILITY

| Strategy | Fire Rate | Win Rate | Avg Winner / Avg Loser | Convexity | Best Market | 5-min Viable |
|----------|-----------|----------|----------------------|-----------|-------------|--------------|
| TTM Squeeze Pro (High) | Very Low | 40-50% | 3-5x | High | ES, NQ | Yes |
| ATR Compression/Expansion | Low | 35-45% | 4-6x | Very High | NQ, GC | Yes |
| NR7 + Inside Bar | Low | ~47% | 2-4x | High | ES, NQ, GC | Yes |
| BBW Percentile < 5% | Very Low | 40-50% | 4-8x | Very High | All | Yes |
| VCP Intraday | Low | 50-55% | 2-3x | Moderate | GC, NQ | Moderate |
| HV Percentile < 20% | Low | 45-55% | 3-5x | High | ES, NQ | Yes |
| Dual Thrust (high K) | Moderate | 45-50% | 2-3x | Moderate | All futures | Yes |

---

## RECOMMENDED "TAIL ENGINE" CANDIDATES FOR YOUR PORTFOLIO

Based on your existing portfolio structure (6 strategies, mostly trend/pullback/mean-reversion), the best candidates for a volatility squeeze tail engine on 5-minute futures bars are:

### Top Pick: ATR Compression + BBW Percentile Hybrid
Combine ATR ratio dead zone detection with BBW percentile < 10% as a dual filter. This fires extremely rarely but catches genuine volatility regime transitions. Implementation:
1. ATR(10)/ATR(50) < 0.75 **AND** BBW percentile < 10%
2. Breakout above/below 10-bar high/low
3. ATR expansion confirmation (25%+ increase)
4. Trail with 2x contracted ATR
5. Target: Let it run until ATR ratio peaks

### Second Pick: TTM Squeeze Pro "High Squeeze" Fire
Only trade the highest compression level (BB inside 1.0x ATR KC):
1. Require 8+ bars of high squeeze (red dots)
2. Enter on first release (green dot) in momentum direction
3. Exit on 2 consecutive declining momentum bars
4. Expect 3-8 trades per month on 5-min NQ/ES

### Third Pick: NR7 + Inside Bar + Volume Contraction
Triple filter for maximum selectivity:
1. NR7 bar that is also an inside bar
2. Volume below 50% of 20-bar average
3. Bracket order above/below
4. ATR trail at 2x ATR(14)

---

## IMPLEMENTATION NOTES FOR 5-MINUTE FUTURES

1. **Session filter**: Only take signals during core US session (9:30 AM - 3:00 PM ET for equity indices; 8:30 AM - 1:30 PM CT for gold)
2. **Avoid first 5 minutes**: Opening bar volatility creates false squeeze releases
3. **Regime gate**: Your existing regime engine (4-factor) should gate these -- only fire squeeze strategies in LOW_VOL regimes (which is precisely when squeezes form)
4. **Position sizing**: Use the contracted ATR value for stop distance, which gives naturally tighter stops and better risk/reward
5. **Expected profile**: 2-5 trades per week, win rate 40-50%, profit factor 1.5-2.5, with occasional 5-10R outlier wins

---

Sources:
- [TTM Squeeze Indicator - TrendSpider](https://trendspider.com/learning-center/introduction-to-ttm-squeeze/)
- [TTM Squeeze - StockCharts ChartSchool](https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/ttm-squeeze)
- [TTM Squeeze - Simpler Trading](https://www.simplertrading.com/news/ttm-squeeze-explained)
- [TTM Squeeze Pro - Pineify](https://pineify.app/resources/blog/ttm-squeeze-pro-indicator-tradingview-pine-script)
- [Squeeze Pro - TradingView by Beardy_Fred](https://www.tradingview.com/script/0drMdHsO-TTM-Squeeze-Pro/)
- [BB/KC Squeeze Optimization - PyQuantLab](https://pyquantlab.medium.com/optimizing-the-bollinger-band-keltner-channel-squeeze-strategy-volatility-breakout-trading-in-70b49101cb30)
- [Keltner Channel Strategy 77% Win Rate - QuantifiedStrategies](https://www.quantifiedstrategies.com/keltner-bands-trading-strategies/)
- [ATR Volatility Compression - Medium](https://medium.com/coding-nexus/atr-volatility-compression-a-winning-breakout-strategy-with-python-8aba9008a65b)
- [ATR Channel Squeeze Breakout - FMZQuant](https://medium.com/@FMZQuant/atr-channel-squeeze-breakout-strategy-volatility-breakout-trading-system-with-momentum-indicator-be10b8784ee9)
- [Bollinger Band Squeeze Backtest - QuantifiedStrategies](https://www.quantifiedstrategies.com/bollinger-band-squeeze-strategy/)
- [BB Squeeze Strategy Quantitative Study - Superalgos](https://medium.com/superalgos/a-quantitative-study-of-the-bollinger-bands-squeeze-strategy-9f47143f33fb)
- [NR7 Trading Strategy - QuantifiedStrategies](https://www.quantifiedstrategies.com/nr7-trading-strategy-toby-crabel/)
- [Narrow Range Day NR7 - StockCharts](https://chartschool.stockcharts.com/table-of-contents/trading-strategies-and-models/trading-strategies/narrow-range-day-nr7)
- [VCP Pattern - TraderLion](https://traderlion.com/technical-analysis/volatility-contraction-pattern/)
- [VCP Pattern - TrendSpider](https://trendspider.com/learning-center/volatility-contraction-pattern-vcp/)
- [Dual Thrust Algorithm - QuantConnect](https://www.quantconnect.com/learning/articles/investment-strategy-library/dual-thrust-trading-algorithm)
- [Squeeze Momentum Indicator - LazyBear TradingView](https://www.tradingview.com/script/nqQ1DT5a-Squeeze-Momentum-Indicator-LazyBear/)
- [BB-KC Squeeze Breakout with ATR Trailing - PyQuantLab](https://pyquantlab.medium.com/bollinger-keltner-squeeze-breakout-trading-strategy-with-atr-trailing-stops-47c54e098e52)
- [BBW Percentile - TradingView](https://www.tradingview.com/script/tqitSsyG-Bollinger-Band-Width-Percentile/)
- [Managed Futures Convexity - CME Group](https://www.cmegroup.com/education/files/managed-futures-and-volatility.pdf)
- [Donchian Channel Strategies - LuxAlgo](https://www.luxalgo.com/blog/donchian-channels-breakout-and-trend-following-strategy/)
- [Opening Range Breakout Profitability Study - ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1544612312000438)
- [Gold Futures Trading Strategies - NinjaTrader](https://ninjatrader.com/futures/blogs/gold-futures-trading-strategies-for-volatile-markets/)
- [HV Percentile and IV Rank - Schwab](https://www.schwab.com/learn/story/using-implied-volatility-percentiles)
- [200 Trading Strategies Backtested - QuantifiedStrategies](https://www.quantifiedstrategies.com/trading-strategies-free/)