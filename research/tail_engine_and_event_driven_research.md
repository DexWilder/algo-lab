# Tail Engine & Event-Driven Strategy Research
## Compiled 2026-03-14

---

# PART 1: TAIL ENGINE STRATEGIES (Low Frequency, High Convexity)

## Philosophy
The core idea: **lose small, win big**. Win rates hover below 50% but the payoff asymmetry (many scratches, a few home runs) creates convexity that compounds over time. Risk management IS the strategy — not an add-on.

---

## Strategy T1: Turtle Trading System (Modernized for Intraday Futures)

### Original Rules (Richard Dennis, 1983)
**System 1 (Short-term):**
- **Entry**: Buy when price hits a NEW 20-day high; short when price hits a NEW 20-day low
- **Exit**: Close longs at 10-day low; close shorts at 10-day high
- **Stop**: 2N below entry for longs (2N = 2x 20-period ATR)
- **Position Sizing**: Unit = (1% of equity) / (N x dollar-per-point). Risk 1% per unit.
- **Pyramiding**: Add 1 unit for every 0.5N move in your favor. Max 4 units per market.
- **Skip rule**: System 1 skips entry if the previous breakout was a winner (captures bigger moves by waiting for System 2)

**System 2 (Long-term):**
- **Entry**: Buy at 55-day high; short at 55-day low
- **Exit**: Close longs at 20-day low; close shorts at 20-day high
- **Stop**: Same 2N stop
- **No skip rule**: Always take System 2 signals

### Modern Adaptations for Intraday Futures
- Replace 20-day with 20-bar on 5m/15m charts (equivalent concept)
- Add moving average alignment filter (e.g., 50-bar EMA direction must confirm breakout direction)
- Tighten stop from 2N to 1.5N with trailing stops
- Add volatility regime filter: reduce position size or skip trades during HIGH volatility (inverse of original)
- Use ATR-normalized range rather than fixed N-day lookback

### Expected Performance
- **Win rate**: 30-40% (structural for trend-following)
- **Profit factor**: 1.5-2.5 when trends are present
- **Trade frequency**: 2-5 trades per week on 5m bars, much less on daily
- **Best markets**: Trending futures — NQ, ES, GC, CL, currencies
- **Why the edge exists**: Behavioral — humans cut winners and hold losers. Mechanical trend-following does the opposite. Markets have fat tails (more extreme moves than normal distribution predicts).

---

## Strategy T2: Donchian Channel Extreme Breakout

### Mechanical Rules
**Entry:**
- Long: Price closes above the highest high of the last N bars (N = 50 or 100 for "extreme" variant)
- Short: Price closes below the lowest low of the last N bars
- Filter: Only enter if 14-period ATR > 50-period MA of ATR (ensures market is volatile enough to sustain breakout)

**Exit:**
- Use a shorter Donchian channel for exit (e.g., 20-bar low for longs, 20-bar high for shorts)
- OR ATR trailing stop at 2-3x ATR

**Position Sizing:**
- Risk 1-2% per trade, sized by ATR distance to stop

### Backtesting Results (from multiple sources)
- **Tested**: E-mini S&P 500, Crude Oil, Nasdaq 100, Gold Futures — all profitable
- **Win rate**: ~45% (unusually high for trend-following; typical is 30-35%)
- **Test period**: 1990-2025 (35 years) on Nasdaq and Gold
- **Key finding**: Outperforms dramatically during trending periods; underperforms in sideways markets
- **ATR filter impact**: Profit factor improves ~40% when filtering out low-volatility environments
- **15-year futures backtest**: 20 US futures markets (currencies, commodities, financials) — profitable

### Why the Edge Exists
- Longer lookback (50-100 bars) filters out noise and only fires on genuine regime changes
- Captures the biggest moves while avoiding choppy breakout failures
- Volatility filter ensures sufficient momentum exists to sustain the move

### Best Markets
- Nasdaq 100 (NQ/MNQ), Gold (GC/MGC), Crude Oil (CL/MCL), currencies, bonds

---

## Strategy T3: ATR Volatility Compression Breakout

### Mechanical Rules
**Setup (Volatility Compression Detection):**
- Current 14-period ATR < 50-period MA of ATR (market is compressed/quiet)
- ADX < 20 (no trend present = coiled spring)
- Wait for compression to resolve

