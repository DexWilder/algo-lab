# Harvest Batch 2 — Targeted MES/MNQ Index Strategies

*Date: 2026-03-09*
*Goal: Find non-gold edge for portfolio diversification*

---

## Harvest Parameters

| Parameter | Value |
|-----------|-------|
| Target assets | MES, MNQ (index futures) |
| Excluded families | Generic VWAP, mean reversion (proven dead on indices) |
| Target families | Session trend, volatility compression, trend following, range expansion |
| Source | TradingView open-source scripts + GitHub |
| Batch size | 15 candidates |

---

## Why This Harvest

Batch 1 (76 scripts) was asset-agnostic. Conversion testing proved:
- All edges concentrate in gold (MGC)
- VWAP mean reversion fails on all assets
- ORB breakout marginal on indices after costs
- Gap momentum fails on MES/MNQ completely

Index futures require different strategy DNA: session-based trend following, volatility compression breakouts, and momentum systems designed for mean-reverting microstructure with occasional trend days.

---

## Candidates Harvested

### Session Trend Following (4)

| # | ID | Title | Author | AF | Source |
|---|-----|-------|--------|-----|--------|
| 1 | idx-001-exlux-vix-channel | NY VIX Channel Trend US Futures Day Trade Strategy | exlux | 5 | [TradingView](https://www.tradingview.com/script/TlOcVraF-NY-VIX-Channel-Trend-US-Futures-Day-Trade-Strategy/) |
| 2 | idx-002-varuns-ema-rsi-adx | EMA Cross + RSI + ADX Autotrade Strategy V2 | varuns_back | 5 | [TradingView](https://www.tradingview.com/script/e7XQPek8-EMA-Cross-RSI-ADX-Autotrade-Strategy-V2/) |
| 3 | idx-003-jake-ema-sessions | EMA + Sessions + RSI Strategy v1.0 | jake_theboss | 4 | [TradingView](https://www.tradingview.com/script/5DOEFwJx/) |
| 4 | idx-004-traderspost-855ema | 8-55 EMA Crossover NQ Futures Strategy | TradersPost | 5 | [GitHub](https://github.com/TradersPost/pinescript/blob/master/strategies/8-55-EMA-Crossover-NQ-Futures-Strategy.pinescript) |

### Volatility Compression Breakout (5)

| # | ID | Title | Author | AF | Source |
|---|-----|-------|--------|-----|--------|
| 5 | idx-005-orion-vol-breakout | ORION: Hybrid Volatility Breakout Strategy | ana_gagua | 5 | [TradingView](https://www.tradingview.com/script/6xLkMWMC-ORION-Hybrid-Volatility-Breakout-Strategy/) |
| 6 | idx-006-chenzy-vol-expansion | Volatility Expansion Breakout | ChenzyForex | 4 | [TradingView](https://www.tradingview.com/script/zhEefWDB-Volatility-Expansion-Breakout/) |
| 7 | idx-007-lazybear-bbkc-squeeze | Trading Strategy based on BB/KC Squeeze | LazyBear | 5 | [TradingView](https://www.tradingview.com/script/x9r2dOhI-Trading-Strategy-based-on-BB-KC-squeeze/) |
| 8 | idx-008-leafalgo-vol-compress | Volatility Compression Breakout | LeafAlgo | 4 | [TradingView](https://www.tradingview.com/script/Lc8WH9UF-Volatility-Compression-Breakout/) |
| 9 | idx-009-cryptoeason-bb-st-kc | BB Squeeze + SuperTrend + Keltner Channel | CryptoEason4134 | 4 | [TradingView](https://www.tradingview.com/script/yvAeU1bx/) |

### Trend Following / Multi-Timeframe (3)

| # | ID | Title | Author | AF | Source |
|---|-----|-------|--------|-----|--------|
| 10 | idx-010-dropio-mtf-ema-alma | MTF EMA ALMA Strategy with RSI Supertrend | Dropio12 | 4 | [GitHub](https://github.com/Dropio12/MTF-EMA-ALMA-Strategy-with-RSI-Supertrend-and-Advanced-Volume-Delta-Divergence-Visualization) |
| 11 | idx-011-darshak-supertrend-ema | SuperTrend + Fast/Slow EMA Strategy | darshakssc | 4 | [TradingView](https://www.tradingview.com/script/dJDWRnCA-Supertrend-and-Fast-and-Slow-EMA-Strategy/) |
| 12 | idx-012-dearvn-futures-es-nq | ES/NQ Futures Trading Script | dearvn | 3 | [GitHub](https://github.com/dearvn/trading-futures-tradingview-script) |

### Range Expansion / Momentum (3)

| # | ID | Title | Author | AF | Source |
|---|-----|-------|--------|-----|--------|
| 13 | idx-013-dicargo-vol-breakout | Volatility Breakout Strategy (Larry Williams) | Dicargo_Beam | 5 | [TradingView](https://www.tradingview.com/script/vzWeDyXd-Volatility-Breakout-Strategy/) |
| 14 | idx-014-revolution-momentum | Momentum Strategy | REV0LUTI0N | 4 | [TradingView](https://www.tradingview.com/script/XhCZbT4b-Momentum-Strategy/) |
| 15 | idx-015-juanc-fvbo-squeeze | BB-Keltner Squeeze Failed Volatility Breakout | juanc2316 | 4 | [TradingView](https://www.tradingview.com/script/KqtrEiQS-Bollinger-Band-Keltner-Squeeze-Failed-Volatility-Breakout/) |

---

## Top 3 Conversion Candidates

### #1: NY VIX Channel Trend (idx-001)

**Why:** Only strategy designed specifically for ES/NQ index futures day trading. Uses VIX-derived implied volatility channel (not arbitrary ATR multiples). Session-anchored at 9:30 AM, one trade per day, deterministic entry/exit. Academic-grade concept (implied move from options pricing).

**Entry:** First window (5-120 min) closes above/below session open → long/short.
**Exit:** VIX channel boundary, TP/SL, or pre-close flatten.
**Parameters:** Window duration, VIX TP/SL factors, exit lead time.
**Complexity:** Medium — need VIX data feed or proxy.

### #2: ORION Hybrid Volatility Breakout (idx-005)

**Why:** Compression → expansion logic is the #1 strategy type that works on index futures. ATR tightness filter + linear regression flatness + squeeze detection. EMA 150 trend filter. Anti-stale box logic (45-bar expiry).

**Entry:** Price breaks compression box in trend direction (above EMA 150 = long, below = short).
**Exit:** R:R target (1:1.9), stop at box opposite side.
**Complexity:** Medium — multiple filters but all deterministic.

### #3: BB/KC Squeeze Strategy (idx-007)

**Why:** LazyBear is a legendary Pine Script developer. Classic squeeze concept (BB inside KC → compression → explosion). Simple, proven logic. SAR trend filter for direction.

**Entry:** BB bands exit KC → volatility expanding → enter in direction of momentum.
**Exit:** SAR reversal or predefined stop.
**Complexity:** Easy — straightforward indicator logic.

---

## Conversion Order

1. **idx-001 (VIX Channel)** — highest index-specificity, most unique logic
2. **idx-005 (ORION)** — best compression→expansion framework
3. **idx-007 (BB/KC Squeeze)** — simplest, fastest to convert and test

If all 3 fail on MES/MNQ, the lab's conclusion strengthens: the current data/engine combination doesn't produce index futures edges, and the gold concentration is a feature, not a bug.

---

## Notes

- None of these strategies existed in Batch 1 (76 scripts). The original harvest was heavily biased toward VWAP and ORB families.
- idx-001 is the only strategy in the entire pipeline that uses volatility index data (VIX) as a primary signal component.
- idx-005 and idx-007 both test the "compression leads to expansion" thesis — if neither works, that family is dead on our data.
- Source code not downloaded yet for any candidate. Need to extract from TradingView/GitHub before conversion.

---
*Harvest Batch 2 completed 2026-03-09*
