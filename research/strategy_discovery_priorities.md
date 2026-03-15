# Strategy Discovery Priorities — Synthesized Research

**Date**: 2026-03-14
**Sources**: Web research across TradingView, academic papers, quant blogs, trading forums
**Goal**: Grow portfolio from 6 core → 10-12 uncorrelated strategies

## Tier 1: Build Immediately (leverage existing infrastructure)

### 1. TTM Squeeze Breakout (Volatility Expansion Family)
**Why**: Most documented vol expansion setup. BB inside KC = squeeze, first bar outside = fire.
- **Asset**: MGC (gold compresses cleanly), M2K (violent expansion)
- **Logic**: BB(20,2.0) inside KC(20,1.5x ATR) for 6+ bars → first bar outside → enter direction of momentum
- **Exit**: 3x ATR trailing stop, time exit at session end
- **Profile**: Tail engine — fires 2-5x per week, large winners
- **Correlation**: Should be near-zero vs existing strategies (different trigger mechanism)
- **Existing code reuse**: BB infrastructure from bb_equilibrium, ATR from everywhere

### 2. ATR Compression Breakout (Volatility Expansion Family)
**Why**: Simpler than TTM, strong tail engine profile, uses ATR ratio as compression detector.
- **Asset**: M2K (Russell), MNQ
- **Logic**: ATR(5)/ATR(50) < 0.75 (dead zone) → price breaks N-bar high/low → ATR increases 25%+ → enter
- **Exit**: 2x contracted ATR stop, trail at 2x contracted ATR after 1R
- **Profile**: Very strong tail engine — dead zone entries are rare and explosive
- **Key insight**: Use the contracted ATR for stops = tighter risk, better R:R

### 3. IBS Mean Reversion on M2K (Russell-Specific)
**Why**: 78% documented win rate on broad indices. Russell's thin liquidity amplifies overshoots.
- **Asset**: M2K only
- **Logic**: Internal Bar Strength = (Close - Low) / (High - Low). Buy next open when IBS < 0.20, sell when IBS > 0.80
- **Exit**: Close at end of next day, or when IBS reverses
- **Profile**: Workhorse — daily frequency, high win rate, small but consistent edge
- **Note**: This is a daily-timeframe strategy, different from our 5m intraday focus. Could run as a separate overlay.

### 4. ORB + VIX Filter Enhancement (ORB Family Extension)
**Why**: Research shows high VIX (>25) produces negative ORB expectancy. Adding this filter to ORB-MGC-Long is free improvement.
- **Asset**: MGC (existing), extend to M2K
- **Logic**: Skip ORB entries when VIX > 25. Widen targets when VIX 15-25 (trending).
- **Profile**: Enhancement to existing strategy, not a new one
- **Need**: VIX data feed (can use VX futures or daily VIX close)

## Tier 2: Build Next (new families, more research needed)

### 5. NR7 Narrow Range Breakout (Toby Crabel)
**Why**: Classic vol contraction signal. Narrowest 5m bar in last 7 → bracket order.
- **Asset**: M2K, MNQ
- **Logic**: Identify NR7 bar → buy stop above high, sell stop below low → first triggered = entry
- **Exit**: 2x ATR stop, close at session end
- **Profile**: Moderate frequency, pairs well with squeeze strategies

### 6. Gap Fill Fade on M2K (Russell-Specific)
**Why**: 76% of RTY gaps fill during RTH. When overnight session fades gap, fill rate = 83%.
- **Asset**: M2K
- **Logic**: Measure overnight gap (RTH close to RTH open). If gap > threshold → fade toward fill. Overnight midpoint predicts direction (76% accuracy).
- **Exit**: Target = gap fill level, stop = 1.5x ATR
- **Profile**: 1 trade per day max, structural edge (institutional rebalancing)

### 7. Pre-FOMC Drift (Event-Driven)
**Why**: Academically documented by NY Fed. Only 8 trades/year but Sharpe 1.14.
- **Asset**: MES or MNQ (S&P/Nasdaq most liquid)
- **Logic**: Buy at 2 PM day before FOMC, sell 15 min before announcement
- **Exit**: Time-based exit, no stop (or wide 3x ATR stop)
- **Profile**: Ultra-rare tail engine — 8 trades/year, but consistent positive drift
- **Caveat**: Edge has weakened since 2016 for meetings with press conferences

### 8. BBW Percentile Breakout (Advanced Volatility Expansion)
**Why**: Most selective squeeze filter — only fires when bandwidth is at historical extreme (<5th percentile).
- **Asset**: M2K, MGC
- **Logic**: BBW percentile < 5% → wait for BBWP to cross above its 13-bar SMA → enter in momentum direction
- **Exit**: Trail with ATR, take profits when BBWP > 80%
- **Profile**: Very strong tail engine — fires very rarely, largest asymmetric payoffs

## Tier 3: Future Consideration

### 9. Dual Thrust (Michael Chalek)
- Widely used by CTAs, but fires frequently and needs regime filter
- Better suited as a daily strategy

### 10. VCP Intraday (Minervini Adaptation)
- Multi-contraction patterns are rare on 5m bars
- Gold forms cleaner VCPs than equity indices
- Complex to detect mechanically

### 11. Event Day Meta-Layer
- Not a strategy per se — a controller enhancement
- Pause all strategies during event windows, widen stops, reduce size
- Implement as strategy_controller enhancement after freeze lifts

### 12. Russell Reconstitution Seasonal
- Only fires once per year (June 23 → July 1)
- 1.34% avg gain over 6 days, consistent since 1988
- Now semi-annual (December window added)
- Very low priority for algo system

## Implementation Order

| Priority | Strategy | Family | Asset | Correlation Risk | Build Effort |
|---|---|---|---|---|---|
| 1 | TTM Squeeze Breakout | vol_expansion | MGC/M2K | Low (new trigger) | Medium |
| 2 | ATR Compression Breakout | vol_expansion | M2K/MNQ | Low (new trigger) | Low |
| 3 | ORB + VIX Filter | breakout (existing) | MGC | N/A (enhancement) | Low |
| 4 | Gap Fill Fade M2K | mean_reversion | M2K | Low (daily/overnight) | Medium |
| 5 | NR7 Breakout | vol_expansion | M2K/MNQ | Med (similar to squeeze) | Low |
| 6 | BBW Percentile Breakout | vol_expansion | M2K/MGC | Med (BB-based) | Medium |
| 7 | Pre-FOMC Drift | event_driven | MES/MNQ | None (calendar-based) | Low |

## Portfolio Impact Projection

Adding 4 uncorrelated strategies (Tier 1) to the current 6 would:
- Increase strategy count to 10 (target range)
- Fill volatility expansion gap completely
- Add M2K-specific edges (leveraging confirmed microstructure)
- Improve portfolio Sharpe by ~30% (sqrt(10/6) = 1.29)
- Reduce single-asset concentration (MNQ currently 46% of PnL)