**Entry:**
- When a candle's range exceeds 2x the current ATR AND closes beyond key support/resistance
- Enter in the direction of the breakout
- Alternative: Price exceeds previous resistance/support by at least 1 ATR

**Stop Loss:**
- 1.5-3.0x ATR from entry (popular range)
- Placed on opposite side of the compression zone

**Exit:**
- Trailing stop at 2x ATR
- OR fixed R:R target of 3:1 or 4:1

**Timeframe:** 60-minute bars work well for E-mini Nasdaq 100

### Expected Performance
- **Win rate**: 35-45%
- **Profit factor**: 1.8-2.5 (when properly filtered)
- **Trade frequency**: 1-3 trades per week on 60m bars
- **Key insight**: Simple breakout logic shows strong potential but produces many trades; in low-volatility environments, fees and slippage reduce performance. The compression filter is essential.

### Why the Edge Exists
- Volatility is mean-reverting: periods of low volatility predict periods of high volatility
- Compression followed by expansion is a structural market phenomenon
- The filter eliminates 40%+ of losing trades by avoiding trades in already-expanded environments

---

## Strategy T4: Crisis Alpha / Systematic Trend Following (CTA-Style)

### How Institutional Funds Do It (AQR, Man AHL, Winton)

**Signal Generation:**
- Multiple lookback periods combined: typically 1-week, 1-month, 3-month, 6-month, 12-month momentum
- Signal types: Moving average crossovers (Man AHL uses double exponential MA crossovers), breakout signals, price-minus-MA, total return momentum
- Signals from each timeframe are weighted (often equal-weighted to prevent overfitting) and combined into a composite signal

**Universe:**
- 50-100+ liquid futures and FX forwards
- Asset classes: equities, fixed income, currencies, commodities
- Equal risk allocation across asset classes

**Position Sizing:**
- Volatility targeting: each position sized so it contributes equal risk
- Typically target 10-15% annual portfolio volatility
- Position size = (target risk per position) / (ATR x point value)

**Risk Management:**
- Risk control is "the beating heart of the strategy"
- Fast reduction in exposure to crisis markets (under 15 days per research)
- Portfolio-level correlation monitoring

### Man AHL Specifics
- Suite of double exponentially weighted MA crossover models (in use ~30 years)
- Mix of MA crossovers and breakout momentum signals
- Holding period approximately 3 months (medium-frequency)
- Faster trading speeds = more convexity during crises but lower average returns
- Slower models have seen less Sharpe ratio decline over time

### Performance Characteristics
- **Crisis alpha**: During equity market crashes, trend followers profit by being short equities and/or long bonds/gold
- **Convexity**: Non-linear payoff in both extreme left and right tails of equity returns
- **Diversification**: Positive yields in gaining markets counterbalance poor performance in crisis markets
- **CTA crisis alpha mechanism**: Diversification across markets + fast exposure reduction (<15 days)
- **Sharpe ratio**: 0.5-1.0 historically for diversified CTA strategies
- **Correlation to equities**: Near zero on average, strongly negative during equity drawdowns

### Adaptation for Small-Scale (Single Futures)
- Use 3 lookback periods: 10-bar, 30-bar, 60-bar momentum on 5m or 15m bars
- Combine signals: take trade only when 2 of 3 timeframes agree on direction
- ATR-based position sizing with 1% risk per trade
- Trailing stop at 2.5x ATR
- This creates the multi-timeframe convex profile at intraday scale

---

## Strategy T5: N-Day High/Low Breakout with Volatility Filter

### Mechanical Rules
**Entry:**
- Long: Price breaks above highest high of last N days (N = 7, 10, 20, or 55)
- Short: Price breaks below lowest low of last N days
- FILTER 1: 14-period ATR > 50-period MA of ATR (volatility is expanding)
- FILTER 2 (optional): ADX > 25 (trending environment confirmed)

**Exit:**
- Shorter channel exit: Close at M-day low/high (M = N/2, e.g., 10-day exit for 20-day entry)
- Time exit: Close after 2x N bars if no stop/target hit
- Trailing stop: 2x ATR

