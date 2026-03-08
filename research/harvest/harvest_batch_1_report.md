# Harvest Batch 1 — Final Report

**Date:** 2026-03-07
**Batch ID:** harvest_batch_1
**Status:** Complete

---

## 1. Harvest Overview

| Metric | Count |
|--------|------:|
| **Total strategies evaluated** | 108+ |
| **Accepted candidates (TradingView)** | 54 |
| **Accepted candidates (External)** | 22 |
| **Total accepted** | 76 |
| **Rejected candidates** | 32+ |
| **Sources queried** | 7 (TradingView, GitHub, QuantConnect, Quantpedia, FMZ, Research Papers, Blogs) |
| **Duplicates removed** | 3 |
| **Families covered** | 3 (ICT, ORB, VWAP) |
| **External components extracted** | 30 |

### Accepted by Family

| Family | TradingView | External | Total | Target | Hit Rate |
|--------|------------|----------|-------|--------|----------|
| VWAP | 23 | 8 | 31 | 20 | 155% |
| ORB | 18 | 11 | 29 | 20 | 145% |
| ICT | 13 | 3 | 16 | 20 | 80% |
| **Total** | **54** | **22** | **76** | **60** | **127%** |

### Rejection Reasons

| Reason | Count |
|--------|------:|
| Indicator only (no `strategy()` function) | 20 |
| Invite-only / paid / closed source | 3 |
| Duplicate of existing script | 3 |
| Insufficient detail / cannot verify | 2 |
| Author explicitly states not for trading | 1 |
| Wrong family classification | 2 |
| No defined exit logic | 1 |

### External Source Highlights

| Source | Strategies Found | Key Discovery |
|--------|----------------:|---------------|
| GitHub | 12 | `smartmoneyconcepts` pip library — instant ICT detection toolkit |
| QuantConnect | 3 | Zarattini ORB paper (Sharpe 2.81) — proves raw ORB needs filters |
| Research Papers | 3 | IEEE TORB paper — optimal probing time varies by market |
| FMZ | 2 | VWAP + OBV-RSI dual confirmation — best mean reversion setup |
| Blogs | 2 | QuantifiedStrategies proves raw ORB = 0.04% edge (dead without filters) |

### Critical Research Insights from External Sources

1. **Raw ORB is dead.** QuantifiedStrategies proved it: 0.04% avg gain on S&P 500 without filters. The Zarattini paper's Sharpe 2.81 comes entirely from volume-based "Stocks in Play" filtering. For MES futures, equivalent filters (session volatility gate, volume spike, regime detection) are mandatory.

2. **`smartmoneyconcepts` Python library is a breakthrough.** Pip-installable (`pip install smartmoneyconcepts`). Detects FVG, OB, BOS, CHoCH, Liquidity sweeps, Sessions — all from a standard OHLCV DataFrame. Direct integration into our backtest engine for ICT strategy development.

3. **4-phase state machine pattern** (GH-ORB-007, Backtrader Gold pullback). SCANNING→ARMED→WINDOW_OPEN→ENTRY with 6-layer validation. Maps directly to Lucid's pullback entry architecture. PF 1.64, Sharpe 0.89 on Gold.

4. **Dual confirmation is the common thread in winning strategies.** Every successful automated strategy uses 2+ independent confirming signals (VWAP+OBV-RSI, EMA stack+VWAP+RSI, Supertrend+MACD+VWAP).

5. **Mean reversion on futures requires regime awareness.** Every source warns MR fails catastrophically in trends. Volume-based regime filter (OBV-RSI, CTI, ADX) is not optional — it IS the strategy.

### Key Structural Finding: ICT Strategy Gap

The ICT/SMC community overwhelmingly builds **indicators** rather than strategies. Out of ~25 ICT scripts evaluated, 12 were indicator-only. ICT concepts (order blocks, FVGs, kill zones) are primarily **detection patterns**, not complete trade systems. The best path for ALGO-CORE-ICT-001 is to use high-quality indicators as detection libraries and wrap them with custom `strategy()` entry/exit logic.

---

## 2. Automation-Ready Candidates (Top 15)

Strategies scoring highest on: deterministic rules, clear entry/exit, fixed session logic, defined stop/target, no discretionary interpretation, automated execution compatibility.

