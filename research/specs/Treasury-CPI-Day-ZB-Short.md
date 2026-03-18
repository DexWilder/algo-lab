# Strategy Spec: Treasury-CPI-Day-ZB-Short

## Hypothesis

CPI releases create directional pressure on Treasury futures. During
the current macro regime (2019-2026), CPI releases have tended to be
interpreted as hawkish for bonds — higher-than-expected or sticky
inflation reinforces rate-hike/hold expectations, pushing bond prices
down (yields up). A short ZB position into CPI day captures this
directional bias.

**Why ZB short specifically:**
- ZB (30-Year Bond) has the highest duration — it moves the most per
  yield change, amplifying the CPI-driven repricing
- ZB short PF 1.26 on 63 trades vs ZN short PF 0.96 (no edge on ZN)
- The long side fails on ZB (PF 0.79) — the effect is directionally
  short in the current regime

**Honest framing: this is regime-dependent.** The short bias works
because the 2019-2026 period was dominated by inflation concerns (2021-2023
tightening cycle, 2024-2025 sticky inflation). In a disinflationary
regime (falling inflation → rate cuts → bond rally), the CPI-day effect
could reverse. The strategy must be understood as a regime-conditioned
event trade, not a universal CPI-day pattern.

## Why This Is Different From Existing Event Sleeves

| Dimension | PreFOMC-Drift | TV-NFP-Levels | CPI-Day-ZB-Short |
|-----------|--------------|---------------|-------------------|
| Event | FOMC (8/yr) | NFP (12/yr) | CPI (12/yr) |
| Asset | MNQ (equity) | MNQ (equity) | ZB (rates) |
| Mechanism | Anticipation drift (pre-event) | Level breakout (post-event) | Directional repricing (through-event) |
| Direction | Long equity | Long equity | **Short bonds** |
| Factor | EVENT | EVENT | **EVENT + Rates asset** |
| Session overlap | Zero with each other | Zero with each other | **Zero with both** |

Three completely independent event families, three different assets,
three different mechanisms. Zero calendar overlap (CPI, FOMC, and NFP
are different dates). Adding CPI-Day-ZB-Short would give the portfolio
three independent event sleeves covering both equity and rates.

## Signal Logic

1. Check if tomorrow is a CPI release date (hardcoded BLS calendar)
2. At last bar before CBOT close (~14:55 ET), enter short ZB
3. Hold through CPI release (08:30 ET next day) and intraday reaction
4. Exit at CBOT close (~14:55 ET) on CPI day
5. No re-entry until next month's CPI

## Data and Sample

| Metric | Value |
|--------|-------|
| Asset | ZB (30-Year Bond) |
| Data range | 2019-06 to 2026-03 (6.7 years) |
| CPI events in sample | 63 (after data alignment) |
| Trades per year | ~9-11 |
| Direction | Short only |

## Results (6.7-Year Backtest)

| Metric | Value |
|--------|-------|
| Trades | 63 |
| PF | **1.26** |
| WR | 52% |
| Total PnL | +$8,094 |
| WF H1 PF | 0.99 (31 trades — flat) |
| WF H2 PF | **1.50** (32 trades — strong) |

### Year-by-Year

| Year | N | PF | PnL |
|------|---|-----|------|
| 2019 | 6 | 2.28 | +$2,125 |
| 2020 | 10 | 0.62 | -$2,531 |
| 2021 | 9 | 1.19 | +$688 |
| 2022 | 8 | 0.37 | -$4,375 |
| 2023 | 9 | 0.85 | -$906 |
| 2024 | 11 | 4.01 | +$10,906 |
| 2025 | 8 | 1.94 | +$2,031 |
| 2026 | 2 | 1.71 | +$156 |

### Regime Pattern

The year-by-year reveals the regime dependency:
- **2019:** Strong (pre-COVID, rate cut cycle — short bonds lost but
  CPI was benign, PF 2.28)
- **2020:** Loss (COVID deflationary shock — bonds rallied hard)
- **2021:** Marginal (inflation starting, mixed CPI prints)
- **2022:** Loss (rates rising fast but CPI was already priced in —
  bonds rallied on some CPI prints as "peak inflation" narrative)
