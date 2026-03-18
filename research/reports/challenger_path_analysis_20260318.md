# Challenger Path Analysis — Next Displacement Upgrade
## 2026-03-18

*Focus: which single challenger path makes the portfolio stronger fastest.*

---

## Targets

| Incumbent | Bucket | Rubric | Vulnerability |
|-----------|--------|--------|---------------|
| MomIgn-M2K-Short | Watch | 14 | Lowest rubric, overcrowded MOMENTUM, deadline June 1 |
| PB-MGC-Short | Core | 16 | Lowest core, 9 trades in 6yr, 4th MGC at soft cap |

---

## Top 3 Challengers

### #1. Treasury-Rolldown-Carry-Spread

| Dimension | Assessment |
|-----------|------------|
| **Rubric** | 18 raw + 2 gap = **20 effective** |
| **Gap value** | CARRY factor (0 active) + Rates asset (0 active) = **2 gaps, the two biggest in the portfolio** |
| **Mechanism** | STRONG (3/4) — academic basis, carry lookup provides real directional signal, spread confirmed rate-neutral (corr 0.027) |
| **Current status** | Testing. strategy.py complete. PF 1.11 (equal) / 1.10 (DV01) on 79 monthly trades. |
| **Displacement target** | MomIgn (14) → decisive. PB-MGC (16) → arguable after forward evidence. |
| **Timeline to displacement** | **June 1 (75 days).** MomIgn's watch deadline. Treasury-Rolldown needs any forward evidence by then. Since it's a monthly-rebalance strategy, it will have 2-3 spread returns by June. |
| **What must happen** | Get Treasury-Rolldown into the forward runner to accumulate live evidence. Even 2 months of spread returns (positive or negative) constitutes evidence. |
| **Likelihood** | **HIGH.** Strategy exists, signal works, data exists. The only question is whether PF 1.11 holds forward. Even flat forward performance fills two gaps that MomIgn doesn't fill. |

**Portfolio upgrade if displaced:**
- Opens CARRY (0 → 1)
- Opens Rates (0 → 1)
- Removes MOMENTUM overcrowding (1 fewer)
- Reduces M2K concentration (3 → 2 watch)
- Replaces rubric 14 with effective 20

---

### #2. VolManaged-EquityIndex-Futures

| Dimension | Assessment |
|-----------|------------|
| **Rubric (estimated)** | Q1=3(STRONG: Moreira/Muir NBER), Q2=3(STRONG: documented across decades), Q3=4(ELITE: only vol-management idea with code path), Q4=3(STRONG: fills VOL gap, MES is underpopulated), Q5=1(WEAK: no backtest yet), Q6=3(STRONG: simple to implement, low eng cost) = **17 raw + 2 gap = 19 effective** |
| **Gap value** | VOLATILITY factor (0 active, 1 watch). MES asset (only 1 active strategy). |
| **Mechanism** | STRONG — inverse-vol scaling is one of the most replicated results in academic finance. Simple, robust, not parameter-dependent. |
| **Current status** | Idea. No strategy.py. Testable now — needs only daily realized vol on MES (we have this). |
| **Displacement target** | MomIgn (14) → clear advantage. PB-MGC (16) → would need strong backtest. |
| **Timeline** | **4-6 weeks** from conversion approval. Spec → code → first-pass → validation. Simple strategy (vol scaling, no complex entries) so factory throughput should be fast. |
| **What must happen** | Open a conversion slot. Write spec. Convert to strategy.py. Run first-pass. If PF > 1.2 with VOL factor tag, it enters conviction directly (rubric estimate 19 with gap bonus). |
| **Likelihood** | **MEDIUM-HIGH.** Academic basis is extremely strong but we haven't tested it on our data yet. The mechanism is so simple (scale position by 1/vol) that it's hard to imagine it producing zero edge — the question is whether the edge is large enough. |

**Portfolio upgrade if displaced:**
- Opens VOLATILITY factor (0 → 1 in conviction)
- Adds MES depth (only 1 active MES strategy currently)
- Non-morning session (daily rebalance, not intraday)
- Horizon diversification (daily, not 5m)

