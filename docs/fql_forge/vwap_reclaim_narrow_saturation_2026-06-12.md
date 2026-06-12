# VWAP Reclaim Workhorse Mechanism — Narrow Saturation Annotation (2026-06-12)

> **Authority:** Operator decision #191 A (2026-06-12).
> **Doctrine:** [[feedback_asset_family_saturation_rule]] — narrow saturation, REOPENABLE_WITH_NEW_THESIS.
> **Status:** Lane B research annotation. No registry mutation.

## What is saturated

**Saturated:** VWAP reclaim / VWAP-cross workhorse mechanism with `ema_slope` filter and `profit_ladder` exit on MNQ and MES.

Evidence (cycle 12e):

| Candidate | n | PF | Median | Verdict |
|---|---:|---:|---:|---|
| WH-MNQ-vwap_reclaim | 1127 | 1.107 | +$1.76 | KILL (PF<1.15 floor) |
| WH-MES-vwap_reclaim | 1185 | 0.918 | -$4.99 | KILL (median neg) |

**Mechanism produces trades but no edge** after V1 cost model. Trade frequency was strong (63-66% days traded) but PF fails the cheap-screen floor.

## What is NOT saturated

The VWAP reclaim thesis itself remains open if combined with a NEW thesis. Specifically:

1. **Regime-specific VWAP reclaim** — high-volatility regime only, or trend-day only
2. **Event-day VWAP reclaim** — VWAP reclaim only on macro event days
3. **Failed-VWAP trap** — VWAP cross that fails to hold, then reverses (mean-reversion of the reclaim)
4. **VWAP reclaim + order-flow context** — only when volume confirms
5. **VWAP reclaim + multi-timeframe alignment** — only when daily / weekly VWAP aligns

These are NEW theses, not parameter rescues. Per operator #191 "no rescue/filter/exit work unless a materially new thesis is proposed."

## What is FORBIDDEN

- Filter/exit "rescue" loops on the existing mechanism (per operator #191)
- Threshold parameter sweep without new thesis
- Re-test on additional assets unless thesis change justifies

## REOPEN CRITERIA

- A written new thesis with mechanistic edge hypothesis (not parameter tuning)
- Demonstrated event/regime-conditioned edge in synthetic data BEFORE production test
- Cross-mechanism combination that addresses why simple reclaim fails

## What the failure showed

The simple VWAP-cross signal trades often but doesn't survive transaction costs. This is consistent with VWAP being a widely-watched institutional reference — naive crosses get crowded and adversely selected. A successful VWAP strategy likely requires conditional context (regime, order flow, event proximity) rather than the cross itself.

## Cross-reference

- [[feedback_asset_family_saturation_rule]] — narrow saturation doctrine
- [[feedback_concentration_is_load_bearing]] — gate primacy
- `docs/fql_forge/cpi_event_window_narrow_saturation_2026-06-11.md` (precedent)
- `docs/fql_forge/fomc_mgc_narrow_saturation_2026-06-11.md` (precedent)

## Status

VWAP reclaim / VWAP-cross workhorse mechanism: **NARROW SATURATION** (MNQ, MES, ema_slope + profit_ladder).

Next VWAP work blocked pending one of the REOPEN CRITERIA above.

The 2 candidate strategies are archived:
- `WH-MNQ-vwap_reclaim-ema_slope-PL` → ARCHIVED — REOPENABLE_WITH_NEW_THESIS
- `WH-MES-vwap_reclaim-ema_slope-PL` → ARCHIVED — REOPENABLE_WITH_NEW_THESIS