| Rank | ID | Name | Family | AF | Key Edge |
|------|-----|------|--------|---:|----------|
| 1 | VWAP-006 | VWAP-RSI Scalper FINAL v1 | vwap | 5 | Prop firm designed, ES futures, RSI(3)+VWAP+EMA, ATR stops, session control |
| 2 | ORB-009 | ORB Breakout + VWAP + Volume Filters | orb | 5 | Triple filter (VWAP slope, volume, candle strength), breakeven, EOD exit |
| 3 | ICT-010 | Captain Backtest Model [TFO] | ict | 5 | Session sweep → bias → pullback retracement, ES/NQ 5m proven |
| 4 | ORB-006 | ATR Trailing ORB | orb | 5 | Partial profit (50% at 3%), ATR trailing, break-even, EOD exit |
| 5 | VWAP-001 | RVWAP Mean Reversion | vwap | 5 | Rolling VWAP stdev bands, multiple anchors, session filters, v1.56 |
| 6 | ICT-002 | Liquidity Sweeper | ict | 5 | Clean sweep reversal, ATR SL, configurable R:R (2:1 default) |
| 7 | ICT-003 | Liquidity Sweep Filter | ict | 5 | Non-repainting, trend shift + sweep + volume profile |
| 8 | ORB-008 | NY ORB (MambaFX x DoyleStyle) | orb | 5 | Pine v6, 200/50/13 EMA filters, retest confirmation, session window |
| 9 | VWAP-020 | EMA + VWAP Strategy | vwap | 5 | VWAP flat filter (chop detection), ATR stops (1.5x), 2:1 R:R |
| 10 | VWAP-018 | ES Scalping Pro | vwap | 5 | Built for ES, 40-tick SL / 80-tick TP, dead simple |
| 11 | ORB-013 | ORB + Backtesting (3-level TP) | orb | 5 | 3x TP levels, monthly dashboard, timezone-aware, partial exits |
| 12 | VWAP-008 | VWAP Retest + EMA9 Cross + Pattern V2 | vwap | 5 | Session 9:30-12:30 EST, forced exit 1PM, documented 1.18 PF |
| 13 | ICT-009 | Order Block Volumatic FVG | ict | 5 | FVG mitigation depth, trailing stop, LTF volume analysis, Pine v6 |
| 14 | ORB-014 | 15-min ORB Retest | orb | 5 | Retest entry logic, fixed SL/TP, commission modeled |
| 15 | VWAP-013 | VWAP + RSI Strategy | vwap | 5 | RSI(3) pullback in last 10 bars + VWAP + EMA trend filter |

**Automation Filter Summary:** 30 scripts scored AF=5 (fully deterministic). 15 scored AF=4 (mostly clear). 9 scored AF=3-4 (mixed, need refinement).

---

## 3. Unique Entry Logic Discovered (Top 10)

| # | Entry Rule | Source | AF | Family | Why Unique |
|---|-----------|--------|---:|--------|------------|
| 1 | **Session sweep → bias determination → pullback retracement entry** | ICT-010 (Captain Backtest) | 5 | ict | Combines session structure with sweep-based bias, then waits for pullback — structural, not reactive |
| 2 | **FVG mitigation depth threshold entry** | ICT-009 (OB Volumatic FVG) | 5 | ict | Measures how deep price penetrates a FVG box (mitigation %), enters only when threshold met — quantified ICT concept |
| 3 | **RSI calculated on VWAP (not close price)** | VWAP-012 (RSI of VWAP) | 5 | vwap | Novel indicator composition — RSI source is VWAP itself, not raw close. Different signal timing than standard RSI |
| 4 | **VWAP flat filter (chop detector) gating entries** | VWAP-020 (EMA+VWAP) | 5 | vwap | Uses VWAP slope to detect range-bound conditions and skip entries. Simple but powerful regime filter |
| 5 | **Multi-period VWAP divergence (2-period vs 5-period)** | VWAP-002 (HYE Mean Reversion) | 5 | vwap | Jaws-algorithm adaptation — compares fast vs slow VWAP to detect overextension. Unique VWAP-on-VWAP approach |
| 6 | **Confidence scoring system (0-975 scale)** | VWAP-009 (GCK VWAP BOT) | 5 | vwap | Multi-factor scoring (HTF, market structure, session quality, volatility, volume) to rank signal quality before entry |
| 7 | **Cumulative gap momentum with SMA signal line** | ORB-018 (Gap Momentum TASC) | 5 | orb | Perry Kaufman academic method — cumulative open-gap series acts like OBV but for gaps. Published research backing |
| 8 | **VWAP reclaim + pullback hold + EMA stack (5/8/13)** | VWAP-023 (Neptuko) | 4 | vwap | Institutional-style VWAP reclaim. Not just cross — requires reclaim, pullback, and hold above VWAP with EMA confirmation |
| 9 | **ORB breakout with retest confirmation** | ORB-008 (MambaFX) | 5 | orb | Requires full candle outside OR + optional retest before entry — reduces false breakouts significantly |
| 10 | **Liquidity sweep + trend shift + volume profile** | ICT-003 (AlgoAlpha) | 5 | ict | Combines three institutional concepts into single non-repainting signal. Major vs minor sweep classification |