**Position Sizing:**
- Unit = (2% of equity) / (N-value x dollar-per-point)

### Performance by Lookback Period
| Lookback | Frequency | Win Rate | Best For |
|----------|-----------|----------|----------|
| 7-day | High (~daily) | 35-40% | Short-term momentum |
| 20-day | Medium (~weekly) | 40-45% | Standard trend capture |
| 55-day | Low (~monthly) | 45-50% | Major trend changes |
| 100-day | Very low | 50%+ | Only mega-trends |

### Why the Edge Exists
- Channel breakout captures the asymmetry of market returns (fat tails)
- Volatility filter dramatically improves signal quality (40% profit factor improvement)
- Markets exhibit momentum: new highs tend to lead to more new highs

---

## Strategy T6: Gap-and-Go / Gap Fade for Futures

### Gap-and-Go (Momentum Continuation)
**Entry:**
- Gap up > 0.5% from prior close at open
- Wait for first 1-minute candle to establish direction
- Enter long if 1-min candle closes above premarket high with volume confirmation
- Enter short for gap down below premarket low

**Stop:** Just below the opening candle low (for longs)
**Target:** 2:1 R:R minimum; trail with 1-min candle structure
**Time Exit:** Close by 1 PM ET (gap dynamics exhausted by then)

### Gap Fade (Mean Reversion)
**Entry:**
- Buy at market open AGAINST the gap direction
- Exit when price retraces to yesterday's close (the "gap fill")
- R:R is 1:1 by definition

**Performance:**
- Common gaps fill 90% of the time within 1-3 days in active instruments
- Range-bound markets: 70-80% fill probability
- Strong trending markets: only 40-60% fill probability
- **WARNING**: Gap strategies have degraded significantly — used to be "low-hanging fruit" but no longer easy edge in major indices
- Very large gaps (> 0.7%) have NEGATIVE expectancy when faded (-0.11% per trade)

### Best Application for Algo Lab
- Gap-and-Go works better than Gap Fade in current markets
- Best on gold futures (MGC) which gap more cleanly than equity indices
- Combine with volatility filter: only trade gaps on days when ATR is above average

---

## Strategy T7: Opening Range Breakout (ORB)

### Mechanical Rules (Best Performing Variants)

**15-Minute ORB:**
- Define opening range: High and Low of first 15 minutes after market open (9:30-9:45 ET)
- **Long**: Enter when a 5-min candle CLOSES above the opening range high
- **Short**: Enter when a 5-min candle CLOSES below the opening range low
- **Stop**: Opposite side of the opening range
- **Target**: 1.5x the opening range size (first target), 3.0x for runner
- **Max 1 trade per day per direction; no re-entries after stop-out**

**VIX-Adjusted Rules:**
| VIX Level | Stop | Target 1 | Target 2 | Expected Win Rate |
|-----------|------|----------|----------|-------------------|
| < 15 (low) | 0.5x range | 1.5x range | 3.0x range | 62% |
| 15-25 (medium) | 1.0x range | 1.5x range | 2.0x range | 55% |
| > 25 (high) | SKIP | SKIP | SKIP | Negative expectancy |

### Backtesting Results
- **5-min ORB on NQ**: 433% profit on $10K account in 1 year, nearly doubled 15-min version returns, cut max drawdown in half
- **15-min ORB**: 114 trades, 74.56% win rate, profit factor 2.512, max DD $2,725 (12%)
- **60-min ORB**: Highest win rate at 89.4%, profit factor 1.44 (smaller wins but very consistent)

### Why the Edge Exists
- Institutional order flow concentrates at the open; the opening range captures the equilibrium zone
- Breakout from this zone signals one-sided institutional flow
- VIX filter is crucial: high-VIX environments produce whipsaws that destroy the edge

---

## Strategy T8: Initial Balance (IB) Breakout — Gold Specialty

### Mechanical Rules
**Setup:**
- Initial Balance = High and Low of the first 60 minutes of trading
- Wait for price to break beyond the IB range
- Do NOT trade the breakout directly — wait for a retracement

**Entry:**
- After IB breakout, enter in the breakout direction at 25% of IB range INSIDE the IB
- Example: IB range = 40 points, breaks down. Entry = IB low + 10 points (25% retrace)

