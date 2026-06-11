# Packet Standard V1 — Inventory Re-score (Phase 2 Tier A)

> **Date:** 2026-06-11
> **Authority:** Operator directive (compressed Factory Stabilization).
> **Source:** `research/forge_cycle_2026-06-11l_phase2_tier_a_rescore.py`.
> **Reference standard:** [[packet_standard_v1]] (`docs/fql_forge/PACKET_STANDARD_V1_2026-06-11.md`).

## Tier definitions

- **Tier A — Full re-audit:** close-to-packet candidates re-run under canonical V1 doctrine.
- **Tier B — Verdict reaffirmation (no re-run):** clean PF/median KILLs that obviously remain KILL under V1 (no event-window filter change affects them).
- **Tier C — Reference only:** already-archived families with no near-packet status.

## Tier A — Full re-audit (7 candidates)

### 1. Packet #1 NFP-MGC-Long-2h (TAIL_ENGINE)

**Canonical filter:** strict + hold-continuity (24-bar hold > 60min).

| Gate | Value | Pass? |
|---|---|---|
| n ≥ 20 | 42 | ✅ |
| PF ≥ 1.30 | 1.250 | ❌ |
| Stress PF ≥ 1.30 | 1.142 | ❌ |
| Max instance ≤ 35% | 97.9% | ❌ |
| Positive instance frac ≥ 60% | 50% | ❌ |
| Instance CV ≤ 3.0 | 3.99 | ❌ |
| Era 3 PF ≥ 1.0 | 1.07 | ✅ |
| Calendar grade | OPERATOR_VERIFIED | ✅ |
| Era 3 median (SOFT) | -$6.24 | flag |

**V1 verdict: ARCHIVED — REOPENABLE_WITH_NEW_THESIS.**

Reason: 5/8 hard tail-engine gates fail under canonical filter. Prior accepted status was based on metrics that included $4314.96 of fictitious PnL from 21 multi-day data-gap events (per R4). Under V1, the candidate's TRUE edge (42 events, PF 1.25) does not meet tail-engine standards.

### 2. BBKC-MNQ-Both-PL (WORKHORSE)

**Canonical filter:** N/A (continuous intraday, no event filter).

| Gate | Value | Pass? |
|---|---|---|
| n ≥ 500 | 838 | ✅ |
| PF ≥ 1.20 | 1.211 | ✅ |
| Positive median | +$2.76 | ✅ |
| **PASS_STRESS at 2× cost + 2 ticks slip** | median **-$0.48** | ❌ |
| Max-yr ≤ 50% | 43.9% | ✅ |
| Years positive ≥ 50% | 6/8 | ✅ |
| Era 3 PF ≥ 1.0 | 1.32 | ✅ |
| Era 3 median ≥ 0 | +$7.01 | ✅ |

**V1 verdict: ARCHIVED — REOPENABLE_WITH_VERIFIED_COST_DATA.**