---

## 4. Full Strategies Recommended for Research (Top 10)

These are the 10 strategies recommended for conversion to Python and backtesting on Databento CME data.

### 4.1 VWAP-006: VWAP-RSI Scalper FINAL v1

| Attribute | Detail |
|-----------|--------|
| **Source** | TradingView (michaelriggs) |
| **Family** | VWAP (mean reversion / scalping) |
| **Entry** | RSI(3) oversold/overbought + VWAP directional filter + EMA trend filter |
| **Exit** | ATR-based stops, session-controlled US cash hours |
| **Risk** | ATR-adaptive position sizing, session flatten |
| **Session** | US cash hours only (3m-15m charts) |
| **AF** | 5/5 |
| **Why** | Explicitly designed for prop firm challenges. Best direct fit for our use case. |

### 4.2 ICT-010: Captain Backtest Model [TFO]

| Attribute | Detail |
|-----------|--------|
| **Source** | TradingView (tradeforopp) |
| **Family** | ICT (sweep + session structure) |
| **Entry** | Session range sweep → bias by 11:15 EST → pullback retracement through prior candle structure |
| **Exit** | Fixed R:R (toggleable) or hold until trade window close |
| **Risk** | ES 5pt SL, NQ 25pt SL — fixed point risk |
| **Session** | NY open session, bias determined by 11:15 EST |
| **AF** | 5/5 |
| **Why** | Only ICT strategy with futures-proven track record (ES/NQ 5m). Deterministic rules. |

### 4.3 ORB-009: ORB Breakout + VWAP + Volume Filters

| Attribute | Detail |
|-----------|--------|
| **Source** | TradingView (luiscaballero) |
| **Family** | ORB (breakout) |
| **Entry** | Close above/below OR high/low + VWAP slope filter + volume threshold + candle strength (close in top/bottom 30%) |
| **Exit** | TP = multiple of OR range, SL = opposite side, breakeven at 50% TP, EOD close |
| **Risk** | Breakeven adjustment, EOD flatten |
| **Session** | Configurable opening range period |
| **AF** | 5/5 |
| **Why** | Best filter architecture of all ORB scripts. Three independent, toggleable quality gates. |

### 4.4 VWAP-001: RVWAP Mean Reversion

| Attribute | Detail |
|-----------|--------|
| **Source** | TradingView (vvedding) |
| **Family** | VWAP (mean reversion) |
| **Entry** | Price dips below rolling VWAP stdev lower band and crosses above (long); inverse for short |
| **Exit** | Cross back to RVWAP center |
| **Risk** | Stdev-defined bands adapt to volatility |
| **Session** | Multiple anchor options (30m-Y), session filters (NY/London/Asia) |
| **AF** | 5/5 |
| **Why** | Purest mean reversion implementation. Most similar to our existing VWAP-REV module. v1.56 (Feb 2026). |

### 4.5 ORB-006: ATR Trailing ORB

