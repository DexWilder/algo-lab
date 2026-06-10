# Metals-Specific Event Spec Shortlist — 2026-06-10

> **Status:** Shortlist per operator decision #128 (metals-specific events permitted; single-asset; clean calendar required).
> **Authority:** Lane B research-only.
> **Purpose:** Catalog macro-event extensions of Packet #1 template (EVT-NFP-MGC-Long-2h) to MGC-on-other-events. Build proceeds only after operator approval of selected candidate.

## Operator constraints (per #128)

- **Single-asset / metals-specific only.** No broad equity-index sweep.
- No crude event-window repeat without surprise/curve data.
- Must use clean calendar.
- Must pass median, temporal, concentration, and cost-stress gates.
- If becomes broad macro-event mining, stop and surface as operator decision.

## Background

Packet #1 (EVT-NFP-MGC-Long-2h) is built on the thesis that USD-related macro events drive directional flows into gold via the dollar reaction. The proven template:
- Event timestamp: 8:30 ET (BLS releases)
- Entry: +1 bar (8:35 ET) after event
- Exit: +24 bars (~2h hold)
- Direction: Long
- Filter: None
- Result: PF 2.32, 8/8 yrs positive, median ~$25/trade

This template is extensible to other USD-related macro events on MGC.

## Candidate shortlist (3 events)

### Candidate 1: CPI-MGC (PRIMARY RECOMMENDATION)

| Field | Value |
|---|---|
| **Event** | US BLS Consumer Price Index release |
| **Schedule** | Monthly, typically 2nd-3rd Tuesday/Wednesday of month, 8:30 ET |
| **Sample size** | ~12 events/year × 8 years = ~96 events |
| **Theoretical basis** | CPI surprises directly drive Fed rate expectations → real yields → gold pricing. One of the highest-impact macro events for USD/gold |
| **Data status** | **Need to build calendar** — BLS releases follow a published schedule. Minimum viable: rule-based ("3rd Tuesday or 3rd Wednesday of month at 8:30 ET") + manual audit of known shifts |
| **Calendar build complexity** | Moderate (~2-3h: pull historical release dates from BLS website or use rule + audit) |
| **Filter pre-flight** | Event-window thesis → no filter (direction-blind). Per #120: compatible |
| **Proposed first batch (if approved)** | CPI-MGC-Long-2h (matching Packet #1 template); CPI-MGC-Short-2h (control); CPI-MGC-Long-1h, 4h, EOD (window variants) |
| **Expected unlock** | Per Packet #1 pattern: if mechanism transfers, expect PF 1.5-2.5 with positive median + multi-year persistence |

### Candidate 2: FOMC-MGC

| Field | Value |
|---|---|
| **Event** | Federal Open Market Committee policy announcement |
| **Schedule** | 8 scheduled meetings per year, 14:00 ET (sometimes followed by press conference at 14:30) |
| **Sample size** | ~8 events/year × 8 years = ~64 events |
| **Theoretical basis** | FOMC announcements are the highest-impact rates-policy event. Direct rate surprise → gold reaction. But also wildcard: dot-plot revisions, forward guidance, balance-sheet language |
| **Data status** | **Need to build calendar** — Fed publishes meeting schedule; historical dates available via FRED or fred-style sources. Rule-based isn't straightforward (committee meets every ~6 weeks but specific dates vary) |
| **Calendar build complexity** | Moderate (~3-4h: harder than CPI because no simple rule; need to maintain authoritative list of historical meeting dates) |
| **Filter pre-flight** | Event-window thesis → no filter. **WARNING:** afternoon ET event (14:00) means the +24 bar holding window crosses session close (15:45). Needs different exit logic. |
| **Proposed first batch (if approved)** | FOMC-MGC-Long-1h (~12 bars hold within RTH), FOMC-MGC-EOD (exit at session close), FOMC-MGC-Overnight (hold to next-day open) |
| **Expected unlock** | Higher per-trade volatility (FOMC moves are typically larger than CPI) but smaller sample. Could produce high-median candidate but concentration risk |

### Candidate 3: PPI-MGC

| Field | Value |
|---|---|
| **Event** | US BLS Producer Price Index release |
| **Schedule** | Monthly, typically day before or same day as CPI, 8:30 ET |
| **Sample size** | ~12 events/year × 8 years = ~96 events |
| **Theoretical basis** | PPI is a leading indicator of CPI; markets sometimes price in CPI direction from PPI release. Lower direct gold impact than CPI itself |
| **Data status** | Same as CPI — BLS calendar |
| **Calendar build complexity** | Same as CPI (~2-3h) |
| **Filter pre-flight** | Same as Candidate 1 (event-window, no filter) |
| **Proposed first batch (if approved)** | PPI-MGC-Long-2h (matching template) |
| **Expected unlock** | Less than CPI — PPI signal-to-noise lower. But could find independent edge if PPI surprises that don't propagate to CPI exist |

## Recommendation: Build Candidate 1 first (CPI-MGC)

**Reasons:**
1. **Highest theoretical relevance** — CPI is the single most-impactful USD-driving macro release; closest match to NFP-MGC thesis
2. **Cleanest calendar** — BLS publishes schedule; rule-based + audit is viable
3. **Largest sample** (~96 events) for statistical resolution
4. **Lowest build complexity** (~2-3h)
5. **Filter pre-flight compatible** — event-window thesis, filter=none default
6. **Different event from NFP** — family-review should show low correlation (different release day; different specific data)

## Constraints / hard rules per #128

- Single-asset (MGC only). No broad equity-index sweep.
- Clean calendar required — if BLS schedule has too many shift exceptions, mark DATA_REQUIRED.
- Standard gates apply: median ≥ $2, PASS_STRESS, max-yr ≤ 50%, Era3 ≥ 0.
- Family review vs Packet #1 mandatory before any promotion — CPI and NFP both happen on different days but USD-driving events may produce overlapping signals.

## Stop condition (per #128 operator clause)

If this becomes broad macro-event mining (testing 5+ event types with similar thesis), STOP and surface as operator decision. Three candidates is the cap; do not expand without explicit approval.

## Source artifacts

- `docs/fql_forge/paper_packet_drafts/EVT-NFP-MGC-Long-2h_2026-06-04.md` (template)
- `research/forge_nfp_calendar_verify.py` (NFP calendar reference)
- `research/forge_eia_crude_calendar.py` (EIA calendar reference)
- `research/event_window_engine.py` (existing event-window harness)
- BLS CPI release schedule (operator-verifiable): https://www.bls.gov/schedule/news_release/cpi.htm
- BLS PPI release schedule: https://www.bls.gov/schedule/news_release/ppi.htm
- Federal Reserve FOMC schedule: https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm

## Constraints

- No registry mutation, no scheduler change, no portfolio allocation change, no paper/live promotion.
- No cost-assumption changes without verified data.
- Build proceeds only on operator approval of recommended candidate (CPI-MGC).
- Family review vs Packet #1 mandatory before any promotion classification.
