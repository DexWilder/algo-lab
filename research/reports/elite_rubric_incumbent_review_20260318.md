# Elite Rubric — Incumbent Strategy Review
## 2026-03-18

*Scored against the 6-question Elite Review Rubric.*
*Q1=Mechanism, Q2=Durability, Q3=Best-in-family, Q4=Portfolio fit,
Q5=Evidence, Q6=Worth attention. Each 1-4 (WEAK-ELITE).*

---

## CORE STRATEGIES (5)

### 1. XB-PB-EMA-MES-Short — 20/24 STRONG

| Q1 | Q2 | Q3 | Q4 | Q5 | Q6 | Total |
|----|----|----|----|----|----| ------|
| 3 | 3 | 4 | 3 | 3 | 4 | **20** |

Only MES strategy in the portfolio. FULL_ON controller action (highest
activation at 0.82). PF 1.31, 88 trades, 15.5% PnL share, 100% param
stability. Half-life HEALTHY, contribution ADDS VALUE — the only core
strategy with that distinction. Forward PnL is negative (-$362 on 6
trades) but sample is tiny. Drift alerts in midday/afternoon are actually
positive (leakage into adjacent sessions, not degradation). Mechanism is
clear: pullback into EMA trend, short bias on MES. ELITE on best-in-family
(only MES strategy) and worth-attention (low maintenance, strong metrics).

**Verdict: Deserves its slot.** Strongest core strategy by activation score
and contribution status.

---

### 2. ORB-MGC-Long — 19/24 STRONG

| Q1 | Q2 | Q3 | Q4 | Q5 | Q6 | Total |
|----|----|----|----|----|----| ------|
| 3 | 3 | 3 | 3 | 3 | 4 | **19** |