| Attribute | Detail |
|-----------|--------|
| **Source** | TradingView (Wealth-Guru) |
| **Family** | ORB (breakout) |
| **Entry** | Close crosses above first-30-min high (long) or below low (short) |
| **Exit** | ATR trailing (3.5x multiplier), 50% partial profit at 3%, break-even, EOD 3:15 PM |
| **Risk** | ATR trailing + partial profit + break-even = 3-stage risk management |
| **Session** | First 30 min range, EOD exit 3:15 PM |
| **AF** | 5/5 |
| **Why** | Most complete risk management of any ORB script. Matches our 3-stage exit architecture. |

### 4.6 ICT-003: Liquidity Sweep Filter Strategy

| Attribute | Detail |
|-----------|--------|
| **Source** | TradingView (AlgoAlpha X PineIndicators) |
| **Family** | ICT (liquidity sweep) |
| **Entry** | Bullish/bearish liquidity sweep + trend shift confirmation via volatility-based MA system |
| **Exit** | Trend reversal signal |
| **Risk** | Direction config (long-only, short-only, both) |
| **Session** | Any |
| **AF** | 5/5 |
| **Why** | Non-repainting. Major vs minor sweep classification. Volume profile integration. |

### 4.7 VWAP-020: EMA + VWAP with Flat Filter

| Attribute | Detail |
|-----------|--------|
| **Source** | TradingView (cryptocu84) |
| **Family** | VWAP (trend following) |
| **Entry** | EMA9 cross above VWAP + EMA9 > EMA21 + VWAP directional slope |
| **Exit** | ATR(14)*1.5 SL, 2:1 R:R TP |
| **Risk** | ATR-adaptive, chop filter via VWAP flat detection |
| **Session** | 5-15m charts, weekday filter |
| **AF** | 5/5 |
| **Why** | VWAP flat filter is a standout regime detection feature. Directly applicable to our framework. |

### 4.8 ORB-008: NY ORB (MambaFX x DoyleStyle)

| Attribute | Detail |
|-----------|--------|
| **Source** | TradingView (menardpro97) |
| **Family** | ORB (breakout) |
| **Entry** | Full candle outside 15m OR + optional retest. 200/50/13 EMA trend alignment |
| **Exit** | 2R TP, 1R SL |
| **Risk** | Fixed R:R, trend filter prevents counter-trend entries |
| **Session** | 9:45 AM - 12:00 PM EST only, 5m execution TF |
| **AF** | 5/5 |
| **Why** | Pine v6. Multi-EMA filter stack is the most robust trend confirmation of any ORB script. |

### 4.9 ICT-009: Order Block Volumatic FVG Strategy

| Attribute | Detail |
|-----------|--------|
| **Source** | TradingView (TagsTrading) |
| **Family** | ICT (FVG) |
| **Entry** | Scans FVG boxes, computes mitigation % (depth of price entry into box), enters when threshold met |
| **Exit** | Fixed SL% + trailing stop that activates after profit trigger |
| **Risk** | Trailing stop activation, no pyramiding |
| **Session** | Any |
| **AF** | 5/5 |
| **Why** | Quantifies FVG mitigation — turns subjective ICT concept into measurable threshold. Pine v6. |

### 4.10 VWAP-008: VWAP Retest + EMA9 Cross + Pattern V2

| Attribute | Detail |
|-----------|--------|
| **Source** | TradingView (lindittl) |
| **Family** | VWAP (momentum / retest) |
| **Entry** | VWAP retest (price within buffer) + EMA9 cross above VWAP (within 3 bars) + bullish candle pattern |
| **Exit** | TP +3%, SL 0.5% below VWAP, forced exit 1 PM EST |
| **Risk** | Defined SL/TP, session flatten at 1 PM |
| **Session** | 9:30-12:30 EST morning only |
| **AF** | 5/5 |
| **Why** | Pre-validated: 120 trades backtested, 52.5% WR, 1.18 PF, 1.22% max DD. Session-restricted with forced exit. |

---

## 5. Strategy Diversity Analysis

### 5.1 Strategy Logic Clusters

