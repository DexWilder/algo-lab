# Treasury-Rolldown-Carry-Spread — Formal First-Pass Report
## 2026-03-18

---

## Classification: MONITOR

Not ADVANCE. Not REJECT. The walk-forward split is the deciding factor.

---

## Results Summary

| Metric | Equal Notional | DV01 Normalized |
|--------|---------------|-----------------|
| Trades | 79 | 79 |
| PF | 1.11 | 1.10 |
| WR | 48% | 56% |
| Total PnL | +$9,898 | +$3,141 |
| Annualized Sharpe | 0.14 | 0.12 |
| Max DD | $24,062 | $7,195 |
| WF H1 PF | **1.58** | 0.94 |
| WF H2 PF | **0.69** | 1.31 |
| Rank changes | 33/79 (42%) | 33/79 (42%) |
| Duration corr | 0.027 | 0.027 |

## Walk-Forward Analysis (Critical Finding)

The equal-notional variant shows a clear walk-forward split:
- **H1 (2019-2022): PF 1.58** — strong, driven by the 2020-2022 period
- **H2 (2023-2026): PF 0.69** — failing, driven by 2023 and 2025 weakness

The DV01 variant shows the inverse pattern:
- **H1: PF 0.94** — marginal
- **H2: PF 1.31** — improving

This means the two variants capture different aspects of the curve:
- Equal notional profits from ZB-vs-ZF spread (duration-weighted, benefits
  from large curve moves in 2020-2022)
- DV01 normalized profits from carry-adjusted spread (neutralized duration,
  benefits from quieter 2023-2024 period)

Neither variant has consistent walk-forward stability across both halves.
This prevents ADVANCE classification.

## Year-by-Year (Equal Notional)

| Year | N | PF | PnL | Assessment |
|------|---|-----|------|-----------|
| 2019 | 4 | 0.73 | -$1,852 | Loss (short sample) |
| 2020 | 12 | 1.68 | +$8,828 | Strong (COVID curve steepening) |
| 2021 | 12 | 1.96 | +$10,383 | Strong (continued steepening) |
| 2022 | 12 | 1.93 | +$12,070 | **Strong (rate shock — best year)** |
| 2023 | 12 | 0.65 | -$8,227 | Loss (curve normalized) |
| 2024 | 12 | 1.45 | +$3,680 | Moderate recovery |
| 2025 | 12 | 0.23 | -$9,609 | **Loss (worst year)** |
| 2026 | 3 | 0.00 | -$5,375 | Loss (ongoing) |

**Pattern:** Strong in curve-reshaping regimes (2020-2022). Weak when
the curve is stable or normalizing (2023, 2025-2026). This is
regime-dependent behavior — not surprising for a carry/curve strategy,
but it means the edge is intermittent.

## Tenor Pair Dominance

| Pair | N | % | PnL | PF | Assessment |
|------|---|---|------|-----|-----------|
| ZF/ZB (long 5Y, short 30Y) | 41 | 52% | +$22,695 | 1.48 | **All the profit** |
| ZB/ZF (long 30Y, short 5Y) | 30 | 38% | -$11,266 | 0.71 | All the loss |
| Others | 8 | 10% | -$1,531 | — | Marginal |

The strategy is effectively a ZF-vs-ZB spread bet. When ZF outperforms
ZB (curve flattens from the long end), it wins. When ZB outperforms ZF
(curve steepens), it loses. The carry ranking correctly identifies which
direction to bet — but only 52% of the time.

## Duration Exposure Check

Correlation of spread PnL with ZN monthly return: **0.027**

The spread IS rate-neutral. This is confirmed. The strategy does not
have hidden directional exposure. It profits from curve shape changes,
not rate level changes.

## Displacement Check

```
Candidate: Treasury-Rolldown-Carry-Spread
Rubric Score: 18/24 (raw), 20 effective with +2 gap bonus
Factor: CARRY  Session: monthly  Asset: ZN/ZF/ZB

DISPLACEMENT CHECK 1: Core — PB-MGC-Short (16/24)
  Does this candidate beat it?  [X] YES (20 vs 16)
  Same asset/session overlap?   [ ] NO — different asset class entirely
  If YES: portfolio gains CARRY factor + Rates asset class.
  VERDICT: Would displace on rubric, but WF instability weakens the case.
  Not ready for core displacement without forward evidence.

DISPLACEMENT CHECK 2: Watch — MomIgn-M2K-Short (14/24)
  Does this candidate beat it?  [X] YES (20 vs 14, +6 points)
  VERDICT: DECISIVE advantage. Even with MONITOR classification,
  the gap value (CARRY + Rates) far exceeds MomIgn's contribution
  (MOMENTUM overcrowded, no forward evidence, validation collapsed).

DISPLACEMENT CHECK 3: Gap Value
  Fills CARRY factor gap?    [X] YES (0 active)
  Fills Rates asset gap?     [X] YES (0 active)
  Fills session gap?         [ ] NO
  Gaps filled: 2
  Gap bonus: +2

DISPLACEMENT VERDICT:
  [X] DISPLACE watch name — earns MomIgn's slot at June 1 deadline
      even at MONITOR classification, because:
      1. Gap value (2 gaps) exceeds any other candidate
      2. MomIgn has 0 forward evidence and rubric 14
      3. The CARRY factor has 0 representation in any active bucket
      4. Even a MONITOR-quality CARRY strategy is more portfolio-
         valuable than a MARGINAL MOMENTUM strategy in an overcrowded factor
  [ ] Does NOT displace core (PB-MGC) yet — needs forward evidence
```

## What This Changes

**MomIgn is under MORE pressure, not less.** Even though Treasury-Rolldown
classified as MONITOR (not ADVANCE), the displacement case against MomIgn
strengthened because:

1. The MONITOR classification is honest — PF 1.11 with WF instability is
   not elite. But the CARRY gap is so large (0 active) that even a
   marginal CARRY signal is more valuable than a 14th MOMENTUM strategy.

2. The year-by-year shows the strategy IS profitable in curve-reshaping
   regimes (2020-2022). The question is whether the current quiet regime
   (2025-2026) is temporary or permanent. A watch slot gives time to
   find out without committing to conviction.

3. MomIgn's counterargument would need to be: "I'm accumulating strong
   forward evidence that justifies keeping a MOMENTUM strategy instead
   of opening the CARRY factor." MomIgn has 0 forward trades.

**PB-MGC-Short is NOT under more pressure from this result.** The WF
instability means Treasury-Rolldown is not core-ready. It needs forward
evidence to challenge core.

**The displacement decision at June 1 becomes:**
- If Treasury-Rolldown has any forward evidence (even 2-3 spread returns)
  → replaces MomIgn in watch. This is the base case.
- If Treasury-Rolldown has no forward evidence AND shows continued 2026
  weakness → stays in testing, MomIgn still expires, slot opens for
  VolManaged instead.

## VolManaged Fallback Assessment

This MONITOR classification does NOT trigger the VolManaged fallback.
The fallback triggers if Treasury-Rolldown "weakens materially" — defined
as forward PF collapsing, mechanism breaking, or rubric dropping below 16.

The rubric is still 18 (mechanism is sound, rate-neutrality confirmed,
gap value is real). The WF instability is a known concern, not a
mechanism failure. Treasury-Rolldown remains the lead challenger.

VolManaged remains #2 — next conversion slot after the June 1 decision.
