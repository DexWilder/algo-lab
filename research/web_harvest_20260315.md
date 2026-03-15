# FQL Web Strategy Harvest — 2026-03-15

## Sources Searched
- Academic papers (JFE, SSRN, ScienceDirect, NY Fed)
- QuantifiedStrategies, QuantStart, Quantpedia
- TradingView practitioner strategies
- Quant forums and blogs

## 15 Candidates Found (10 added to registry)

### Tier 1 — Academic-Backed (HIGH confidence)

1. **Noise-Boundary Breakout (MES-long)** — Zarattini/Aziz/Barbon 2024
   - Swiss Finance Institute. Sharpe 1.33, 19.6% annualized (2007-2024)
   - Fills MES-long gap

2. **Intraday Momentum Continuation (MES afternoon)** — Gao/Han/Li/Zhou JFE 2018
   - Last 30min trades in direction of morning return
   - R-squared 1.6%, 6.02% CE gains. VIX > 20 filter critical
   - Fills afternoon session gap

3. **Pre-FOMC Drift (MES-long)** — Lucca/Moench NY Fed
   - 49 bps avg return in 24h pre-FOMC. Still alive through 2024.
   - 8 trades/year. Fills event-driven gap

### Tier 2 — Practitioner-Validated (MEDIUM confidence)

4. **VWAP Pullback Long (MES)** — Composite practitioner sources
   - Documented as "highest-probability trade of the day" on ES
   - 100-150 trades/yr. Fills MES-long gap

5. **Russell ORB Long (M2K)** — Academic ORB research
   - 15-min range, long above. M2K higher beta amplifies
   - 80-120 trades/yr. Fills M2K-long gap

6. **Keltner Channel Breakout (M2K-long)** — QuantifiedStrategies
   - 77% documented win rate. RSI + ADX confirmation
   - 80-120 trades/yr. Fills M2K-long gap

7. **Crude Oil VWAP Bounce (MCL-long)** — Anthony Crudele
   - Morning session London/NY overlap. VWAP pullback entry
   - 100-150 trades/yr. Fills MCL-long gap

8. **Crude Oil ORB Long (MCL)** — ScienceDirect academic
   - "Remarkable success of ORB in US crude oil futures"
   - 100-130 trades/yr. Fills MCL-long gap

### Tier 3 — Event-Driven / Niche

9. **EIA Inventory Surprise (MCL)** — Practitioner consensus
   - Wednesday 10:30 ET. Only outsized surprises (>5M bbl)
   - 20-25 trades/yr. Fills event-driven + MCL

10. **OPEX Week Long (MES)** — Quantpedia
    - Gamma hedging driven. Weakening last 3 years
    - 12 trades/yr. Low priority

### Not Added to Registry (lower priority / overlap)

11. **Last-Hour Momentum Surge** — Small sample (18 trades)
12. **MOC Imbalance Fade** — Needs NYSE real-time data feed
13. **SPY-IWM Spread** — Added but complex (needs simultaneous data)
14. **9/20 EMA Crossover (MES)** — Crossover entries fail on 5m bars (known lesson)
15. **Crude BB Mean Reversion** — Similar to existing BB-EQ family

## Dead Ends Documented
- **CPI day trading**: QuantifiedStrategies — no edge (+0.01% avg)
- **NFP day trading**: No edge found across multiple sources
- **Simple ORB on ES/MES**: Edge eroded due to crowding, needs regime filters
- **OPEX week**: Weakened significantly last 3 years

## Key Academic Sources
- Gao, Han, Li, Zhou (JFE 2018) — Market Intraday Momentum
- Zarattini, Aziz, Barbon (2024) — Beat the Market: Intraday Momentum for SPY
- Lucca & Moench (NY Fed SR512) — Pre-FOMC Announcement Drift
- Baltussen, Da, et al. (JFE 2021) — Hedging Demand and Market Intraday Momentum
- ScienceDirect — ORB profitability in crude oil futures
