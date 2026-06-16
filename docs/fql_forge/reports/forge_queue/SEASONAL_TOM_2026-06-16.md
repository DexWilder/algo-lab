# Forge Report — Turn-of-Month seasonal (pivot batch 1) — 2026-06-16

> **Mode:** Lane B / REPORT-ONLY. Seasonal-vein pivot, non-equity focus, constrained gates. **Strict verdict: KILL/NONE** (no clean pass) — but a real beta-controlled near-miss on rates. No promotion/wiring/mutation.
> Artifacts: `research/forge_cycle_2026-06-16c_turn_of_month_seasonal.py` + `.json`.

## Results (long TOM window: penultimate td of M -> 3rd td of M+1)
| Asset | PF | vs generic | median | maxyr | worstYr | LOOmin | H1/H2 | MTM-DD | blocker |
|---|---|---|---|---|---|---|---|---|---|
| **ZN** | **1.451** | **1.84×** (gen 0.79) | **-$96.85** | 46.2% | -$1,266 | 1.214 | 1.64/1.28 | -$1,828 (<$2K ✅) | **negative median** (positive-skew) |
| ZF | 1.310 | 1.63× (gen 0.80) | -$18.73 | 37.8% | -$2,615 | 1.049 | 1.13/1.53 | -$1,523 | neg median + worstYr>$2K |
| MGC | 1.450 | 1.11× (gen 1.31) | +$23.76 | 38.2% | -$2,618 | 1.193 | 1.96/1.23 | **-$7,794** | prop-DD fail + weak beta-ctrl |
| MCL | 1.037 | ~1× | +$20.76 | 66.1% | — | 0.816 | — | -$1,427 | no edge |
| ZB | 1.128 | 1.55× | -$159.35 | 63.6% | -$2,725 | 0.951 | — | -$3,875 | conc + worstYr + LOO |
| MES (ref) | 0.919 | 0.73× (gen 1.26) | — | — | — | — | — | — | TOM < generic (not an equity effect) |
| MNQ (ref) | 0.917 | 0.70× (gen 1.31) | — | — | — | — | — | — | TOM < generic |

## Findings
- **ZN turn-of-month is a real, beta-controlled, prop-survivable rates seasonal** (PF 1.45 vs losing generic 0.79; LOO/H1H2 robust; MTM-DD < $2K). Blocked only by **negative median** (low-hit-rate, tail-win profile). → **WATCH-LOW**: real non-equity seasonal, needs distribution-appropriate handling (e.g., the median gate may be the wrong gate for a positive-skew tail strategy) before it could be a candidate. First non-equity structure the search has found.
- **Control result:** TOM is NOT an equity effect here (MES/MNQ underperform generic) but IS a rates effect — confirms the seasonal vein carries real, asset-class-specific structure (and is not just disguised beta — ZN beats a *losing* baseline).
- Strict gates cleared by: none. So no deployable candidate this batch.

## Boundaries
Report-only; no promotion/wiring/mutation; canonical feeds + active books untouched. Phase 1C frozen.
