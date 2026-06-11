# CPI Event-Window — Narrow Saturation Annotation (2026-06-11)

> **Authority:** Operator decision #156 (2026-06-11).
> **Doctrine:** [[feedback_asset_family_saturation_rule]] — saturation is narrow, REOPENABLE_WITH_NEW_THESIS.
> **Status:** Lane B research annotation only. No registry mutation.

## What is saturated

**Saturated:** CPI event-window with **simple single-direction entries** and **simple time-based exits** across:

- MGC (CPI clean coverage 67.8% — EVENT_DATA_GAPPED; archived 2026-06-10 per concentration fail)
- MES (CPI clean 91.1% — KILL across long/short × 1h/2h/4h, all PF < 1.15)
- MNQ (CPI clean 91.1% — KILL or OBSERVATIONAL; near-misses fail Era 3 + concentration)
- ZN (CPI clean 90.0% — KILL across all 6 variants)

Evidence:
- Cycle 2026-06-10d (CPI-MGC first batch)
- Cycle 2026-06-10g (CPI-MGC clean-data audit)
- Cycle 2026-06-10h (CPI-MGC archive)
- Cycle 2026-06-11a (CPI-MES/MNQ/ZN first batch)
- Cycle 2026-06-11b (CPI-MNQ deep-screen)

## What is NOT saturated

The CPI event-window thesis itself remains open. Specifically:

1. **CPI with a genuine new directional thesis** — e.g., pre-event drift filter where direction is conditional on observable pre-event state
2. **CPI with volatility-regime thesis written BEFORE testing** — must be pre-declared with mechanistic justification, not a rescue of the MNQ near-miss
3. **CPI with surprise-data (consensus vs actual)** — surprise direction may produce a tradable directional response (data-dependent)
4. **CPI with different exit architecture** — profit_ladder, trailing stop, volatility-adjusted exit, etc.
5. **CPI on other assets** — only with data verification + thesis justification
6. **CPI with cross-event interaction** — e.g., CPI-near-FOMC composite filter

## REOPEN CRITERIA (any one)

- A new written thesis with a mechanistic edge hypothesis (not a parameter sweep)
- A new primitive in the crossbreeding catalog that addresses the failure mode (e.g., regime filter built for a different purpose)
- New data (e.g., CPI surprise data joined to existing calendar)
- New asset or session not previously tested
- Operator override with documented rationale

## What is FORBIDDEN

- Vol-regime CPI-MNQ retest **now** (operator #156): smells like curve-fit rescue without a written thesis
- Further single-direction CPI sweeps on the 4 saturated assets without new primitive/data/thesis
- Lowering concentration or Era 3 gates to "rescue" the MNQ near-miss

## What the failures showed

The MNQ near-miss is **instructive** but not a packet. Per cycle 11b deep-screen:

| Candidate | PF | max-yr | yrs+ | Era3 PF | Era3 med | Family corr (max) |
|---|---:|---:|---:|---:|---:|---:|
| CPI-MNQ-Long-1h | 1.198 | **104.7%** | 5/8 | **0.84** | **-$1.24** | 0.027 |
| CPI-MNQ-Long-2h | 1.151 | **82.5%** | 5/8 | **0.88** | +$32.26 | 0.027 |

Family review CLEAN (max corr 0.027 across Packet #1, MNQ probation, MES-ORB, BBKC) → these would have unlocked as PAPER_PACKET if the edge were durable.

**The edge is not durable.** It is driven by 2019, 2021, 2023 outliers; recent regime (2022, 2024, 2026) is losing. Era 3 PF below 1.0 violates regime-wall doctrine.

This is exactly the kind of pattern the concentration + Era 3 gates exist to catch — and they did.

## Cross-reference

- [[feedback_asset_family_saturation_rule]] — narrow saturation doctrine
- [[feedback_concentration_is_load_bearing]] — concentration is hard packet-readiness gate
- [[feedback_event_window_clean_events_rule]] — clean-events filter doctrine
- [[feedback_validation_gates]] — the 6 real concentration gates
- [[feedback_edge_doctrine]] — durable edge requires positive median, cross-asset, sample size, low concentration

## Status

CPI single-direction event-window: **NARROW SATURATION** (4 assets, 6 hold-window × direction variants each).

Next CPI work blocked pending one of the REOPEN CRITERIA above.

NFP-MES/MNQ/ZN cross-asset replication launched as next search basis per #155.