Backtest PF 1.99 (second highest in core), 62 trades, 16.9% PnL share.
Morning session ORB on gold — clear structural mechanism (opening range
defines the day's trend on metals). Only forward strategy with positive
PnL (+$184 on 2 trades). Parameter stability 100%. Midday session ALARM
is a concern (barely positive in that window) but the core morning edge
is intact. Regime gate (avoid LOW_VOL) is appropriate.

**Verdict: Deserves its slot.** Strong tail-engine characteristics
(moderate frequency, high PF). Only concern is MGC crowding (4 strategies
on MGC already at soft cap).

---

### 3. BB-EQ-MGC-Long — 18/24 STRONG

| Q1 | Q2 | Q3 | Q4 | Q5 | Q6 | Total |
|----|----|----|----|----|----| ------|
| 3 | 3 | 4 | 2 | 3 | 3 | **18** |

3x capital efficiency (5.6% of trades → 16.6% of PnL). PF 1.68, 22
trades in 6 years — genuine tail engine. Only mean-reversion strategy
in core, providing factor diversification (everything else is momentum
or breakout). Afternoon session ALARM is real (5 trades, 20% WR, -$27
avg PnL) but the strategy's edge is in morning compression/release, not
afternoon. Zero forward trades so far — needs monitoring. Q4 scores
lower because it adds to MGC crowding (4th MGC strategy).

**Verdict: Deserves its slot** for now. Factor diversification (only
MR in core) justifies the MGC concentration cost. Vulnerable if a
non-MGC mean-reversion strategy is validated.

---

### 4. PB-MGC-Short — 16/24 MARGINAL

| Q1 | Q2 | Q3 | Q4 | Q5 | Q6 | Total |
|----|----|----|----|----|----| ------|
| 3 | 2 | 2 | 2 | 2 | 3 | **14** → raised to **16** |

Backtest PF 2.36 but only 9 trades in 6 years (4.8% PnL share). The
deepest filter stack in the portfolio (6 layers) produces a high-quality
but extremely rare signal. Forward PnL is -$316 on 3 trades — too thin
to draw conclusions. The mechanism is real (pullback into trend, short
MGC in high-vol trending) but the trade count makes durability assessment
unreliable. Same family as XB-PB-EMA (pullback), same session (morning),
same direction logic — but different asset (MGC vs MES) and opposite
direction (short vs short), which provides some diversification.

Raised from raw 14 to 16 because the 6-layer filter is genuinely
selective (not broken — just rare) and high-vol-trending regime
requirement is structurally sound.

**Verdict: Vulnerable.** Low trade count makes all metrics unreliable.
4th MGC strategy at the soft cap. If it generates <5 more trades in
the next 6 months, the slot cost exceeds the information value. Not an
immediate downgrade — but first to go if a non-MGC candidate needs the
slot.

---

### 5. VWAP-MNQ-Long — 15/24 MARGINAL

| Q1 | Q2 | Q3 | Q4 | Q5 | Q6 | Total |
|----|----|----|----|----|----| ------|
| 3 | 2 | 2 | 2 | 3 | 3 | **15** |

Historical backbone: 163 trades, 32.4% PnL share, PF 1.26. But the
controller has already moved it to PROBATION action (activation 0.51,
lowest among core). Afternoon session ALARM (7 trades, 14.3% WR, -$41
avg PnL) is a structural concern — the afternoon edge is broken, not
just noisy. Zero forward trades despite being the highest-frequency
strategy, which is unexpected and warrants investigation. Competes
directly with NoiseBoundary-MNQ-Long (same asset, direction, session
overlap) — and NoiseBoundary has WF 10/10 PERFECT vs VWAP's adequate
but unexceptional walk-forward.

**Verdict: Vulnerable.** Controller already flagged it. Afternoon ALARM
is real. NoiseBoundary-MNQ may be the stronger MNQ-long representative.
Should be reviewed for potential replacement or session restriction
(remove afternoon, keep morning-only).

---

## OFFICIAL PROBATION STRATEGIES (5)

### 6. PreFOMC-Drift-Equity — 22/24 ELITE

| Q1 | Q2 | Q3 | Q4 | Q5 | Q6 | Total |
|----|----|----|----|----|----| ------|
| 4 | 3 | 4 | 4 | 3 | 4 | **22** |

Academic basis (Lucca & Moench 2015). PF 1.73, Sharpe 3.85. Zero
momentum correlation (-0.004). Walk-forward 2.03/1.46 (both halves
strong). Fills EVENT factor gap. Zero session overlap with any other
strategy. Only weakness: forward evidence is thin (event-driven, ~8
trades/year). 2023 underperformance has a structural explanation (Fed
pause). PASS 7/8 validation.

**Verdict: Elite candidate.** The best diversification bet in the
portfolio. If forward evidence confirms at 8+ trades, this is a
high-conviction promotion.

---

### 7. DailyTrend-MGC-Long — 21/24 ELITE

| Q1 | Q2 | Q3 | Q4 | Q5 | Q6 | Total |
|----|----|----|----|----|----| ------|
| 3 | 4 | 4 | 4 | 3 | 3 | **21** |

PF 3.65 (highest in entire registry), Sharpe 5.13, 44 trades. Walk-
forward H1=1.14, H2=5.62. PASS 7/8 validation. First multi-horizon
strategy (daily bars). Adds genuine horizon diversification. Only daily
strategy in the portfolio. Bootstrap CI lower bound 1.38 (strong). One
concern: adds to MGC concentration (5th MGC including core). But the
horizon separation (daily vs intraday) means zero signal overlap with
ORB-MGC or BB-EQ-MGC.

**Verdict: Elite candidate.** The PF and horizon diversification are
genuine. Forward evidence needed (15 trades target — ~6 months at
current frequency). Worth the MGC concentration cost because the horizon
is truly different.

---

### 8. MomPB-6J-Long-US — 19/24 STRONG

| Q1 | Q2 | Q3 | Q4 | Q5 | Q6 | Total |
|----|----|----|----|----|----| ------|
| 3 | 3 | 3 | 4 | 2 | 4 | **19** |

First validated non-equity strategy. PF 1.58, Sharpe 2.92, 43 trades.
Walk-forward 1.76/1.45 (both strong). 6E cross-validates PF 1.72. Fills
FX asset gap and adds non-momentum carry exposure (secondary factor).
Carry bias filter would improve PF to 1.67 (queued, not applied).
Evidence is thin (0 forward trades yet) — the score reflects backtest
strength plus the carry lookup research opportunity.

**Verdict: Deserves its slot.** Strongest FX candidate. Carry filter
improvement queued. Monitor forward evidence.

---

### 9. FXBreak-6J-Short-London — 17/24 MARGINAL-STRONG boundary

| Q1 | Q2 | Q3 | Q4 | Q5 | Q6 | Total |
|----|----|----|----|----|----| ------|
| 3 | 3 | 3 | 3 | 2 | 3 | **17** |

PF 1.20 (lowest of the 5 official probation). Walk-forward 1.08/1.35
(both positive but H1 is thin). Complementary to MomPB-6J (different
session, direction, entry logic — CONFIRMED complementary). 125 trades
provides good sample. Carry bias filter would improve PF to 1.36 with
Sharpe doubling to 2.03 (biggest improvement of any strategy — queued).
Without the carry filter, the raw edge is marginal. With it, STRONG.

**Verdict: On the boundary.** The carry filter research is the deciding
factor. If formal carry_lookup confirms the improvement, score rises to
19-20. If not, this is the weakest official probation strategy and first
to be replaced by a stronger candidate.

---

### 10. TV-NFP-High-Low-Levels — 18/24 STRONG

| Q1 | Q2 | Q3 | Q4 | Q5 | Q6 | Total |
|----|----|----|----|----|----| ------|
| 3 | 3 | 4 | 4 | 2 | 2 | **18** |

PF 1.66, Sharpe 3.25 after salvage (short side removed — PF 0.38).
Walk-forward 1.50/1.61 (both halves consistent). Fills EVENT factor
gap alongside PreFOMC. Zero overlap with any non-event strategy. First
successful salvage in the system. Watch items: T3 weakening (PF 1.09),
Bootstrap CI 0.93 (below 1.0). Half-life flagged ARCHIVE_CANDIDATE —
needs monitoring. Evidence score low (0 forward trades, ~12 events/year).
Attention score low because of the watch items that need active tracking.

**Verdict: Deserves its slot** but with active monitoring. The EVENT
factor gap-fill and NFP-specific coverage justify the attention cost.
If watch items worsen, this is a downgrade candidate.

---

## ADDITIONAL PROBATION (9)

### 11. NoiseBoundary-MNQ-Long — 18/24 STRONG

| Q1 | Q2 | Q3 | Q4 | Q5 | Q6 | Total |
|----|----|----|----|----|----| ------|
| 3 | 3 | 4 | 2 | 3 | 3 | **18** |

WF 10/10 PERFECT. 609 trades, PF 1.28, Sharpe 1.40. Academic source.
Cross-asset edge on MES+MYM. Forward PnL -$531 on 3 trades (tiny
sample). Kill flag for redundancy with Donchian-MNQ — but NoiseBoundary
is the stronger representative. Q4 lower because MNQ-long is already
covered by VWAP-MNQ. Could potentially replace VWAP-MNQ as the primary
MNQ workhorse if VWAP continues to underperform.

**Verdict: Strong workhorse candidate.** May displace VWAP-MNQ-Long.

---

### 12. TTMSqueeze-M2K-Short — 17/24 MARGINAL-STRONG

| Q1 | Q2 | Q3 | Q4 | Q5 | Q6 | Total |
|----|----|----|----|----|----| ------|
| 3 | 3 | 3 | 3 | 2 | 3 | **17** |

PF 1.97, 48 trades. First vol-expansion strategy. M2K adds asset
diversification away from MNQ/MGC. Short direction adds to short
coverage. Validation 5.5, param stability 86% (slightly below 100%).

**Verdict: Worth its slot.** VOLATILITY factor representation.

---

### 13. GapMom-Multi — 16/24 MARGINAL

| Q1 | Q2 | Q3 | Q4 | Q5 | Q6 | Total |
|----|----|----|----|----|----| ------|
| 3 | 2 | 2 | 2 | 2 | 3 | **14** → **16** |

PF 1.72 on MGC-long, WF 6.7/10, param stability 83%. Multi-asset
but best results are MGC-specific. Adds to MGC and morning
concentration. Mechanism is real (gap + momentum) but family is
crowded (breakout x morning). Raised to 16 because MCL cross-asset
potential provides energy coverage option.

**Verdict: Vulnerable.** MGC-concentrated, morning-concentrated.

---

### 14. CloseVWAP-M2K-Short — 16/24 MARGINAL

| Q1 | Q2 | Q3 | Q4 | Q5 | Q6 | Total |
|----|----|----|----|----|----| ------|
| 3 | 2 | 3 | 3 | 2 | 3 | **16** |

PF 1.42, 146 trades. Close session (unique). Mean-reversion (factor
diversification). DECAYING half-life is the main concern. Stabilizer
role justified by close-session coverage.

**Verdict: On watch.** Decay signal is real. Worth keeping for session
diversification but review at next checkpoint.

---

### 15. Donchian-MNQ-Long-GRINDING — 14/24 MARGINAL

| Q1 | Q2 | Q3 | Q4 | Q5 | Q6 | Total |
|----|----|----|----|----|----| ------|
| 3 | 3 | 1 | 2 | 2 | 3 | **14** |

PF 1.6, 47 trades, 100% param stability. But kill flag: redundancy
with NoiseBoundary-MNQ (corr=0.374). Same asset, same direction, same
family logic. NoiseBoundary is clearly stronger (WF 10/10, 609 trades
vs 47). Q3 = WEAK because it IS the inferior family representative.

**Verdict: Archive candidate.** NoiseBoundary supersedes this.

---

### 16. MomIgn-M2K-Short — 14/24 MARGINAL

| Q1 | Q2 | Q3 | Q4 | Q5 | Q6 | Total |
|----|----|----|----|----|----| ------|
| 2 | 2 | 2 | 3 | 2 | 3 | **14** |

PF 1.24, 90 trades. Validation collapsed from 9.0/10 (2yr) to 6.0/10
(6.7yr) — the edge narrowed significantly with more data. Mechanism
scored lower because VWAP cross + volume surge is common and the
extended-history degradation suggests it may be noise. M2K midday is a
useful session/asset slot.

**Verdict: Vulnerable.** Edge degradation on extended history is a
yellow flag. The M2K midday slot has value, but this may not be the
right occupant.

---

### 17. ORBEnh-M2K-Short — 13/24 MARGINAL

| Q1 | Q2 | Q3 | Q4 | Q5 | Q6 | Total |
|----|----|----|----|----|----| ------|
| 3 | 2 | 2 | 2 | 1 | 3 | **13** |

Validation 8.0/10 but only on 2-year data. No extended-history
confirmation. No PF in registry. Half-life ARCHIVE_CANDIDATE. Morning
M2K is not a gap. 100% param stability is good but sample-dependent.

**Verdict: Weakest probation strategy.** Needs extended-history
validation before any further investment. Archive candidate if
validation fails.

---

### 18. VWAPMR-MCL-Short — 13/24 MARGINAL

| Q1 | Q2 | Q3 | Q4 | Q5 | Q6 | Total |
|----|----|----|----|----|----| ------|
| 2 | 2 | 2 | 3 | 1 | 3 | **13** |

Validation 6.5/10. Param stability 70% (weakest in entire portfolio).
Half-life ARCHIVE_CANDIDATE. MCL morning is a useful slot (energy gap)
but this occupant may not be strong enough. No PF in registry. Only
2-year validation.

**Verdict: Weakest alongside ORBEnh.** MCL energy slot has value, but
this strategy may not deserve it. Archive if param stability doesn't
improve on extended history.

---

### 19. RangeExpansion-MCL — 14/24 MARGINAL

| Q1 | Q2 | Q3 | Q4 | Q5 | Q6 | Total |
|----|----|----|----|----|----| ------|
| 3 | 1 | 3 | 3 | 2 | 2 | **14** |

WF 10/10 PERFECT. PF 1.46, 214 trades. But half-life decay is severe:
Sharpe 2.39 → 0.46 (1yr) → -0.13 (6mo). The edge is actively dying.
Q2 = WEAK because recent performance is clearly degrading. MCL coverage
is valuable (first energy strategy) but not if the edge is gone.

**Verdict: Active decay — review immediately.** If the next 3 months
confirm the Sharpe trajectory, archive. The WF 10/10 score is
historical, not predictive of future performance.

---

## RANKED SUMMARY

### By Rubric Score

| Rank | Strategy | Score | Rating | Slot Status |
|------|----------|-------|--------|-------------|
| 1 | PreFOMC-Drift-Equity | 22 | **ELITE** | Deserves slot — best diversification bet |
| 2 | DailyTrend-MGC-Long | 21 | **ELITE** | Deserves slot — unique horizon |
| 3 | XB-PB-EMA-MES-Short | 20 | **STRONG** | Deserves slot — strongest core |
| 4 | ORB-MGC-Long | 19 | **STRONG** | Deserves slot — strong tail engine |
| 5 | MomPB-6J-Long-US | 19 | **STRONG** | Deserves slot — FX asset gap |
| 6 | BB-EQ-MGC-Long | 18 | **STRONG** | Deserves slot — MR factor diversification |
| 7 | NoiseBoundary-MNQ-Long | 18 | **STRONG** | Deserves slot — potential VWAP replacement |
| 8 | TV-NFP-High-Low-Levels | 18 | **STRONG** | Deserves slot (with monitoring) — EVENT gap |
| 9 | FXBreak-6J-Short-London | 17 | **MARGINAL+** | Boundary — carry filter is the swing factor |
| 10 | TTMSqueeze-M2K-Short | 17 | **MARGINAL+** | Worth slot — VOL factor representation |
| 11 | CloseVWAP-M2K-Short | 16 | **MARGINAL** | On watch — decay signal |
| 12 | GapMom-Multi | 16 | **MARGINAL** | Vulnerable — MGC/morning concentrated |
| 13 | PB-MGC-Short | 16 | **MARGINAL** | Vulnerable — too few trades |
| 14 | VWAP-MNQ-Long | 15 | **MARGINAL** | Vulnerable — controller already flagged |
| 15 | Donchian-MNQ-Long | 14 | **MARGINAL** | Archive candidate — superseded by NoiseBoundary |
| 16 | MomIgn-M2K-Short | 14 | **MARGINAL** | Vulnerable — edge degraded on extended data |
| 17 | RangeExpansion-MCL | 14 | **MARGINAL** | Active decay — review immediately |
| 18 | ORBEnh-M2K-Short | 13 | **MARGINAL** | Weakest — needs extended validation |
| 19 | VWAPMR-MCL-Short | 13 | **MARGINAL** | Weakest — 70% param stability |

---

## PORTFOLIO SLOT ASSESSMENT

### Strongest Slots (8 strategies earning their place)

1. **PreFOMC-Drift** — ELITE, fills EVENT gap, zero correlation
2. **DailyTrend-MGC** — ELITE, fills horizon gap, PF 3.65
3. **XB-PB-EMA-MES** — STRONG, only MES, ADDS VALUE contribution
4. **ORB-MGC** — STRONG, tail engine, only positive forward PnL
5. **MomPB-6J** — STRONG, fills FX gap, carry filter upside
6. **BB-EQ-MGC** — STRONG, only core MR, 3x capital efficiency
7. **NoiseBoundary-MNQ** — STRONG, WF 10/10, workhorse candidate
8. **TV-NFP-Levels** — STRONG, fills EVENT gap (with active watch items)

### Vulnerable Slots (5 strategies at risk)

9. **VWAP-MNQ-Long** — Controller already at PROBATION action. Afternoon
   ALARM. NoiseBoundary may be the better MNQ-long representative.
10. **PB-MGC-Short** — 9 trades in 6 years. Unreliable metrics. 4th MGC
    strategy at soft cap.
11. **GapMom** — MGC-concentrated, morning-concentrated. Family is crowded.
12. **MomIgn-M2K** — Edge degraded from 9.0 to 6.0 on extended data.
13. **RangeExpansion** — Active decay. Sharpe -0.13 over last 6 months.

### Archive Candidates (3 strategies likely not earning their slot)

14. **Donchian-MNQ-Long** — Superseded by NoiseBoundary. Redundancy
    kill flag. Clear inferior family representative.
15. **ORBEnh-M2K-Short** — No extended-history validation. Half-life
    ARCHIVE_CANDIDATE. Weakest evidence base.
16. **VWAPMR-MCL-Short** — 70% param stability (worst). Half-life
    ARCHIVE_CANDIDATE. MCL slot is valuable but this occupant is weak.

### Best Refinement Candidates (3)

1. **FXBreak-6J-Short-London** — Carry filter research is queued and
   could raise score from 17 to 20. Biggest single-improvement
   opportunity in the portfolio.
2. **CloseVWAP-M2K-Short** — Close session is unique and valuable.
   If decay stabilizes, this is a solid stabilizer. If decay continues,
   replace with a better close-session strategy.
3. **VWAP-MNQ-Long** — Morning-only session restriction could save it.
   Remove afternoon exposure (ALARM), keep the morning edge (HEALTHY).
   Or accept that NoiseBoundary is the successor and archive gracefully.
