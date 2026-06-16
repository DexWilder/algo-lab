# Forge — Seasonal batch 2 (non-equity): RATES calendar structure found — 2026-06-16

> **Mode:** Lane B / REPORT-ONLY, distribution-aware, non-equity. No promotion/wiring/mutation.
> **Headline:** Rates (ZN/ZF/ZB) carry real, beta-controlled FOMC-week + turn-of-month seasonal structure. **ZN/FOMC-week is the lead non-equity diversifier candidate — WATCH, blocked only by prop-DD.** ZN-TOM reclassified STRUCTURE_FOUND (gate correction validated).
> Artifacts: `research/forge_cycle_2026-06-16d_*` + `.json`.

## Non-equity hits (vs generic baseline; generic rates-long LOSES so these are real alpha)
| Mechanism | PF | gen | expectancy | median | conc | left-tail | max-adverse-window | verdict |
|---|---|---|---|---|---|---|---|---|
| **ZN FOMC-week** | **1.86** | 0.79 | +$232 | **+$44** | **29.7%** | -$1,878 | **-$2,718 (>$2K)** | **WATCH (only prop-DD)** |
| ZN TOM | 1.45 | 0.79 | +$117 | -$97 | 46.2% | -$1,503 | -$1,828 (<$2K) | STRUCTURE_FOUND (pos-skew) |
| ZF FOMC-week | 1.51 | 0.80 | +$96 | +$28 | 44.5% | -$1,347 | -$2,055 (>$2K) | WATCH (prop-DD) |
| ZF TOM | 1.31 | 0.80 | +$55 | -$19 | 37.8% | -$1,097 | -$1,523 | STRUCTURE_FOUND |
| ZB FOMC-week | 1.48 | 0.73 | +$312 | -$3 | 27.9% | -$4,347 | -$4,500 | WATCH (prop-DD, large) |

MGC/MCL: no calendar structure (TOM/FOMC/holiday all KILL/no-beta-control). Rates day-of-week: all KILL. Equity control: TOM/FOMC underperform generic; DOW-Mon MES/MNQ PF ~1.7 (equity Monday effect, beta-laden — control curiosity only).

## Significance
First **non-equity, calendar, beta-controlled, positive-median, well-concentrated** seasonal (ZN/FOMC-week) — hits the exact missing category (rates / non-MNQ / calendar). Its single blocker (max-adverse-window slightly over $2K on the ~4-day hold) is a **deployment-shape** question (stop/window/sizing), not an edge question.

## Next action (deployment-shaping, NOT tuning a KILL)
Shape ZN/FOMC-week to prop-deployability: add a hard intra-window stop to cap max-adverse-window < $2K and/or test a tighter window; verdict PASS only if it then holds PF≥1.3 + positive expectancy + beta-control + concentration + prop-DD<$2K. If it clears → first deployable non-equity diversifier candidate. Also worth: ZN-TOM under proper tail-strategy gates.

## Boundaries
Report-only; no promotion/wiring/mutation; canonical feeds + active books untouched. Phase 1C frozen.
