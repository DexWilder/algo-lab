# Forge Report — stop_run_reversal cross-asset screen — 2026-06-15

> **Mode:** Lane B / REPORT-ONLY (Phase 1C activation frozen; Forge engine running). No promotion, no wiring.
> **Doctrine:** `feedback_cross_asset_first` — cross-asset test the Wave 1 winner before building new families.
> **Verdict:** stop_run_reversal is **MNQ-specific**. Non-MNQ portability = **none**. Asset-diversification gap remains OPEN.
> **Artifact:** `research/forge_cycle_2026-06-15_stop_run_cross_asset_screen.py` + `.json`.

## Setup
Exact validated MNQ config (`entry=stop_run_reversal, exit=profit_ladder, filter=ema_slope, params={}`) screened on the equity-index micros + gold + energy where XB-ORB generalized. Same `generate_crossbred_signals` + `run_backtest` + canonical asset_config costs as DATA_AUDIT_GREEN.

## Results

| Asset | Verdict | PF | median | n | WR | top3 | max-yr |
|---|---|---:|---:|---:|---:|---:|---:|
| **MNQ** (baseline) | PASS_TO_FORWARD_CLOCK | 1.479 | $15.76 | 1415 | 54.7% | 11.9% | 25.1% |
| MES | DEFER | 1.352 | $2.51 | 1398 | 51.5% | 19.8% | 40.4% |
| MGC | DEFER | 1.593 | $3.76 | 703 | 52.3% | 25.8% | 67.3% |
| M2K | DEFER | 1.201 | $1.26 | 1404 | 51.2% | 20.4% | 31.5% |
| MYM | DEFER (tail-engine) | 1.239 | $0.26 | 472 | 50.2% | 59.7% | 65.4% |
| MCL | KILL | 1.145 | -$2.24 | 995 | 48.6% | 36.4% | 37.8% |

Baseline MNQ reproduces the validated edge (PF 1.479 ≈ committed 1.477; n=1415 = append-only drift). MNQ-control integrity confirmed.

## Finding
- **The `stop_run_reversal` entry's edge does not generalize.** Off MNQ, medians collapse to ≈$0 (MES $2.51, MGC $3.76, M2K $1.26, MYM $0.26) or go negative (MCL -$2.24), and year-concentration blows past gates (MGC 67%, MYM 65%). Even where PF looks ok (MGC 1.593), it's a concentration artifact (max-yr 67%).
- **Contrast with orb_breakout**, which validated across MNQ/MES/MGC/M2K/MCL/MYM. The load-bearing portable bundle remains `ema_slope + profit_ladder`; the *entry primitive* is where portability lives or dies, and `stop_run_reversal`'s liquidity-sweep edge is MNQ-microstructure-specific.
- **Implication:** the Lane A asset-concentration gap (all 4 candidates MNQ) is **not** closed by porting the winner. Non-MNQ diversification needs a different mechanism, not this entry.

## Disposition (report-only)
- stop_run_reversal: **keep as MNQ-only** workhorse (already Phase 1C on MNQ). Do NOT pursue cross-asset ports.
- No new candidates produced (all non-MNQ DEFER/KILL). No promotion, no wiring.

## Next safe Forge actions (queued, report-only)
1. Cross-asset screen the *other* validated mechanisms (`range_compression_break`, `first_impulse_pullback`) for non-MNQ portability — research only, does NOT touch the held Wave 2/3 MNQ wiring.
2. Target the factor gaps from `inbox/_priorities.md` (VALUE high; CARRY/VOL/EVENT/STRUCTURAL medium) — momentum is saturated, so non-momentum, non-MNQ diversification is the portfolio-useful priority.

Nothing here is promoted or wired. Activation remains frozen pending PHASE1C_24H_VERIFY_OK/FAIL.