| Cluster | Count | Scripts | Core Idea |
|---------|------:|---------|-----------|
| **VWAP Band Mean Reversion** | 6 | VWAP-001,002,004,005,007,019 | Enter at VWAP stdev/offset band extremes, exit at VWAP center |
| **VWAP + EMA Trend Following** | 5 | VWAP-010,011,018,020,022 | EMA/VWAP crossover as trend signal, VWAP as directional filter |
| **VWAP + RSI Confluence** | 4 | VWAP-006,012,013,021 | RSI oversold/overbought with VWAP as context filter |
| **ORB Classic Breakout** | 6 | ORB-001,004,005,013,014,017 | Break above/below OR high/low, fixed SL/TP or R:R |
| **ORB Filtered Breakout** | 5 | ORB-006,008,009,010,015 | ORB breakout + quality filters (VWAP, volume, EMA, SuperTrend) |
| **ORB Session/Drive** | 3 | ORB-002,007,011 | Market profile open drive or session-specific breakout |
| **ICT Liquidity Sweep** | 5 | ICT-002,003,005,007,008 | Detect stop hunts / sweeps, enter reversal |
| **ICT FVG-Based** | 4 | ICT-009,012,013,001 | Fair Value Gap detection + entry on fill/mitigation |
| **ICT SMC Structure** | 3 | ICT-004,006,011 | BOS/CHoCH/OB structure-based entries |
| **Hybrid / Unique** | 4 | VWAP-003,009,017, ORB-018 | Anchored VWAP pivot, confidence scoring, Minervini filter, gap momentum |

### 5.2 Duplicated Ideas (Low Diversity)

| Pair | Overlap | Resolution |
|------|---------|------------|
| ORB-009 / ORB-010 | Same author, same core logic, different defaults | Keep both — ORB-010 is NQ-specific refinement |
| VWAP-012 / VWAP-021 | Both use RSI(VWAP), different implementations | Keep both — different exit logic and position sizing |
| VWAP-013 / VWAP-014 | Same author, both use EMA filter + VWAP + pullback | Keep both — one uses RSI, other uses BB for pullback detection |
| ICT-004 / ICT-006 | Both use order block breakout, simple implementations | Keep ICT-004 (more complete), consider rejecting ICT-006 |

### 5.3 Unique Strategy Families Discovered

| Family | Sub-Type | Unique Scripts | Build Target |
|--------|----------|---------------|-------------|
| **VWAP Mean Reversion** | Band bounce | 6 scripts | ALGO-CORE-VWAP-001 |
| **VWAP Trend Following** | EMA/VWAP cross | 5 scripts | New family candidate |
| **ORB Classic** | Pure breakout | 6 scripts | ALGO-CORE-ORB-001 |
| **ORB Filtered** | Multi-filter breakout | 5 scripts | ALGO-CORE-ORB-001 (advanced) |
| **ICT Sweep Reversal** | Liquidity sweep → reversal | 5 scripts | ALGO-CORE-ICT-001 |
| **ICT FVG** | Fair value gap fill | 4 scripts | ALGO-CORE-ICT-001 (sub-type) |
| **Gap Momentum** | Cumulative gap analysis | 1 script | New family candidate |
| **Confidence Scoring** | Multi-factor signal quality | 1 script | Component extraction only |

### 5.4 Diversity Assessment

**Strengths:**
- Good coverage across all 3 target families (ICT, ORB, VWAP)
- Multiple distinct entry logics within each family (not just variations on one idea)
- Mix of mean reversion + trend following + breakout + liquidity concepts
- Several unique ideas not found in our existing codebase (FVG mitigation %, confidence scoring, gap momentum, VWAP flat filter)

**Gaps:**
- No pure **momentum** strategies (MACD/stochastic-based)
- No **pairs trading** or **stat-arb** strategies
- Limited **overnight/swing** strategies (most are intraday)
- ICT family needs more strategy-grade scripts (most are indicators)

---

## 6. Extracted Strategy Components

### 6.1 Entry Components (13 unique patterns)

