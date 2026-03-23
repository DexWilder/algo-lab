# Highest-Signal Source Shortlist

*Organized by source type. Based on RSS testing, community size,
content quality assessment, and transcript availability.*
*Date: 2026-03-23*

---

## 1. YouTube

YouTube is the weakest source lane by conversion. Most content is
narrative/discretionary. The few channels worth tracking produce
occasional mechanical gems buried in long-form content.

### Best Channels

| Channel | Handle | Role | Signal/Noise | Transcripts | Note |
|---------|--------|------|-------------|-------------|------|
| **QuantConnect** | @QuantConnect | Fragment source | Medium | No | Platform tutorials sometimes contain testable strategy logic |
| **Part Time Larry** | @parttimelarry | Fragment source | Medium | No | Python backtesting content, sometimes with futures applicability |
| **Coding Jesus** | @CodingJesus | Fragment source | Low-Med | No | ML/quant trading, occasionally systematic |
| **Top Traders Unplugged** | @toptradersunplugged | Support/convergence | Medium | No | CTA/managed futures interviews — conceptual, rarely mechanical |
| **Moon Dev** | @moondevonyt | Fragment source | Low-Med | No | Algo trading implementation, some testable ideas |

### Avoid

| Channel | Why |
|---------|-----|
| Generic "day trading" channels | Discretionary, lifestyle, motivation — zero testable rules |
| ICT / SMC channels | Closed family |
| Crypto-focused channels | Wrong asset class |
| "I made $X in Y days" channels | Hype, not substance |

### Best Query Themes (for YouTube helper)

```
"systematic trading backtest results"
"quantitative trading strategy explained"
"futures backtesting python"
"managed futures trend following"
"volatility targeting portfolio"
"carry trade systematic"
"mean reversion strategy rules"
```

**Verdict: Keep running, low cap (3-5/run). YouTube is a fragment source
at best. Don't expect primary ideas from this lane.**

---

## 2. Reddit / Forums

Reddit has strong raw volume but most content is opinions, not rules.
The signal lives in self-text and top comments, not titles.

### Best Communities

| Community | Members | Role | Signal/Noise | Note |
|-----------|---------|------|-------------|------|
| **r/algotrading** | 1.8M | Primary idea + fragment | Medium | Largest quant trading community. Mechanical discussions exist but buried in noise |
| **r/quant** | 183K | Support/convergence | Medium-High | More academic, factor-focused. Good for convergent evidence |
| **r/FuturesTrading** | 177K | Fragment source | Low-Med | More practitioner, some session-specific insights |
| **r/quantfinance** | 69K | Support/convergence | Medium | Academic quant finance, risk models, factor research |
| **r/RealDayTrading** | 126K | Fragment source | Low-Med | Rules-based discussions exist, mixed with discretionary |
| **r/options** | 1.4M | Fragment source | Low | Options ideas that may translate to futures vol strategies |

### Avoid

| Community | Why |
|-----------|-----|
| r/wallstreetbets | Pure noise — memes, YOLO, zero systematic content |
| r/Daytrading (5M) | Massive but mostly discretionary/beginner content |
| r/StockMarket (4M) | General market discussion, not strategy-focused |
| r/pennystocks | Wrong universe entirely |
| Any crypto subreddit | Wrong asset class |

### Best Query Themes (for Reddit helper)

```
"backtest results strategy"        — finds people showing actual results
"entry exit rules"                 — finds mechanical descriptions
"systematic strategy rules"        — finds rule-based discussions
"futures strategy profitable"      — finds practitioner experience
"volatility filter regime"         — finds fragment ideas
"session trading strategy"         — finds timing edges
"stop loss strategy systematic"    — finds exit/risk logic
"carry trade strategy"             — fills CARRY gap
"treasury futures"                 — fills rates gap
"crude oil futures strategy"       — fills energy gap
```

**Verdict: Keep running, medium cap (15/run). Reddit is best for
fragments and convergence, not primary strategies. Score body + comments,
not titles.**

---

## 3. GitHub

GitHub has the highest pass rate (50%) but lowest raw volume.
The bottleneck is search breadth, not quality.

### Best Query Themes

| Theme | Expected Yield | Note |
|-------|---------------|------|
| `"quantitative trading strategy"` | High | Broad, finds the big repos |
| `"systematic trading backtest"` | High | Finds repos with actual results |
| `"backtesting framework python"` | Medium | Framework repos sometimes include example strategies |
| `"futures trading python"` | Medium | Directly relevant to FQL |
| `"carry trade systematic"` | Medium | CARRY gap fill |
| `"volatility managed portfolio"` | Medium | VOL gap fill |
| `"mean reversion trading"` | Medium | Broad factor |
| `"pairs trading cointegration"` | Medium | Statistical arb / relative value |
| `"risk parity portfolio python"` | Low-Med | Portfolio construction logic |
| `"trend following backtest"` | Medium | Managed futures style |
| `"commodity futures python"` | Low-Med | Energy/commodity gap fill |
| `"market microstructure"` | Low | Academic, may translate |

