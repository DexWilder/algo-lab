# FOMC Event-Family Boundary Map — 2026-06-16

> Report-only. Turns the one-off ZN-FOMC edge into a *mapped* event family with known boundaries, applying the same regime/robustness discipline (cycle 16j) to ZF-FOMC and FOMC-MNQ-1h. Evidence: `forge_cycle_2026-06-16k_fomc_family_boundaries.json`. Reuses the fidelity-green executor; NON-WIRED; no mutation.

## The map

| Member | TF | Baseline | Regime dependence | Gate? | Role |
|---|---|---|---|---|---|
| **ZN-FOMC-week** | daily | n54 PF 1.945 | **HARD: easing-only** (16j: directionally robust 18/18) | **YES** — block if ZN 42-td trend ≤ 0 | **PRIMARY rates sleeve** |
| **ZF-FOMC-week** | daily | n54 PF 1.453 | **Same easing/hiking split** (directionally robust 14/14; 42td cut UP n20 PF 9.25 / DOWN n33 PF 0.58 net −$4.1k) | YES — gate off the same rate-trend | **Confirmation depth — NOT independent, NOT double-size** (ZN/ZF correlated) |
| **FOMC-MNQ-1h** | intraday 5m | n54 PF 1.777 | **NONE** — no clean driver (equity-trend sep 0.067; rate-trend sep 0.533, not robust) | **NO** — has not earned one; do not impose | **Independent all-weather event engine** |

## Findings that matter

1. **ZF confirms the regime effect is real (macro, not instrument artifact)** — ZF independently reproduces the easing-edge / hiking-loss split. This raises confidence in the ZN hard gate. But ZN and ZF are the same rates-complex trade (correlated; the ZF data audit already classified them "one correlated sleeve, ZN primary, ZF not double-size"). **ZF is not a second independent diversifier** — counting it as one would double-count correlated risk.

2. **FOMC-MNQ-1h is the genuinely independent member** — different instrument, different timeframe, and (critically) **no regime dependence**: it works across both easing and hiking regimes. That makes it a cleaner standalone event engine than the regime-conditional rates sleeve, and a real diversifier from it.

3. **The discipline cuts both ways — MNQ does NOT get a gate.** ZN/ZF *earned* a hard regime gate (block removes a money-loser). MNQ did not — its edge is regime-agnostic and hold-robust (PF ≥1.2 across 6–20 bar holds, peak ~8–10; 12 bars is not tuned). **Bolting a regime gate onto MNQ would be cargo-cult governance** — a gate with no evidence behind it is fake safety, the same failure mode (inverted) that the ZN boundary test guarded against. Gates are earned per-member, not inherited by family.

## Consequence for the mission count
The FOMC family yields **two distinct deployable engines, not three:**
- a **regime-gated rates sleeve** (ZN primary, ZF confirmation depth), and
- an **all-weather equity event engine** (FOMC-MNQ-1h).
Both run on the one shared executor (`engine/event_executor.py`); ZN/ZF carry the regime gate, MNQ does not. All still gated behind activation reopen + Phase 1C clear + external DSCL + V1 packets.

## Boundaries
Report-only mapping. No promotion, no wiring, no mutation.