| ID | Entry Pattern | Source | Category |
|----|--------------|--------|----------|
| ENTRY-VWAP-BAND-001 | VWAP stdev band touch → cross back | VWAP-001,004,005,007 | Mean reversion |
| ENTRY-VWAP-RSI-001 | RSI(3) oversold + VWAP directional filter | VWAP-006,013 | Pullback |
| ENTRY-VWAP-CROSS-001 | EMA cross above/below VWAP | VWAP-010,018,020 | Trend |
| ENTRY-VWAP-RECLAIM-001 | VWAP reclaim + pullback hold | VWAP-023 | Institutional |
| ENTRY-ORB-BREAK-001 | Close above/below OR high/low | ORB-001,004,005,013,017 | Breakout |
| ENTRY-ORB-RETEST-001 | ORB breakout + retest confirmation | ORB-008,014 | Breakout (filtered) |
| ENTRY-ORB-FILTER-001 | ORB + VWAP slope + volume + candle strength | ORB-009,010 | Breakout (multi-filter) |
| ENTRY-ICT-SWEEP-001 | Liquidity sweep at swing high/low → reversal | ICT-002,003,007,008 | Reversal |
| ENTRY-ICT-FVG-001 | FVG detection + mitigation depth entry | ICT-009,013 | Gap fill |
| ENTRY-ICT-SESSBIAS-001 | Session sweep → bias → pullback | ICT-010 | Structure |
| ENTRY-ICT-OB-001 | Order block breakout | ICT-004,006 | Structure |
| ENTRY-GAP-MOM-001 | Cumulative gap momentum signal line | ORB-018 | Momentum |
| ENTRY-RSIVWAP-001 | RSI calculated on VWAP source | VWAP-012,021 | Composite |

### 6.2 Filter Components (8 unique patterns)

| ID | Filter | Source |
|----|--------|--------|
| FILTER-EMA-TREND-001 | EMA 200/50/13 trend alignment | ORB-008, VWAP-013 |
| FILTER-VWAP-FLAT-001 | VWAP slope = flat → skip (chop) | VWAP-020 |
| FILTER-VOL-AVG-001 | Volume > Nx moving average | ORB-009,010, ICT-008 |
| FILTER-SESSION-001 | Time window gating (kill zones, NY open) | VWAP-006,008, ORB-007 |
| FILTER-ADX-REGIME-001 | ADX threshold for trend/range | Existing (PB-TREND) |
| FILTER-CANDLE-STRENGTH-001 | Close in top/bottom 30% of range | ORB-009 |
| FILTER-MAXTRADES-001 | Max N trades per day | ORB-001,004 |
| FILTER-CONFIDENCE-001 | Multi-factor confidence score threshold | VWAP-009 |

### 6.3 Exit Components (10 unique patterns)

| ID | Exit Model | Source |
|----|-----------|--------|
| EXIT-ATR-TRAIL-001 | ATR multiplier trailing stop | ORB-006, VWAP-020 |
| EXIT-FIXED-RR-001 | Fixed R:R ratio (1:2, 1:3) | ORB-007,008,014, ICT-002 |
| EXIT-PARTIAL-001 | 50% partial at Nx profit, hold remainder | ORB-006 |
| EXIT-3TARGET-001 | 3-level TP (60%/120%/200% or 1R/2R/3R) | ORB-013, VWAP-009 |
| EXIT-EOD-001 | Forced exit at session close (3:15 PM) | ORB-001,004,006,014 |
| EXIT-VWAP-RETURN-001 | Exit when price returns to VWAP center | VWAP-001,004,007 |
| EXIT-MA-CROSSBACK-001 | Exit when MA crosses back (trend reversal) | ORB-007,011 |
| EXIT-RSI-EXTREME-001 | Exit at RSI overbought/oversold threshold | VWAP-012,013 |
| EXIT-BE-ADJUST-001 | Move SL to breakeven at 50% of TP distance | ORB-009,010 |
| EXIT-TREND-REVERSAL-001 | Exit on opposite signal (cut-and-reverse) | VWAP-010, ICT-003 |

### 6.4 Risk Model Components (5 unique patterns)

| ID | Risk Model | Source |
|----|-----------|--------|
| RISK-ATR-STOP-001 | SL = Nx ATR from entry | ORB-006, VWAP-006,020, PB-TREND |
| RISK-OR-OPPOSITE-001 | SL at opposite side of opening range | ORB-007,009,013 |
| RISK-FIXED-TICK-001 | Fixed tick/point stop (40 SL / 80 TP) | VWAP-018, ORB-017 |
| RISK-PERCENT-001 | Fixed % of equity (5% SL) | VWAP-012,013,014 |
| RISK-STRUCTURE-001 | SL at prior swing high/low | ICT-007, ICT-010 |

