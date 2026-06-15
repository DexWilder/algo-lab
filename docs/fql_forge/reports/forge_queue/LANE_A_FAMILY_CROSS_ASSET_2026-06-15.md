# Forge Report — Lane A family cross-asset portability (CONCLUSIVE) — 2026-06-15

> **Mode:** Lane B / REPORT-ONLY. No tuning, promotion, or wiring.
> **Conclusion:** `LANE_A_MOMENTUM_FAMILY_MNQ_SPECIFIC`. All 3 Lane A daily-workhorse mechanisms are MNQ-specific. **Stop porting the family; the asset-diversification gap requires NEW mechanisms.**
> **Artifacts:** `research/forge_cycle_2026-06-15{,b}_*` + `.json`.

## Results (exact validated config, MES/MGC/M2K/MYM/MCL vs MNQ baseline)

**range_compression_break** — non-MNQ PASS: NONE
| Asset | Verdict | PF | median | max-yr |
|---|---|---:|---:|---:|
| MNQ (base) | PASS | 1.359 | $8.76 | 32.8% |
| MES | DEFER | 1.205 | $1.26 | 46.3% |
| MGC | DEFER | 1.252 | $0.76 | 50.8% |
| M2K | KILL | 1.096 | -$0.74 | 85.6% |
| MYM | DEFER | 1.454 | $0.51 | 68.5% |
| MCL | KILL | 0.96 | -$3.24 | — |

**first_impulse_pullback** — non-MNQ PASS: NONE
| Asset | Verdict | PF | median | max-yr |
|---|---|---:|---:|---:|
| MNQ (base) | DEFER | 1.337 | $4.26 | 21.5% |
| MES | DEFER | 1.242 | -$2.49 | 34.8% |
| MGC | KILL | 1.075 | -$3.74 | 117% |
| M2K | KILL | 1.057 | -$1.24 | 133% |
| MYM | KILL | 1.051 | -$0.74 | 181% |
| MCL | KILL | 0.931 | -$3.24 | — |

(Combined with the 2026-06-15 stop_run screen: all three mechanisms MNQ-specific.)

## Finding
- Off MNQ, every Lane A mechanism collapses: medians ≈$0 or negative, year-concentration 46–181% (degenerate — single year carries it amid losses elsewhere). No non-MNQ PASS anywhere.
- The portable bundle remains `ema_slope + profit_ladder`; the **entry primitives** carry MNQ-microstructure-specific edges that do not generalize. This is the opposite of `orb_breakout`, which validated cross-asset.
- **Decision:** halt Lane A family cross-asset porting (don't rabbit-hole). Asset diversification needs genuinely new, non-momentum mechanisms.

## Pivot — next Forge priority (non-momentum factor gaps)
Per `inbox/_priorities.md` (momentum saturated; gaps VALUE/CARRY/VOL/EVENT/STRUCTURAL), Forge now biases toward portfolio-useful, non-MNQ, non-momentum diversification. Next step: diagnose which factor gaps are runnable now with existing primitives + data (vs blocked), then build/screen the highest-unlock target. No promotion/wiring; report-only.

Activation remains frozen pending PHASE1C_24H_VERIFY.