**Stop Loss:**
- 60% of IB range from entry
- Example: If IB range = 40, stop = 24 points from IB boundary

**Target:**
- 50% of IB range BEYOND the IB boundary
- Example: IB range = 40, target = IB low - 20 (for shorts)

**Time Exit:** Close at end of session if neither stop nor target is hit

### Backtesting Results (Gold Futures)
- **Period**: Jan 2025 - Jan 2026
- **Return**: 121% in 3 months on $10K account (1 contract)
- **Win rate**: ~50%
- **Average winner**: ~2x average loser (2:1 reward-to-risk)
- **Trade frequency**: 1 trade per day
- **Includes commissions**: Yes

### Why the Edge Exists
- Gold mean-reverts cleanly intraday (confirmed in your own research)
- IB establishes a value area; breakout + retest creates a high-probability entry
- The retracement entry avoids false breakouts and improves R:R

---

# PART 2: EVENT-DRIVEN SYSTEMATIC STRATEGIES

## Philosophy
Scheduled economic events create PREDICTABLE volatility patterns. The edge is not in predicting direction but in trading the STRUCTURE: pre-event drift, post-event momentum, and volatility crush. These are calendar-based, low-frequency strategies that fire 8-12 times per year.

---

## Strategy E1: Pre-FOMC Announcement Drift

### The Anomaly (NY Fed Research)
Since 1994, the pre-FOMC drift has accounted for **over half of total annual excess stock market returns**. The probability of finding such large returns by chance is < 0.02%.

### Mechanical Rules
**Entry:** Buy SPX/ES at 2:00 PM ET the day BEFORE a scheduled FOMC announcement
**Exit:** Sell 15 minutes BEFORE the FOMC announcement (typically 1:45 PM ET on announcement day)
**Holding period:** ~24 hours
**Instruments:** ES/MES futures, SPY, or 3x leveraged ETFs

### Backtesting Results
- **CAGR**: ~4% per year (on SPX), 8-9% using 3x leveraged ETFs
- **Sharpe ratio**: 1.14 (for the 2pm-to-pre-announcement variant), 0.5-0.6 for close-to-close
- **Trades per year**: 8 (one per FOMC meeting)
- **Only trades 5% of all trading days**
- **The drift does NOT reverse post-announcement** — it's real positioning, not noise
- **Cross-country**: Statistically significant in US, UK, France, Switzerland (29-52 bps per event)

### Recent Status
- Has WEAKENED since 2016 in meetings with press conferences
- Still present in meetings WITHOUT press conferences
- Reduced uncertainty about Fed policy has compressed the premium

### Why the Edge Exists
- Institutional pre-positioning ahead of uncertainty resolution
- Risk premium that gets priced in as event approaches
- Three waves of institutional money create drift: HFT (instant), fast discretionary (minutes), slow institutional (hours to days)

---

## Strategy E2: CPI Release Day Trading

### Mechanical Rules (Conservative)
**Pre-CPI Setup:**
- 8:30 AM ET release time — this is UNTRADEABLE for the first 90 seconds
- 8:30-8:31:30: Spreads blow out, 100-200 point NQ swings in first minute
- 8:31:30-9:00: High-volatility reaction window — pause automation entirely
- 9:00-10:00: Stabilization period — gradually resume with modified parameters

**CPI Day Adjustments for Existing Strategies:**
- Widen stop losses by 50-100%
- Reduce position sizes by 30-50%
- DISABLE mean-reversion strategies
- Only run trend-following/breakout strategies

**Post-CPI Momentum Strategy:**
- Wait until 9:30 AM ET (regular session open)
- Enter in the direction of the initial CPI move IF it was a significant surprise
- Surprise threshold: Core CPI y/y >= 0.3 percentage points above/below consensus
- No threshold met = no trade
- Stop: 2x normal ATR stop
- Target: 3:1 R:R or trail with ATR

### Backtest (QuantifiedStrategies.com)
- Buying S&P 500 at the open on CPI day and selling at close: average gain 0.09%
- Holding beyond CPI day shows no edge (-0.04% after 5 days)
- **Key insight**: CPI is a same-day trade, not a swing trade

