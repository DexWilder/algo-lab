# FOMC Event-Family Boundary Map — 2026-06-16

> Report-only. Turns the one-off ZN-FOMC edge into a *mapped* event family with known boundaries, applying the same regime/robustness discipline (cycle 16j) to ZF-FOMC and FOMC-MNQ-1h. Evidence: `forge_cycle_2026-06-16k_fomc_family_boundaries.json`. Reuses the fidelity-green executor; NON-WIRED; no mutation.

## The map

| Member | TF | Baseline | Regime dependence | Gate? | Role |
|---|---|---|---|---|---|
| **ZN-FOMC-week** | daily | n54 PF 1.945 | **HARD: easing-only** (16j: directionally robust 18/18) | **YES** — block if ZN 42-td trend ≤ 0 | **PRIMARY rates sleeve** |
| **ZF-FOMC-week** | daily | n54 PF 1.453 | **Same easing/hiking split** (directionally robust 14/14; 42td cut UP n20 PF 9.25 / DOWN n33 PF 0.58 net −$4.1k) | YES — gate off the same rate-trend | **Confirmation depth — NOT independent, NOT double-size** (ZN/ZF correlated) |
| **FOMC-MNQ-1h** | intraday 5m | n54 PF 1.777 | **NONE** — no clean driver (equity-trend sep 0.067; rate-trend sep 0.533, not robust) | **NO** — has not earned one; do not impose | **Independent all-weather event engine** — regime-agnostic + hold-robust + **entry-robust** (16m); credible paper-path candidate |

## Findings that matter

1. **ZF confirms the regime effect is real (macro, not instrument artifact)** — ZF independently reproduces the easing-edge / hiking-loss split. This raises confidence in the ZN hard gate. But ZN and ZF are the same rates-complex trade (correlated; the ZF data audit already classified them "one correlated sleeve, ZN primary, ZF not double-size"). **ZF is not a second independent diversifier** — counting it as one would double-count correlated risk.

2. **FOMC-MNQ-1h is the genuinely independent member** — different instrument, different timeframe, and (critically) **no regime dependence**: it works across both easing and hiking regimes. That makes it a cleaner standalone event engine than the regime-conditional rates sleeve, and a real diversifier from it.

3. **The discipline cuts both ways — MNQ does NOT get a gate.** ZN/ZF *earned* a hard regime gate (block removes a money-loser). MNQ did not — its edge is regime-agnostic and hold-robust (PF ≥1.2 across 6–20 bar holds, peak ~8–10; 12 bars is not tuned). **Bolting a regime gate onto MNQ would be cargo-cult governance** — a gate with no evidence behind it is fake safety, the same failure mode (inverted) that the ZN boundary test guarded against. Gates are earned per-member, not inherited by family.

## FOMC-MNQ-1h entry-offset robustness (`forge_cycle_2026-06-16m`) → `ENTRY_ROBUST_DRIFT_WINDOW`
The remaining fragility question — is +1 bar real drift or a lucky convention? **It's real drift.** Entry-offset sweep (hold fixed 12 bars, 54 clean events):

| offset | PF | net | median | win% | largest loss | |
|---:|---:|---:|---:|---:|---:|---|
| +0 (release bar) | 1.38 | $1,752 | $54 | 64.8% | −$950 | weakest of band |
| **+1 (validated)** | **1.78** | $3,253 | $67 | 64.8% | −$1,150 | pre-registered |
| +2 | **2.05** | $3,789 | $98 | 66.7% | −$701 | empirical best |
| +3 | 1.78 | $3,122 | $79 | 64.8% | −$801 | |
| +4 | 1.77 | $3,265 | $57 | 63.0% | −$816 | |
| +5 | 1.47 | $2,247 | $29 | 63.0% | −$831 | decaying |
| +6 | 1.43 | $2,329 | $29 | 57.4% | −$825 | decaying |

**Answers:**
- **+0/+1/+2/+3 all work** — PF ≥1.38 across the *entire* +0…+6 range. Not a knife-edge.
- **+1 is NOT uniquely magic** — it's one point in a broad post-FOMC upward-drift window (~+1 to +4), peaking at +2.
- **The release bar (+0) is the weakest entry** — lowest PF/net; entering into the immediate chaotic reaction has worse expectancy. Avoiding it *strengthens* the edge (+2 is best, with the smallest largest-loss and highest win rate). The edge does NOT vanish when you avoid the release bar — it improves.
- **Later entry decays gracefully** — beyond ~+4 the drift exhausts (PF→1.4, lower median/win%, rising std) but stays positive. Opportunity (net) peaks at +2.

**Discipline — keep +1 pre-registered; do NOT re-tune to +2.** +2 looks best *on this data*, but switching the wired offset to chase it would be the same in-sample re-optimization the ZN regime-threshold test warned against. The value of this test is that +1 sits inside a robust window — that *validates* the pre-registered convention; it is not license to cherry-pick the max-PF offset. A future change to +2 would be a gated, out-of-sample-justified decision.

**Status upgrade:** FOMC-MNQ-1h moves from "WATCH / one-off +1 edge" to **credible independent event engine** (regime-agnostic + hold-robust + entry-robust). Still gated: activation reopen + Phase 1C clear + external DSCL + V1 packet.

## Consequence for the mission count
The FOMC family yields **two distinct deployable engines, not three:**
- a **regime-gated rates sleeve** (ZN primary, ZF confirmation depth), and
- an **all-weather equity event engine** (FOMC-MNQ-1h).
Both run on the one shared executor (`engine/event_executor.py`); ZN/ZF carry the regime gate, MNQ does not. All still gated behind activation reopen + Phase 1C clear + external DSCL + V1 packets.

## Boundaries
Report-only mapping. No promotion, no wiring, no mutation.