- **2023:** Marginal loss (sticky inflation, mixed reactions)
- **2024:** **Strong** (PF 4.01 — CPI prints consistently hawkish,
  bonds sold off reliably)
- **2025-2026:** Positive (continuing hawkish CPI regime)

The edge is concentrated in the most recent period (2024-2026). This
could mean (a) the strategy is getting stronger as CPI becomes more
market-moving, or (b) it's a recent-regime artifact. Forward evidence
would distinguish these.

## Key Limitations

1. **Regime dependency is the primary risk.** PF 1.26 on 63 trades is
   marginal. The WF H1 is flat (PF 0.99). The edge lives in H2
   (2023-2026), which is the hawkish-CPI regime. If inflation cools and
   rate cuts begin, the CPI-day short bias could reverse.

2. **2022 paradox.** The tightening year (when shorts "should" work best)
   was actually a loss year (PF 0.37). This is because CPI was SO
   hawkish that the market was already positioned short going in —
   actual CPI prints sometimes triggered short-covering rallies.

3. **PF 1.26 is marginal by elite standard.** This is honest. It clears
   the 1.2 ADVANCE floor barely. The elite question is whether the
   EVENT + Rates gap value justifies a marginal PF.

4. **Original PF 2.81 claim was from a shorter sample.** The full
   6.7-year backtest shows PF 1.26, not 2.81. The higher number was
   likely from a 2-year subset during the peak hawkish period.

## What Would Make This a Real Challenger

This becomes a real challenger (not just another MONITOR) if:

1. **WF H2 strength persists in forward.** If the next 12+ CPI events
   (2026-2027) continue showing PF > 1.2 on ZB-short, the H2 trend
   is real, not a recent artifact.

2. **Regime-conditioning improves the signal.** If adding a simple
   filter (e.g., "only short when trailing 6-month inflation trend is
   rising") improves WF stability, the strategy becomes regime-aware
   rather than regime-dependent.

3. **Combined event sleeve value.** Even at PF 1.26, three independent
   event sleeves (FOMC + NFP + CPI) on different assets produce
   ~32 event trades per year with zero overlap. The portfolio-level
   EVENT factor contribution may be more valuable than any single
   sleeve's PF suggests.

## Displacement Assessment

```
Candidate: Treasury-CPI-Day-ZB-Short
Estimated Rubric: Q1=3(STRONG), Q2=2(MARGINAL — regime dependent),
  Q3=4(ELITE — only CPI rates event), Q4=3(STRONG — EVENT+Rates),
  Q5=2(MARGINAL — WF H1 flat), Q6=2(MARGINAL — 2022 paradox concerning)
Raw: 16/24 + 2 gap bonus = 18 effective

vs MomIgn (14): Advantage (+4 effective). Fills 2 gaps (EVENT family
  + Rates asset) vs MomIgn's 0 gaps.
vs TTMSqueeze (17 watch): Marginal advantage (+1). Different factor
  (EVENT vs VOL). Would compete for a different niche.
vs PB-MGC-Short (16 core): Tie on raw, advantage on gap value. But
  PF 1.26 with regime dependency is not a core-ready strategy.
```

**Verdict: EMERGING CHALLENGER, not yet decision-grade.** Rubric 18
effective meets the conviction threshold IF the WF H2 strength holds.
But the regime dependency and 2022 paradox create real uncertainty.
This needs either (a) forward evidence from the next few CPI events,
or (b) a regime-conditioning filter to improve WF stability before
it's a serious displacement candidate.

## Recommended Next Steps

1. **Do NOT open a conversion slot for this now.** Treasury-Rolldown
   and VolManaged are stronger candidates with clearer paths.

2. **Track the next 3-4 CPI events** (Apr/May/Jun 2026). If ZB sells
   off on CPI day in 3 of 4, the H2 trend is confirmed and the
   strategy strengthens materially.

3. **Queue a regime-conditioning test** as an enhancement: filter by
   trailing inflation trend (CPI YoY direction). If this stabilizes
   the WF, rubric could rise to 19-20.

4. **File as Emerging Challenger #1** — the strongest non-active
   candidate in the pipeline after VolManaged.