### Why the Edge Exists
- CPI surprises force rapid repricing of rate expectations
- Three waves of institutional reaction create a tradeable drift (same structure as FOMC)
- Sustained directional moves when CPI significantly surprises

---

## Strategy E3: NFP (Non-Farm Payroll) Day Trading

### Mechanical Rules
**Pre-NFP (First Friday of each month, 8:30 AM ET):**
- DO NOT hold positions through the release — it's gambling (bid-ask spread widens massively)
- Wait for announcement, then wait 2+ minutes for spreads to normalize

**Post-NFP Pullback Strategy:**
- Wait for the initial NFP spike/drop (first 5-15 minutes)
- Wait for a pullback/retracement (50% of the initial move is common)
- Enter in the direction of the initial move on the pullback
- Stop: Beyond the pre-NFP price level
- Target: 2:1 R:R minimum

**Alternative — Buy-at-Open Strategy:**
- Average open-to-close gain on NFP day: 0.09% (very small, barely tradeable)
- NOT recommended as a standalone strategy

### Why the Edge Exists
- NFP creates forced repositioning by institutional money
- The pullback pattern occurs because initial reaction overshoots, then continuation occurs as slower institutional money enters

---

## Strategy E4: Post-Event Volatility Crush

### The Mechanism
- VIX consistently DECREASES on FOMC meeting days, regardless of content
- Falling volatility triggers Vanna flows: options dealers must buy S&P futures to reduce hedges
- This creates a reflexive upward push in equity prices

### Mechanical Rules (Futures Version — No Options Needed)
**Setup:**
- VIX is elevated (> 20) heading into a scheduled event (FOMC, CPI, NFP)
- This signals the market has priced in uncertainty that will resolve

**Entry:**
- Buy ES/MES at the close of the event day (after announcement)
- OR buy at 2:00 PM ET on announcement day (after initial reaction settles)

**Exit:**
- Hold for 1-3 days
- Target: Capture the vol-crush rally as VIX normalizes
- Stop: Below the event-day low

**With Options (More Convex):**
- Sell Iron Condors BEFORE the event when IV is elevated
- Sell both call spread and put spread outside the expected move
- Let IV crush do the work — profit when vol drops and price stays in range
- Average return: ~10% per event on the vol crush trade

### Why the Edge Exists
- Uncertainty premium gets priced into options/VIX before events
- Resolution of uncertainty (regardless of outcome) removes premium
- Vanna flows create mechanical buying pressure

---

## Strategy E5: Event Calendar Master Strategy