---

### #3. Commodity-TermStructure-Carry-EnergyMetals

| Dimension | Assessment |
|-----------|------------|
| **Rubric** | 17 raw + 2 gap = **19 effective** |
| **Gap value** | CARRY factor (0 active). Commodity asset diversity. |
| **Mechanism** | STRONG in theory (academic), but signal is PROXY (60-day return conflates carry with momentum). SALVAGE classification from batch_first_pass. |
| **Current status** | Testing. SALVAGE. MGC PF 3.23 but dominated by 2025 gold rally. MCL marginal. |
| **Displacement target** | MomIgn (14) → clear advantage on gap value. |
| **Timeline** | **Uncertain.** SALVAGE means it needs a fix (true carry signal via v2 data) or a salvage attempt. The proxy version may not advance without front/back contract data (~$100-200 Databento purchase). |
| **What must happen** | Either: (a) forward evidence on the proxy version shows PF > 1.0 on MGC for 3+ months → enters watch on gap value. Or: (b) approve v2 data purchase, build true carry signal, re-test. |
| **Likelihood** | **MEDIUM.** The mechanism is real but the signal quality is questionable. If Treasury-Rolldown succeeds on rates, Commodity-Carry becomes the second CARRY strategy rather than the first — still valuable but lower urgency. |

**Portfolio upgrade if displaced:**
- Opens CARRY (0 → 1, or adds depth if Treasury-Rolldown is already there)
- Adds commodity carry diversity (MCL/MGC vs rates)
- Different horizon than equity strategies

---

## Ranking: Which Path Makes the Portfolio Stronger Fastest?

| Rank | Challenger | Eff. Score | Gaps | Timeline | Likelihood | Path |
|------|-----------|-----------|------|----------|-----------|------|
| **1** | Treasury-Rolldown | 20 | CARRY + Rates (2) | June 1 | HIGH | **Forward evidence → displace MomIgn at deadline** |
| **2** | VolManaged-Equity | 19 | VOL + MES (2) | 4-6 weeks | MEDIUM-HIGH | **Conversion → first-pass → conviction if ADVANCE** |
| **3** | Commodity-TS-Carry | 19 | CARRY (1) | Uncertain | MEDIUM | **Forward or v2 data → watch slot** |

---

## Single Best Path

**Treasury-Rolldown is the clear #1.** It's the only challenger that is:
- Already built (strategy.py exists)
- Already tested (PF 1.11, 79 trades, rate-neutral confirmed)
- Already scored above conviction threshold (rubric 18)
- Filling the TWO biggest portfolio gaps simultaneously
- On a defined timeline (June 1 MomIgn deadline)
- Requiring only forward evidence to earn the displacement

The upgrade path is: get Treasury-Rolldown into the forward runner →
accumulate 2-3 months of spread returns → apply displacement at June 1.

**VolManaged-Equity is the clear #2** and should be queued as the next
conversion slot after the current carry strategies are settled. It would
be the first VOLATILITY factor strategy to reach conviction and would
address the third-biggest factor gap (after CARRY and STRUCTURAL).

**Commodity-Carry is the #3** — valuable but blocked by signal quality.
It benefits from Treasury-Rolldown going first: if rates carry works,
the carry lookup is validated, and commodity carry gets a stronger
foundation for its v2 upgrade.

---

## Recommended Sequence

```
NOW:     Treasury-Rolldown accumulates forward evidence (already running)
JUNE 1:  Displace MomIgn → CARRY + Rates enter the portfolio
NEXT:    Open conversion slot for VolManaged-EquityIndex-Futures
         (fills VOL gap, simple to build, academic basis)
LATER:   Commodity-Carry v2 (after carry lookup is validated by
         Treasury-Rolldown results)
```

This sequence opens 3 new factor positions (CARRY, Rates, VOL) over
the next 3-4 months while removing MOMENTUM overcrowding. Each step
validates the next: Treasury-Rolldown validates carry lookup →
Commodity-Carry benefits. VolManaged validates vol-scaling → future
vol strategies benefit.
