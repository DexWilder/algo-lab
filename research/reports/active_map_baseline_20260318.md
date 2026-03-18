# FQL Active Map Baseline — 2026-03-18

*Official state-lock. All slot counts, rubric scores, and prioritization
notes are authoritative as of this date.*

---

## CORE (4 / 10 cap)

| Strategy | Asset | Session | Rubric | Role | Note |
|----------|-------|---------|--------|------|------|
| XB-PB-EMA-MES-Short | MES | Morning | 20 STRONG | Workhorse | Strongest core. Only MES. FULL_ON. |
| ORB-MGC-Long | MGC | Morning | 19 STRONG | Tail Engine | PF 1.99. Only positive forward PnL. |
| BB-EQ-MGC-Long | MGC | Morning | 18 STRONG | Tail Engine | 3x capital efficiency. Only MR in core. |
| PB-MGC-Short | MGC | Morning | 16 MARGINAL | Selective | **WEAKEST CORE INCUMBENT.** First slot to challenge with a stronger replacement. 9 trades in 6yr. |

## CONVICTION PROBATION (5 / 5 cap — all rubric >= 18)

| Strategy | Asset | Session | Rubric | Event? | Gap Filled |
|----------|-------|---------|--------|--------|------------|
| PreFOMC-Drift-Equity | MNQ | FOMC overnight | 22 ELITE | 0.5 slot | EVENT factor |
| DailyTrend-MGC-Long | MGC | Daily close | 21 ELITE | No | Horizon (daily) |
| MomPB-6J-Long-US | 6J | US session | 19 STRONG | No | FX asset class |
| NoiseBoundary-MNQ-Long | MNQ | All-day | 18 STRONG | No | MNQ workhorse |
| TV-NFP-High-Low-Levels | MNQ | NFP multi-day | 18 STRONG | 0.5 slot | EVENT factor |

## WATCH (5 / 3 cap — 2 over, deadline pressure)

| Strategy | Asset | Rubric | Deadline | Promote If | Archive If | Priority Note |
|----------|-------|--------|----------|------------|------------|---------------|
| FXBreak-6J | 6J | 17 | 2026-06-01 | Fwd PF > 1.2 / 30 trades | Fwd PF < 0.95 / 30 trades | FX short-bias niche |
| TTMSqueeze-M2K | M2K | 17 | 2026-06-01 | Fwd PF > 1.3 / 20 trades | Fwd PF < 1.0 / 20 trades | Only VOL factor strategy |
| GapMom | multi | 16 | 2026-06-01 | Non-MGC edge improves | Just weaker ORB-MGC | PF 1.72 but concentrated |
| CloseVWAP-M2K | M2K | 16 | 2026-06-01 | Decay stabilizes + fwd PF > 1.2 | Decay continues | **FIRST-EXPIRY.** DECAYING half-life. |
| MomIgn-M2K | M2K | 14 | 2026-06-01 | Fwd PF > 1.3 / 20 trades | Fwd PF < 1.0 / 20 trades | **FIRST-EXPIRY.** Lowest rubric in watch. |

## TESTING (6 — uncapped)

| Strategy | Stage | Deadline | Factor |
|----------|-------|----------|--------|
| RangeExpansion-MCL | Downgraded | 2026-04-18 | VOLATILITY |
| ORBEnh-M2K-Short | Downgraded | 2026-05-01 | MOMENTUM |
| VWAPMR-MCL-Short | Downgraded | 2026-05-01 | MEAN_REVERSION |
| MomPB-6E-Long-US | First pass | — | MOMENTUM |
| Commodity-TermStructure-Carry | First pass | — | CARRY |
| Treasury-Rolldown-Carry-Spread | First pass | — | CARRY |

---

## Slot Rules (Authoritative)

### Conviction Entry
- Rubric >= 18 required. No exceptions.
- If conviction is full (5 slots), new candidate must score higher than
  weakest incumbent to displace. Gap-filling candidates get +2 bonus.
- Event sleeves count at 0.5 slots.

### Watch Entry
- Rubric 14-17 with a real mechanism (Q1 >= STRONG).
- New sub-18 candidates do NOT enter watch unless they displace an
  existing watch name by scoring higher.
- Every watch strategy has a deadline, promote condition, and archive
  condition. No indefinite survival. Maximum 16 weeks.

### Core Entry
- Requires conviction probation promotion with forward evidence.
- If core is full (10 slots), promoted strategy must displace the
  weakest core incumbent.

### Displacement Priority
- **First core slot to challenge:** PB-MGC-Short (16 MARGINAL)
- **First watch slots to expire:** MomIgn-M2K (14), CloseVWAP-M2K (16)

---

## Concentration State

| Dimension | Current | Cap | Status |
|-----------|---------|-----|--------|
| MOMENTUM factor | ~55% | 50% hard | **OVER** — no new entrants |
| Morning session | 5 | 5 hard | **AT CAP** — displacement only |
| MGC asset | 4 (3 core + 1 conviction) | 5 hard | AT SOFT CAP |
| MNQ asset | 3 (1 conviction + 2 event) | 5 hard | Room |
| M2K asset | 3 (watch only) | 5 hard | Room |
| 6J asset | 1 conviction + 1 watch | 5 hard | Room |
| MCL asset | 0 active | 5 hard | **GAP** |
| Rates asset | 0 active | 5 hard | **GAP** |
| CARRY factor | 0 active | — | **GAP** — highest priority |
| EVENT factor | 2 conviction | — | Growing |
| VOLATILITY factor | 1 watch | — | Thin |
| STRUCTURAL factor | 0 active | — | **GAP** |

---

## Pipeline Candidates (Near-Term)

| Candidate | Stage | Factor | Could Challenge |
|-----------|-------|--------|-----------------|
| Commodity-TermStructure-Carry | Testing | CARRY | Watch displacement (fills GAP) |
| Treasury-Rolldown-Carry-Spread | Testing | CARRY | Watch displacement (fills GAP) |
| MomPB-6E-Long-US | Testing | MOMENTUM | Blocked (MOMENTUM > 50%) |

---

*This baseline supersedes all prior portfolio maps. Next review: 2026-06-01
(watch strategy deadlines) or earlier if a testing-stage candidate advances.*