Honest update from prior CONDITIONAL PORTFOLIO_COMPLEMENT classification: BBKC fails the V1 stress gate (median -$0.48 at 2× cost + 2 ticks). Cost-fragile. Could pass under verified actual prop costs (operator-submitted #150 still pending), but cannot be classified as PORTFOLIO_COMPLEMENT under V1 strict reading unless stress passes.

Reopen criteria: verified prop costs that lower the conservative-bias stress assumption.

### 3. FOMC-MGC-Long-4h (TAIL_ENGINE)

**Canonical filter:** strict + hold-continuity (48-bar hold = 4h > 60min).

| Gate | Value | Pass? |
|---|---|---|
| n ≥ 20 (after canonical filter) | **0 clean events** | ❌ |

**V1 verdict: ARCHIVED (insufficient clean events under canonical filter).**

The 48-bar hold-continuity check eliminates all 42 FOMC events from cycle 11f. MGC has session pauses and data gaps within any 4-hour post-event window. Reopen would require new data or shorter hold.

### 4. NFP-MES-Long-1h (TAIL_ENGINE)

**Canonical filter:** strict-only (hold == 60min, R1 carve-out).

| Gate | Value | Pass? |
|---|---|---|
| n ≥ 20 | 84 | ✅ |
| PF ≥ 1.30 | 1.157 | ❌ |
| Stress PF ≥ 1.30 | 0.917 | ❌ |
| Max instance ≤ 35% | 119.0% | ❌ |
| Positive instance frac ≥ 60% | 75% | ✅ |
| Instance CV ≤ 3.0 | 5.87 | ❌ |
| Era 3 PF ≥ 1.0 | 1.03 | ✅ |
| Calendar grade | OPERATOR_VERIFIED | ✅ |
| Era 3 median (SOFT) | +$10.01 | flag (positive — informational) |

**V1 verdict: ARCHIVED — REOPENABLE_WITH_NEW_THESIS.**

4/8 hard gates fail. Concentration and stress are killers.

### 5. NFP-MNQ-Long-1h (TAIL_ENGINE)

**Canonical filter:** strict-only (hold == 60min).

| Gate | Value | Pass? |
|---|---|---|
| n ≥ 20 | 84 | ✅ |
| PF ≥ 1.30 | 1.173 | ❌ |
| Stress PF ≥ 1.30 | 1.107 | ❌ |
| Max instance ≤ 35% | 117.4% | ❌ |
| Positive instance frac ≥ 60% | 62.5% | ✅ |
| Instance CV ≤ 3.0 | 4.74 | ❌ |
| Era 3 PF ≥ 1.0 | 1.35 | ✅ |
| Calendar grade | OPERATOR_VERIFIED | ✅ |
| Era 3 median (SOFT) | +$20.26 | flag (positive — strongest Era 3 of any near-miss) |

**V1 verdict: ARCHIVED — REOPENABLE_WITH_NEW_THESIS.**

4/8 hard gates fail. Era 3 strength is interesting; concentration kills.

### 6. CPI-MNQ-Long-1h (TAIL_ENGINE)

**Canonical filter:** strict-only. **Calendar:** FORGE_COMPILED_DATA_REQUIRED.

Calendar grade alone blocks acceptance under V1 (requires ≥ MACHINE_FETCHED_OFFICIAL).

**V1 verdict: ARCHIVED — REOPENABLE_WITH_NEW_DATA (calendar grade insufficient + concentration fail).**

### 7. CPI-MNQ-Long-2h (TAIL_ENGINE)

**Canonical filter:** strict + hold-continuity. **Calendar:** FORGE_COMPILED_DATA_REQUIRED.

Same calendar block. Plus concentration fail (82.5%).

**V1 verdict: ARCHIVED — REOPENABLE_WITH_NEW_DATA.**

## Tier B — Verdict reaffirmation (no full re-run)

These candidates were cleanly KILL under prior gates; V1 rules do not change the verdict.

| Candidate | Prior verdict | V1 verdict | Reason |
|---|---|---|---|
| LHD-MES-Long-60m / Short-60m | KILL (median neg) | ARCHIVED | Same KILL on V1 workhorse gates |
| LHD-MNQ-Long-60m / Short-60m | KILL (median neg) | ARCHIVED | Same KILL on V1 workhorse gates |
| GAP-MES-Cont-60m / Fade-60m | KILL | ARCHIVED | Continuation: large neg median; Fade: PF<1.15 |
| GAP-MNQ-Cont-60m / Fade-60m | KILL | ARCHIVED | Same |
| All CPI/NFP/FOMC KILL variants from 11a/11c/11e | KILL | ARCHIVED | Same |
| ARF2-MNQ-cont-PL | OBSERVATIONAL (Era 3 fail) | ARCHIVED / REOPENABLE_WITH_NEW_THESIS | Era 3 PF still < 1.0 |

## Tier C — Reference only

Already archived families (CPI-MGC, etc.) — V1 doesn't re-open them. They remain in their saturation annotations:
- `docs/fql_forge/cpi_event_window_narrow_saturation_2026-06-11.md`
- `docs/fql_forge/fomc_mgc_narrow_saturation_2026-06-11.md`
- `project_orb_directional_asymmetry_matrix` (memory)

## V1 sprint state (Day 16 / 30)

| Status | Count |
|---|---:|
| ACCEPTED_PAPER_READINESS_PACKET | **0** |
| PAPER_PACKET_CANDIDATE | 0 |
| REVIEW | 0 |
| PORTFOLIO_COMPLEMENT | 0 (BBKC downgraded under V1 stress gate) |
| OBSERVATIONAL | 0 (consolidated to ARCHIVED REOPENABLE) |
| ARCHIVED / REOPENABLE | 7+ Tier A + ~14 Tier B = ~21 |

**Honest sprint state: 0 accepted, 0 candidates, 0 portfolio complements.**

This is the RED Recovery Mode resting state under V1.

## What V1 Phase 2 accomplished

- Eliminated rule-churn ambiguity for every Tier A candidate (frozen verdicts under stable rules)
- Confirmed that NO existing candidate survives canonical V1 doctrine
- Established that the path to a Packet #2 must come from the post-V1 search queue (new mechanisms, not rescue of existing fails)
- Locked durable archive labels with REOPENABLE conditions for each candidate

## Next step

Resume nonstop hunting under V1 with the post-V1 search queue:
`docs/fql_forge/post_v1_nonstop_search_queue_2026-06-11.md`.
