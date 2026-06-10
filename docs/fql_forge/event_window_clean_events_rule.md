# Event-Window Clean-Events Rule — Data Integrity Doctrine

> **Status:** CODIFIED FQL doctrine. Locked 2026-06-10 per operator decision #146.
> **Authority:** Mandatory pre-audit check for any event-window candidate. Lane B research enforcement.
> **Trigger to codify:** CPI-MGC audit (cycle 10g) surfaced systemic MGC 5-min data gaps at event timestamps. Issue affects entire event_window family on MGC.

## Rule

**All event-window candidates on MGC (and any other asset with known data-gap history) MUST use a clean-events filter and report contamination in the audit.**

## Clean-events filter definition

An event is considered **CLEAN** if and only if:

1. The event timestamp has an exact bar match in the data, OR
2. The next available bar after the event timestamp occurs within `max_gap_minutes` of the event (default: 60 minutes for non-RTH events; operator-tunable per asset)
3. The event is AFTER the data file's start date (no pre-data-start events)

An event is **CONTAMINATED** if:
- Next available bar > `max_gap_minutes` after event (data outage)
- Event predates data start (engine falls back to first available bar — nonsense)
- Event timestamp falls in a multi-day data vendor outage

## Mandatory audit table

Every event-window audit must include this table:

| Metric | Value |
|---|---:|
| Total scheduled events (from verified calendar) | N |
| Events with EXACT bar match | E |
| Events with gap < `max_gap_minutes` | S |
| Events with gap `max_gap_minutes` to 1d (suspicious) | M |
| Events with gap > 1d (DATA OUTAGE) | O |
| Events excluded (pre-data-start) | P |
| **CLEAN events used** | **C = E + S** |
| Excluded contamination % | (M + O + P) / N × 100 |

And:

| Comparison | Contaminated metrics | Clean metrics | Δ |
|---|---|---|---|
| n | — | — | — |
| PF | — | — | — |
| Median | — | — | — |
| Max-yr share | — | — | — |
| Years positive | — | — | — |
| PASS_STRESS verdict | — | — | — |

## Gates require clean metrics

The strict packet-readiness gates (PF ≥ 1.30, median > 0, max-yr ≤ 50%, PASS_STRESS, yrs+ ≥ n_yrs/2, Era 3 ≥ 1.0) must be evaluated on **CLEAN-events metrics**, not contaminated metrics.

A candidate may NOT be accepted to packet status if any gate fails on clean events, even if contaminated metrics pass.

## Documented MGC data-gap status (known constraint)

| Asset | Data file | Status as of 2026-06-10 |
|---|---|---|
| **MGC** | `data/processed/MGC_5m.csv` | **Data starts 2019-06-30; multi-day gaps at 13/90 CPI events; 12/96 NFP events; identical mid-history gap pattern. Affects entire event_window family.** |

Other assets (MES, MNQ, MYM, MCL, ZN, 6E, 6J) — data-gap status not yet audited. Future event-window candidates on those assets must run this clean-events check before audit GREEN.

## Allowed amendments (e.g., Packet #1)

Existing accepted candidates may be amended with clean-events re-verification. If clean metrics STRENGTHEN the candidate (as Packet #1 NFP-MGC did), acceptance holds with amendment note. If clean metrics WEAKEN the candidate below gates, acceptance is REVOKED pending operator review.

## Counter-example revoke clause

If a future data-vendor or contract-series change eliminates the MGC data-gap issue, the contamination check still runs but yields N = E (all clean). Rule remains in place as standing pre-audit discipline.

## Audit dimension assignment

This check is now a SUB-DIMENSION of the existing 8-dim audit, attached to:
- **Dim 5 (Calendar)** for the calendar/event-coverage portion
- **Dim 8 (Artifact stability)** for the data-integrity portion

It is mandatory; not optional.

## Constraints

- No vendor replacement without operator approval (deferred to DATA_UNLOCK option)
- No contract series switch without operator approval
- Lane B research enforcement only; does not mutate registry/scheduler
- Future event-window primitives must include this check in their build PR

## Source artifacts

- `research/forge_cycle_2026-06-10g_cpi_mgc_audit_dims_1_3_4_8.py` (originating discovery)
- `research/data/fql_forge/reports/forge_cycle_2026-06-10g_audit_dims_1_3_4_8.json`
- `research/data/fql_forge/kill_taxonomy.json` key `_HEADLINE_2026-06-10g_audit_finds_data_integrity_issue_affecting_BOTH_candidates`
- Amendment in `docs/fql_forge/paper_packet_drafts/EVT-NFP-MGC-Long-2h_2026-06-04.md`
