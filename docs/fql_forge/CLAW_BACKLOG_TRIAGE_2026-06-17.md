# Claw Backlog Triage + Track-1 Queue — 2026-06-17

> Triage of the full 878-note Claw harvest backlog (the broken Claw→Claude handoff, now processed). Report-only. Mechanism-level, deduplicated, bucketed. Plus the boundary-test result on the gold/rates lead and the first screen off this triage.

## Backlog composition (878 notes)
| Bucket | Count | % | Theme |
|---|--:|--:|---|
| TESTABLE-NOW (distinct, non-exhausted) | ~80 | 9% | but many need data we DON'T hold (see correction) |
| LEVER-B / FEED-BLOCKED | ~485 | 55% | Treasury auction (47), PPP/CPI pipeline (37), curve construction (35), EIA/OPEC (17), VIX curve (9), COT (3) |
| DUPLICATE / EXHAUSTED | ~270 | 31% | London FX (47), PPP FX carry (88), Kalman stat-arb (59), value-rebalance-timing (60), WTI carry (14), vol overlays (88) |
| UNSAFE/INVALID | ~0 | 0% | **Claw produces NO hard kills — misconfiguration** |
| NEEDS REVIEW | 41 | 5% | underspecified |

## In-house-data correction (applied to the triage)
In-house 5m data: `6B 6E 6J ES M2K MCL MES MGC MNQ MYM ZB ZF ZN`. **No ZT/ZC/ZS/NG/SI/HG, no 13th-month contracts, no FRED/USDA/BLS point-in-time feeds.** So several agent "testable-now" items are actually FEED-BLOCKED: WASDE grains (#T4, needs ZC/ZS), commodity carry/skew universe (#T5/#T9, needs ZC/ZS/NG/SI/HG), ZT policy momentum (#T11, no ZT), 13th-month WTI carry (#T1), BoJ/FRED carry (#T15). Reclassified to Lever-B.

## Genuinely in-house testable-now (daily, distinct-driver, non-MNQ-cousin)
| # | Mechanism | Asset/driver | Status |
|---|---|---|---|
| **#T2** | Dual-Thrust breakout (asymmetric prior-day thresholds) | ZN/MCL rates+crude | **SCREENED 2026-06-17b → 10/10 KILL** (breakout family doesn't generalize off-MNQ/gold) |
| #T7 | Afternoon range-compression → break (vol expansion, not reversion) | ZN rates | QUEUED (in-house; needs 5m volume) |
| #T12 | CPI-acceleration regime rotation gold↔rates | MGC/ZN inflation | QUEUED (have `forge_cpi_calendar_verified`; near-daily) |
| #T8 | Mid-month payday flow long | MES equity | low pri (equity + sparse 12/yr) |
| #T3/#T6 | Pre-London compression / Tokyo VWAP | 6E/6J FX | screenable but 2024+ short sample |
| #T14 | NFP frozen-zone breakout | MES/MGC/6E | sparse event (off-target for daily WH2) |

**Next Track-1 screens: #T7 (ZN afternoon compression) and #T12 (CPI gold↔rates rotation)** — the two in-house, distinct-driver, daily-ish leads not in the breakout family that just died.

## Boundary-test result — gold/rates conditioning (`forge_cycle_2026-06-17a`)
Predeclared floors (retain ≥40%, n≥120, PF lift ≥0.15), ZN-trend bands × lookbacks:
- **MGC-ORB × rates-up → WEAK_OR_NOISE** (1/5 eligible configs directional, 20%). The PF 1.672 was a single-lookback artifact. **Lead killed.** (Corrects last turn's "opposite-regime complementarity" — ORB is rates-agnostic.)
- **MGC-prior_day_break × rates-down → SEPARATE_SLEEVE_VARIANT_CANDIDATE** (10/11 eligible directional, 91%; PF lift +0.26 to +0.60 across lookbacks 21–126; retains 52–55%). Robust: the prior_day_break gold edge concentrates when rates fall (PF ~1.7–1.9 vs ~0.9–1.1 when rising). **Real risk-timing gate / sleeve variant** — but still in-sample (no OOS on the gate), still gold, and gating ~halves cadence (→~25/yr). NOT a new engine, NOT daily WH2.

## Lever-B feed highlights (from backlog, by feed)
- **Treasury auction timestamps** (47 notes, 5 mechanism families) — single highest unlock; public Fiscal Data API. Maps to Lever-B #2.
- **Rates curve construction / F2 contracts** (35 notes) — Lever-B #1 (top daily-WH2 unlock).
- PPP/real-rate pipeline (37), EIA/OPEC (17), VIX curve (9), COT (3).

## Claw config findings (for operator — Claw is automation-owned; recommend, don't self-edit)
1. **Fix the 0-kills misconfiguration:** any mechanism on the no-repeat archive = KILL, not NEEDS_REVIEW. Claw is deferring instead of terminating.
2. **Stop re-harvesting 6 saturated families** (cap at one canonical each): London FX (47), PPP FX carry (88), Kalman stat-arb (59), value-rebalance-timing (60), WTI carry (14), non-equity vol overlays (88). These = ~270 notes / 31% of backlog wasted.
3. **Up-weight EVENT sourcing** (only 9%) and **frequency-first** (mission = daily elite).
4. **Add cadence as a required field** (most notes omit expected trades/year).
5. Route sizing/governance overlays out of the harvest inbox into a governance template.

## No-repeat archive — additions (do not re-surface / do not re-screen)
Breakout family off-MNQ/gold (ORB, donchian, **dual-thrust** — all KILL); the 6 saturated Claw families above; MGC-ORB rates conditioning (noise). Keep: MGC-prior_day_break rates-down gate (real, pending OOS).

## Boundaries
Report-only. No activation/wiring/registry/portfolio/scheduler mutation. Claw config changes are recommendations for the operator (Claw is automation-owned — not self-edited).
