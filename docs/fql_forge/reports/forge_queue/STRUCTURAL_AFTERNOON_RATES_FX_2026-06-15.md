# Forge Report — STRUCTURAL/afternoon reversion (rates+FX) — 2026-06-15

> **Mode:** Lane B / REPORT-ONLY. No tuning, promotion, or wiring.
> **Result:** 0 PASS / 0 WATCH — all KILL. **Sanity-checked: the no-edge finding is REAL (not a `midline_target` artifact).** But the afternoon-reversion *thesis* is not dead — these generic primitives just don't capture it with default params.
> **Artifacts:** `research/forge_cycle_2026-06-15c_*` + `.json` (screen); inline diagnostic (control + exit-swap).

## Screen (3 reversion entries × session_afternoon × midline_target × 8 non-equity assets)
0 of 24 PASS. Most PF < 1.0 with negative medians. The extreme rates PFs (ZB ~0.09–0.23, ZN ~0.18) looked suspicious, so before concluding I ran a sanity check.

## ⚠️ Sanity check (why I didn't just report "KILL")
Uniform PF≪1 + degenerate 0.0% concentration smelled like an artifact. Diagnostic:

| Test | PF | Read |
|---|---|---|
| bb_reversion **MNQ** afternoon midline (equity control) | 0.789 | KILL on home turf → not a wrong-asset issue |
| afternoon_reversion **MNQ** afternoon midline | 0.851 | KILL on home turf |
| bb_reversion **6E** afternoon midline_target | 0.971 | — |
| bb_reversion **6E** afternoon **profit_ladder** | 1.032 | exit swap → marginal, still no edge |
| bb_reversion **6E** afternoon **fixed_ratio** | 1.018 | exit swap → marginal, still no edge |
| bb_reversion **ZB** afternoon profit_ladder | 0.228 | still catastrophic → ZB scale-specific |

**Conclusions:**
1. The exit is **not** the artifact (exit swap moves 6E only 0.97→1.03).
2. Even the MNQ equity control fails (PF 0.76–0.85), so it's not asset-class mismatch.
3. The extreme rates PFs are scale/exit-inflated — **do not cite ZB 0.087 etc. as precise**; the robust signal is "no edge," confirmed by the control + exit swap.

## Honest finding
These three **generic** reversion primitives (`afternoon_reversion`, `bb_reversion`, `prior_day_fade`) with **default params** have **no edge in the afternoon** — on rates/FX and on equities. KILL is real.

**Important nuance (thesis ≠ primitive):** the live `ZN-Afternoon-Reversion` probation book *does* have afternoon-reversion edge — but via a different, calibrated mechanism, not these off-the-shelf primitives. So the afternoon-structural *thesis* is not refuted; rather, the generic crossbreeding reversion primitives don't replicate it out-of-box. A parameter-calibration follow-up is possible but **deprioritized** (don't rabbit-hole).

## Decision
Clean (sanity-checked) failure → per the stated plan, **pivot to VOL on non-equity next.** VALUE stays parked (`blocked_by_data`); EVENT/CARRY remain infrastructure-build tracks, not cheap screens.

Activation remains frozen pending PHASE1C_24H_VERIFY. Nothing promoted or wired.