### 6.5 Session Model Components (4 unique patterns)

| ID | Session Model | Source |
|----|--------------|--------|
| SESSION-NY-OPEN-001 | 9:30-11:00 ET (first 90 min) | ORB-007,008, VWAP-008 |
| SESSION-MORNING-001 | 9:30-12:30 ET (morning session) | VWAP-008, ORB-009 |
| SESSION-FULL-DAY-001 | 9:30-15:15 ET (full day, EOD flatten) | ORB-001,004,006 |
| SESSION-KILLZONE-001 | 9:30-11:00 ET + 14:00-15:00 ET (kill zones) | ICT-010, PB-TREND |

---

## 7. External Strategies — Top Picks

These are the highest-value strategies from non-TradingView sources (GitHub, QuantConnect, research, blogs).

| Rank | ID | Name | Source | Family | AF | Key Edge |
|------|-----|------|--------|--------|---:|----------|
| 1 | GH-ICT-001 | smartmoneyconcepts library | GitHub | ict | 5 | Pip-installable ICT detection (FVG, OB, BOS, CHoCH, Liquidity). Direct Python integration |
| 2 | GH-ORB-007 | Backtrader 4-Phase State Machine | GitHub | orb | 5 | SCANNING→ARMED→WINDOW→ENTRY, 6-layer validation, PF 1.64 on Gold |
| 3 | FMZ-VWAP-002 | VWAP + OBV-RSI Mean Reversion | FMZ | vwap | 5 | Dual confirmation (price deviation + volume momentum), 0.6% hard stop |
| 4 | GH-VWAP-004 | Futures Mean Reversion Framework | GitHub | vwap | 5 | Z-score/t-score entries, margin constraints, production-grade futures framework |
| 5 | GH-TREND-001 | Pysystemtrade (Rob Carver) | GitHub | orb | 5 | Gold standard systematic futures. Breakout80/160/320, Sharpe ~0.77, IB production |

---

## 8. Pipeline Funnel

```
Harvest (108+ evaluated)
      ↓ reject 32+ (indicator-only, paid, duplicate, no exits)
Accepted Candidates (76)
      ↓ automation fitness filter (AF >= 4)
Automation-Ready (60+)
      ↓ research priority ranking
Research Candidates (10)
      ↓ conversion + backtesting
Validated Families (target: 3-5)
```

**Current validated families: 1** (ALGO-FAMILY-PB-001)
**Target new families from this harvest: 2-3** (ORB, VWAP, possibly ICT)

---

## 9. Recommended Next Steps

### Priority 1: Convert and backtest top 3 strategies (one per family)
1. **VWAP-006** (VWAP-RSI Scalper) or **FMZ-VWAP-002** (VWAP+OBV-RSI) → ALGO-CORE-VWAP-001 first candidate
2. **ORB-009** (ORB + VWAP + Volume Filters) → ALGO-CORE-ORB-001 first candidate
3. **ICT-010** (Captain Backtest Model) → ALGO-CORE-ICT-001 first candidate

### Priority 2: Integrate external tools
- **`pip install smartmoneyconcepts`** → add to backtest engine for ICT detection
- **4-phase state machine** (GH-ORB-007) → evaluate as architecture upgrade for pullback entries
- **OBV-RSI filter** (FMZ-VWAP-002) → test as regime filter for VWAP-REV module

### Priority 3: Extract and integrate components
- VWAP flat filter (FILTER-VWAP-FLAT-001) → add to existing regime detection
- 3-stage exit model (EXIT-3TARGET-001) → test as upgrade to current bracket exits
- Breakeven adjustment (EXIT-BE-ADJUST-001) → compare with current BE-at-1R logic

### Priority 4: Expand ICT coverage
- Integrate `smartmoneyconcepts` library into backtest engine
- Convert top rejected ICT indicators to strategy wrappers
- Focus on: LuxAlgo SMC detection + DivergentTrades sweep logic + nephew_sam_ market structure

---

*Report generated: 2026-03-07*
*Manifest: intake/manifest.json (54 scripts)*
*Components: research/strategy_components/*
