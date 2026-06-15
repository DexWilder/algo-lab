# Forge Report — VOL mechanisms on non-equity — 2026-06-15

> **Mode:** Lane B / REPORT-ONLY. No tuning, promotion, or wiring.
> **Result:** 0 PASS — all KILL, **MNQ control confirms real no-edge** (not an artifact).
> **Meta:** 2nd consecutive non-momentum generic-primitive cheap-screen failure → **saturation rule triggered**; pause this method.
> **Artifacts:** `research/forge_cycle_2026-06-15d_*` + `.json`.

## Screen (3 vol entries × filter=none × profit_ladder × MNQ-control + 8 non-equity)
| Entry | best PF (asset) | read |
|---|---|---|
| vol_expansion | 0.935 (6E) | KILL everywhere; MNQ control 0.866 |
| bb_keltner_squeeze | 0.94 (MNQ) | KILL everywhere; equity control sub-1.0 |
| volatility_regime_compound | n=0–1 most assets | **under-fired — not actually tested** (default regime-transition thresholds too strict) |

0 of 27 PASS; 0 non-MNQ with PF≥1.2.

**Control confirms:** the MNQ equity controls are also sub-1.0 (0.866–0.94), so this is genuine no-edge for these generic vol primitives with default params — not an asset/exit artifact. (Rates PFs again scale-inflated; don't cite ZB 0.23 etc. as precise.)

## Pattern across the non-momentum pivot (2 cycles)
| Cycle | Method | Result |
|---|---|---|
| 15c structural/afternoon reversion | generic reversion primitives, default params | no edge (control-confirmed) |
| 15d VOL non-equity | generic vol primitives, default params | no edge (control-confirmed) |

**Two consecutive focused cycles, 0 packet-grade → `feedback_asset_family_saturation_rule` triggers: PAUSE the "generic crossbreeding primitives + default params, cheap-screen on non-MNQ" method.** It is exhausted for non-MNQ diversification. The crossbreeding primitive library is effectively tuned to the MNQ-momentum regime; off-MNQ it has no out-of-box edge.

## The gap is real and still open — but cheap screens won't close it
Non-MNQ / non-momentum diversification needs a **different method than cheap-screening defaults.** Options (all bigger than a cheap screen — operator steer needed):

- **A. Parameter-calibration sweeps** per non-equity asset (cf. the `impulse_threshold` lesson: mechanisms port, *thresholds* are asset-specific). Report-only, more compute. Also re-test `volatility_regime_compound` with loosened thresholds (it never fired).
- **B. EVENT infra build** — CPI / auction calendars → event-tail candidates (the FOMC-MNQ tail-engine *worked*; this is the proven non-momentum shape). Highest-precedent path.
- **C. CARRY infra** — rates term-structure (Treasury-Rolldown precedent).
- **D. New factor-specific primitives** designed for rates/FX microstructure (not equity-momentum hand-me-downs).

VALUE stays parked (`blocked_by_data`).

## Recommendation
Pause autonomous cheap-screening (saturation). My lean: **B (EVENT infra)** — it's the proven non-momentum shape (FOMC tail-engine) and most likely to yield a portfolio-useful, prop-survivable, non-momentum candidate. But this is a strategic fork; **awaiting your steer.**

Activation remains frozen pending PHASE1C_24H_VERIFY. Nothing promoted or wired.