### Systematic Event Schedule (Annual Calendar)
| Event | Frequency | Time (ET) | Typical NQ Impact |
|-------|-----------|-----------|-------------------|
| FOMC Rate Decision | 8x/year | 2:00 PM | 50-200 pts |
| CPI Release | 12x/year | 8:30 AM | 100-300 pts |
| NFP Release | 12x/year | 8:30 AM | 50-150 pts |
| GDP Release | 4x/year | 8:30 AM | 30-100 pts |
| PPI Release | 12x/year | 8:30 AM | 30-80 pts |
| PCE (Fed's preferred) | 12x/year | 8:30 AM | 50-150 pts |
| ISM Manufacturing | 12x/year | 10:00 AM | 30-80 pts |
| FOMC Minutes | 8x/year | 2:00 PM | 30-100 pts |

### Master Rules for Event Days
1. **Pre-event (T-24h to T-1h)**: Run pre-FOMC drift strategy if applicable
2. **Event window (T-5min to T+30min)**: ALL strategies paused. No trading.
3. **Post-event reaction (T+30min to T+2h)**: Run breakout/momentum strategies with widened stops
4. **Post-event stabilization (T+2h to close)**: Resume normal strategies with vol-adjusted parameters
5. **T+1 day**: Run vol-crush strategy if VIX was elevated

### Surprise Threshold Framework
- **No surprise** (within consensus): No event trade. Resume normal strategies faster.
- **Moderate surprise** (1-2 std dev from consensus): Take breakout trade with 2:1 R:R
- **Major surprise** (>2 std dev): Take breakout trade with 3:1+ R:R, expect multi-day drift

---

# PART 3: BARBELL PORTFOLIO ARCHITECTURE

## Concept (Nassim Taleb / Universa Investments)
Allocate capital to two extremes with nothing in the middle:
- **70-90% Safe Side**: Low-risk, capital-preserving strategies (your current portfolio of MR + momentum strategies)
- **10-30% Convex Side**: High-risk, high-convexity tail strategies that lose small but occasionally win massive

## Implementation for Algo Lab
- **Safe side (80%)**: Current v0.17 portfolio (VWAP, XB-PB-EMA, ORB-MGC, BB-EQ, PB-MGC, Donchian)
- **Convex side (20%)**: Tail engine strategies from this research
  - Extreme Donchian breakout (50-100 bar lookback)
  - Event-driven FOMC/CPI strategies
  - ATR compression breakout
  - Gap-and-Go on extreme gaps only

## Key Principle
The convex side WILL lose money most of the time. Budget for it. The purpose is to produce massive returns during regime changes that offset drawdowns in the safe side.

---

# PART 4: IMPLEMENTATION PRIORITY FOR ALGO LAB

## Tier 1 — Highest Conviction (Implement First)
1. **Extreme Donchian Breakout (T2)** — You already have Donchian infrastructure. Widen lookback to 50-100 bars, add ATR filter. Low effort, high potential.
2. **ORB with VIX Filter (T7)** — You already have ORB-MGC-Long. Add VIX-based parameter adjustment. Massive backtest results (400%+ returns, 74% win rate).
3. **IB Breakout Gold (T8)** — Gold is your strongest asset. IB breakout is proven on gold specifically. 121% in 3 months, 1 trade/day.
4. **Pre-FOMC Drift (E1)** — 8 trades/year, 1.14 Sharpe, well-documented anomaly. Easy to implement.

## Tier 2 — Strong Evidence (Implement Second)
5. **ATR Compression Breakout (T3)** — Volatility compression -> expansion is structural. Good complement to existing strategies.
6. **Event Day Master Rules (E5)** — Not a new strategy but a meta-layer: pause/adjust existing strategies around events. Reduces drawdowns.
7. **Post-Event Vol Crush (E4)** — Simple buy-after-event when VIX was elevated. 8-12 trades/year.

## Tier 3 — Worth Testing (Implement Third)
8. **Multi-Timeframe Trend (T4)** — CTA-style signal combination across 3 lookback periods. More complex but structurally sound.
9. **CPI Momentum (E2)** — Post-surprise continuation trade. Harder to automate (need surprise threshold data).
10. **Gap-and-Go (T6)** — Edge has degraded in equities. May still work on gold.

---

# SOURCES

## Tail Risk & Convexity
- [Trend-following for tail-risk hedging and alpha generation — Artur Sepp](https://artursepp.com/2018/04/24/trend-following-strategies-for-tail-risk-hedging-and-alpha-generation/)
- [The crisis alpha of managed futures — ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1057521922000242)
- [Convexity: A Powerful Approach to Tail Risk Hedging — GIA](https://www.gia.com/wp-content/uploads/2022/03/Convexity-A-Powerful-and-Customizable-Approach-to-Tail-Risk-Hedging.pdf)
- [The Convexity of Trend Following — Hedge Fund Journal](https://thehedgefundjournal.com/the-convexity-of-trend-following/)
- [Creating Portfolio Convexity: Trend vs Options — Man Group](https://www.man.com/insights/creating-portfolio-convexity)
- [Nassim Taleb Barbell Strategy — QuantifiedStrategies](https://www.quantifiedstrategies.com/nassim-taleb-strategy/)

## Turtle Trading & Donchian
- [Richard Dennis Turtle Trading Rules — TrendSpider](https://trendspider.com/learning-center/richard-dennis-turtle-trading-strategy/)
- [Modern Turtle Trading Strategy Updated Rules — TOS Indicators](https://tosindicators.com/research/modern-turtle-trading-strategy-rules-and-backtest)
- [The Original Turtle Trading Rules PDF](https://oxfordstrat.com/coasdfASD32/uploads/2016/01/turtle-rules.pdf)
- [Donchian Channel Breakout Strategy — Algomatic Trading](https://algomatictrading.substack.com/p/strategy-8-the-easiest-trend-system)
- [Donchian Channel Strategies — QuantifiedStrategies](https://www.quantifiedstrategies.com/donchian-channel/)

## Opening Range & Initial Balance
- [ORB Strategy up 400% — Trade That Swing](https://tradethatswing.com/opening-range-breakout-strategy-up-400-this-year/)
- [Initial Balance Breakout Gold — Trade That Swing](https://tradethatswing.com/one-trade-a-day-gold-strategy-411-in-last-year-fully-automatable/)
- [Opening Range Breakout Strategy — QuantifiedStrategies](https://www.quantifiedstrategies.com/opening-range-breakout-strategy/)
- [VIX-Based ORB Strategy — TOS Indicators](https://tosindicators.com/research/vix-opening-range-breakout-orb-strategy-thinkorswim)
- [Initial Balance Breakout Strategy — Market Profile Info](https://marketprofile.info/articles/initial-balance-breakout-strategy)

## Volatility Breakout
- [Day Trading Volatility Breakouts Systematically — Cracking Markets](https://www.crackingmarkets.com/day-trading-volatility-breakouts-systematically-all-rules-included/)
- [ATR Volatility Compression Breakout — Medium](https://medium.com/coding-nexus/atr-volatility-compression-a-winning-breakout-strategy-with-python-8aba9008a65b)
- [Intraday Volatility Breakout Blueprint — Cracking Markets](https://www.crackingmarkets.com/intraday-volatility-breakout-blueprint/)

## Event-Driven & FOMC
- [The Pre-FOMC Announcement Drift — NY Fed](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr512.pdf)
- [Trading the Fed: Pre-FOMC Drift is Alive — QuantSeeker](https://www.quantseeker.com/p/trading-the-fed-the-pre-fomc-drift)
- [Post-Event Vol Crush — Systematic Individual Investor](https://systematicindividualinvestor.com/2021/09/28/a-market-edge-post-event-vol-crush/)
- [CPI Trading Strategy — QuantifiedStrategies](https://www.quantifiedstrategies.com/cpi-trading-strategy/)
- [NFP Trading Strategy — QuantifiedStrategies](https://www.quantifiedstrategies.com/nfp-trading-strategy/)
- [NQ Futures CPI Automation Adjustments — ClearEdge](https://clearedge.trading/post/nq-futures-cpi-automation-adjustments-guide)
- [Volume dynamics around FOMC — BIS](https://www.bis.org/publ/work1079.pdf)

## Institutional / CTA Research
- [Trend Following: Equity and Bond Crisis Alpha — Man Group](https://www.man.com/insights/trend-following-equity-and-bond-crisis-alpha)
- [AHL Trend-Following: Why/What Sets Us Apart — Man Group](https://ceros.man.com/ahl-trendfollowing-why-trend)
- [Understanding Managed Futures — AQR](https://www.aqr.com/-/media/AQR/Documents/Insights/White-Papers/Understanding-Managed-Futures.pdf)
- [What is Trend Following — Winton](https://www.winton.com/news/what-is-trend-following)
- [Trend Following Primer — Graham Capital](https://www.grahamcapital.com/blog/trend-following-primer/)
- [Managed Futures Understanding — Alpha Architect](https://alphaarchitect.com/managed-futures-understanding-a-misunderstood-diversification-tool/)

## Gap Trading
- [Gap Trading Strategy — QuantifiedStrategies](https://www.quantifiedstrategies.com/gap-trading-strategies/)
- [Gap Fill Strategies Backtest — QuantifiedStrategies](https://www.quantifiedstrategies.com/gap-fill-trading-strategies/)
- [Opening Gap Intraday Patterns — Systematic Individual Investor](https://systematicindividualinvestor.com/2018/05/09/dead-simple-the-opening-gap-and-other-intraday-patterns-around-the-market-opening/)

## Academic Papers
- [Modeling Multifactor Event Driven Trading Strategy — SSRN](https://papers.ssrn.com/sol3/Delivery.cfm/SSRN_ID3683454_code4203724.pdf?abstractid=3683454)
- [Trend Following Strategies: A Practical Guide — SSRN](https://papers.ssrn.com/sol3/Delivery.cfm/5140633.pdf?abstractid=5140633)
- [Disappearing Pre-FOMC Announcement Drift — PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC7525326/)