### Best Repo Patterns

| Pattern | Why |
|---------|-----|
| Repos with `backtest` or `results` in README | Evidence of testable logic |
| Repos with strategy `.py` files | Directly usable code |
| Repos with > 50 stars and recent updates | Community-validated, maintained |
| Repos referencing specific indicators (ATR, VWAP, EMA) | Mechanical, not theoretical |

### Avoid

| Pattern | Why |
|---------|-----|
| Repos with < 5 stars and no README | Likely abandoned experiments |
| Crypto/DeFi repos | Wrong asset class |
| ML-only repos without strategy logic | Framework, not strategy |
| Repos that are just data downloaders | No strategy content |

**Verdict: Keep running, expand queries. GitHub is healthy but narrow.
Pass rate is strong enough to justify 2x query expansion.**

---

## 4. Blogs / Substacks

The highest-signal non-digest source. Long-form practitioner writing
produces the best fragments because authors think deeply about mechanisms.

### Current Feeds (6)

| Feed | Category | Status | Role |
|------|----------|--------|------|
| **Alpha Architect** | Quant research | Active, producing | Primary idea source |
| **Newfound Research** | Portfolio construction | Active, producing | Fragment source |
| **Return Stacked** | Managed futures | Active, producing | Fragment + primary |
| **Robot Wealth** | Quant research | Active | Fragment source |
| **ReSolve Asset Management** | Managed futures | Active, new | Primary idea source |
| **Moontower** | Vol/structure | Active, new | Fragment source |

### Recommended Additions

| Feed | URL | Category | Expected Role | Signal/Noise |
|------|-----|----------|--------------|-------------|
| **Philosophical Economics** | `philosophicaleconomics.com/feed/` | Value/macro | Primary idea source | High — deep analytical posts on valuation, earnings, equity structure |
| **Mutiny Fund** | `mutinyfund.com/feed/` | Portfolio construction | Fragment source | Medium — permanent portfolio, tail hedging, allocation logic |

### Monitor (add if quality confirms)

| Feed | URL | Category | Note |
|------|-----|----------|------|
| Macro Ops | `macro-ops.com/feed/` | Macro/trend | Mixed — some systematic, some discretionary |
| Benn Eifert (Substack) | `benneifert.substack.com/feed` | Vol/options | Deep vol content but sparse posting. Options-focused, may translate |

### Avoid

| Source | Why |
|--------|-----|
| Kyla Scanlon | Macro commentary, not strategy — no testable rules |
| Generic "investing tips" Substacks | Noise |
| News-commentary blogs | No mechanism content |
| Portfolio Charts | Useful for allocation research but not strategy ideas |

**Verdict: Strongest non-digest source. Expand to 8 feeds. Feeds should
be added one at a time to verify quality before raising cap.**

---

## 5. Digests

The highest-signal source by conversion rate. Every entry is a documented
strategy concept.

### Current Feeds (2)

| Feed | Status | Role |
|------|--------|------|
| **Quantpedia** | Active, primary | Primary idea source — 4 attributed notes |
| **ReSolve Asset Management** | Active, new | Primary idea source — carry/trend/CTA |

### Recommended Additions

| Source | Mechanism | Expected Role | Note |
|--------|-----------|--------------|------|
| **QuantifiedStrategies** | Claw direct search (no RSS) | Primary idea source | Strategy-specific blog posts with backtest results. Claw already targets this in academic_scan |

### Monitor

| Source | Note |
|--------|------|
| SSRN quantitative finance | Claw searches directly. No RSS needed — too high volume for a feed |
| arXiv q-fin | Same — Claw searches during academic_scan |

### Not Worth Adding as Feeds

| Source | Why |
|--------|-----|
| AQR Insights | No working RSS feed (tested) |
| Man AHL / Man Group | No working RSS feed (tested, 404) |
| Two Sigma Insights | No working RSS feed (tested, empty response) |
| CAIA | No working RSS (tested, tiny response) |

**Verdict: Strongest source lane. Quantpedia alone produces the highest
conversion rate. ReSolve adds carry/CTA depth. Don't over-expand —
quality matters more than quantity for digests.**

---

## Summary: Recommended Actions

| Source | Current State | Action | Priority |
|--------|-------------|--------|----------|
| **Blog** | 6 feeds, producing | Add Philosophical Economics + Mutiny Fund | HIGH |
| **Digest** | 2 feeds, highest conversion | Keep. Monitor QuantifiedStrategies via Claw | MEDIUM |
| **GitHub** | 24 queries, 50% pass | No change needed — queries already expanded | LOW |
| **Reddit** | 6 subs, 16 queries | No change — wait for attribution data | LOW |
| **YouTube** | 17 queries, 3 leads/run | No change — low-yield source, accept it | LOW |

### Sources to Avoid (noise traps)

- r/wallstreetbets, r/Daytrading, r/pennystocks
- Generic "day trading motivation" YouTube channels
- ICT/SMC channels (closed family)
- Crypto-focused anything
- News-commentary blogs without strategy content
- "I made $X" style content on any platform
