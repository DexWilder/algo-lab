# Event-Window Clean-Events Rule — Data Integrity Doctrine

> **Status:** CODIFIED FQL doctrine. Locked 2026-06-10 per operator decision #146.
> **Authority:** Mandatory pre-audit check for any event-window candidate. Lane B research enforcement.
> **Trigger to codify:** CPI-MGC audit (cycle 10g) surfaced systemic MGC 5-min data gaps at event timestamps. Issue affects entire event_window family on MGC.

## Rule

**All event-window candidates on MGC (and any other asset with known data-gap history) MUST use a clean-events filter and report contamination in the audit.**

## Clean-events filter definition

An event is considered **CLEAN** if and only if:

1. The next available bar AFTER the event timestamp (`df[df.dt > event].head(1)`) is within `max_gap_minutes` of the event (default: 60 minutes for non-RTH events; operator-tunable per asset)
2. The event is AFTER the data file's start date (no pre-data-start events)

An event is **CONTAMINATED** if:
- Next available bar > `max_gap_minutes` after event (data outage)
- Event predates data start (engine falls back to first available bar — nonsense)
- Event timestamp falls in a multi-day data vendor outage

### Doctrine update 2026-06-11: NEXT-BAR GAP MATTERS (per #161-C)

Locked 2026-06-11 after FOMC-MGC filter sensitivity finding (cycle 11e vs 11f):

> **For event-window hold strategies, exact-bar match at the event timestamp is necessary but NOT sufficient.** Event eligibility requires:
>
> 1. event timestamp alignment,
> 2. tradable entry bar (next bar after event within `max_gap_minutes`),
> 3. next-bar continuity (no session-boundary gap between event and entry),
> 4. sufficient continuous bars through the intended hold window or defined exit logic.

**Why:** Cycle 11e treated "exact bar match" as automatically clean, finding 45 events. Cycle 11f's strict next-bar-gap filter found 42 events. The 3-event difference drove PF from 1.158 to 1.403 (25% PF swing on 3 trades) — those 3 events had the entry bar but were immediately followed by session-boundary gaps that distorted exits.

**Implementation:** Filters MUST use `df[df_dt > event].head(1)` (strict greater-than), then compute the gap from event to that next bar. An "exact-match" check alone (`df[df_dt == event]`) is INSUFFICIENT and may overcount clean events.

**Contamination tables** must report BOTH:
- event-bar match status (yes/no), AND
- next-bar gap status (≤ max_gap_minutes / > max_gap_minutes)

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

8-asset data-gap audit performed 2026-06-10 (cycle 10k):
- **CLEAN_EVENT_READY (CPI):** MES (91.1%), MNQ (91.1%), ZN (90.0%)
- **CLEAN_EVENT_USABLE_WITH_WARN (NFP):** MES, MNQ, ZN (87.5% each), MGC (70.8%)
- **EVENT_DATA_GAPPED (CPI on MGC):** 67.8%
- **DATA_REQUIRED:** MYM, MCL, 6E, 6J (insufficient pre-data)

**Important caveat 2026-06-11:** The 06-10k audit used the permissive "exact-match" filter. Per the doctrine update above, the strict next-bar-gap filter is correct. Re-audit pending per #161-A (defensive hygiene). The clean-percent numbers in the 06-10k report should be treated as upper bounds; the strict filter will produce equal or fewer clean events per asset/event.

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
