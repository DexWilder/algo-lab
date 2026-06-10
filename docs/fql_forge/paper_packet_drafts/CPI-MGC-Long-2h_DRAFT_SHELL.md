# Paper-Readiness Packet #2 — CPI-MGC-Long-2h — DRAFT SHELL

> ## Status block (UPDATED 2026-06-10 per operator decisions #144-147)
>
> | Field | Value |
> |---|---|
> | **Status** | **ARCHIVED as PAPER_PACKET_CANDIDATE — REOPENABLE_WITH_CLEAN_VARIANT** |
> | **Disposition** | Per #144 hybrid A/C: archived because clean-events re-run fails strict concentration + stress gates. NO operator discretion exception applied. |
> | **Clean-events variant investigation (cycle 10h)** | NO variant passes strict gates: Long-2h clean (53.8% max-yr, FAIL_STRESS), Long-EOD clean (161% max-yr, Era3 median negative, FAIL_STRESS) |
> | **Recent-era OBSERVATIONAL note** | 2022+ subsample (n=39): PF 2.856, median $10.76, net $4137. OBSERVATIONAL ONLY per #144. NOT a packet candidate. |
> | **Calendar status** | DATA_REQUIRED per #140-C (BLS machine-fetch blocked; operator submission still pending) |
> | **Audit status** | Individual dims marked; OVERALL AUDIT = NOT GREEN; BLOCKED on calendar dim + strict-gate failure |
> | **Paper status** | NOT paper-approved |
> | **Live status** | NOT live-approved |
> | **Sprint position** | Day 13 of 30 |
> | **Authority** | T1 / Lane B / report-only |
>
> **Individual audit dimension verdicts (per #147):**
>
> | Dim | Verdict |
> |---:|---|
> | 1 — Cost source | GREEN |
> | 2 — Cost stress | EVIDENCE COLLECTED on contaminated data; FAIL_STRESS on clean data |
> | 3 — Edge quality | Documented; FAILS gates on clean data |
> | 4 — Lookahead | NO ACTUAL LOOKAHEAD — but surfaced data integrity issue (now codified into doctrine per #146) |
> | 5 — Calendar | BLOCKED — DATA_REQUIRED per #140 |
> | 6 — Survivorship | N/A (single instrument) |
> | 7 — Duplicate/family | GREEN — independent of NFP-MGC (corr -0.021 on clean) |
> | 8 — Artifact stability | GREEN — deterministic re-run, hash-matched |
> | **OVERALL** | **NOT GREEN** — BLOCKED on #5 AND failing concentration + stress gates on clean data |
>
> **REOPEN criteria** (any of these):
> 1. Official BLS calendar arrives AND a new bounded re-run on clean events passes ALL strict gates
> 2. MGC data gaps are resolved (operator-approved data unlock; deferred per #146-A)
> 3. New thesis-specific variant proposed that addresses concentration concern without curve-fitting
> 4. Explicit operator override

---

## 1. Strategy thesis

The U.S. BLS Consumer Price Index ("CPI") release is one of the largest scheduled macro information events for global rates and commodities. CPI surprises drive Federal Reserve rate expectations, which in turn drive real yields, which drive gold pricing.

The thesis: **post-CPI MGC drift is biased LONG** on a 2-hour holding window after release. This is direction-blind (does not depend on CPI being a beat or miss); the pattern is a structural drift phenomenon similar to NFP-MGC (Packet #1).

The CPI thesis is **complementary to NFP-MGC**, not duplicative:
- NFP releases on 1st Friday at 8:30 ET
- CPI releases on Tuesday/Wednesday/Thursday at 8:30 ET (mid-month)
- Family review shows **near-zero correlation** (-0.017) and **1.2% day overlap** (verified Forge-recall calendar)

## 2. Rule definition

| Field | Value |
|---|---|
| **Asset** | MGC (micro gold futures, CME) |
| **Bar timeframe** | 5-minute |
| **Event** | BLS Consumer Price Index release at 08:30 ET |
| **Calendar** | **DATA_REQUIRED** — awaiting operator-verified BLS calendar |
| **Entry** | Long MGC at the open of the **+1 bar** after the event timestamp (i.e., 08:35 ET) |
| **Exit** | Mechanical exit at the close of the **+24 bar** (~2 hours hold; 10:35 ET) |
| **Position sizing** | 1 contract (no vol-adjusted sizing in v1) |
| **Stop loss** | None in v1 (mechanical time exit only) |
| **Filter** | None — every documented CPI release is traded |

## 3. Evidence (Forge-recall verified calendar — preliminary)

| Metric | Value | Notes |
|---|---:|---|
| n | 84 | Across 2019-2026 partial |
| PF | **1.569** | ≥1.30 threshold ✓ |
| Median trade | **+$13.26** | Positive ✓ |
| Mean trade | TBD | Audit dimension |
| Max-year share | **33.5%** | <50% gate ✓ |
| Years positive | 6/8 (75%) | ≥50% gate ✓ |
| H1 / H2 PF | TBD | Audit dimension |
| Era 1 PF | 2.18 (computed mid-audit) | — |
| Era 2 PF | 1.40 | — |
| Era 3 PF | **1.47** | ≥1.0 regime-wall ✓ |
| Era 3 median | **+$15.76** | Positive ✓ |
| **PASS_STRESS** at conservative-bias costs | ✓ | ✓ |
| **Family review vs NFP-MGC** | corr -0.017, day-overlap 1.2% | Independent ✓ |

### Per-year breakdown (verified Forge-recall calendar)

| Year | n | PF | Median | Net |
|---|---:|---:|---:|---:|
| 2019 | 7 | 2.92 | $3.76 | $515 |
| 2020 | 12 | 2.03 | $24.76 | $724 |
| 2021 | 12 | 1.35 | $20.26 | $371 |
| 2022 | 12 | 0.82 | -$14.24 | -$267 |
| 2023 | 12 | 2.62 | $64.26 | $1,737 |
| 2024 | 12 | 1.88 | $2.26 | $1,240 |
| 2025 | 12 | 1.74 | $15.76 | $1,854 |
| 2026 partial (5 events) | 5 | 0.48 | $73.76 | -$645 |

## 4. 8-Dimension Evidence-Integrity Audit Status

| # | Dimension | Status | Notes |
|---:|---|---|---|
| 1 | Cost source | ⏳ IN PROGRESS | Verify `engine/asset_config.py["MGC"]` values used; same conservative bias as Packet #1 |
| 2 | Cost stress survival | ✅ EVIDENCE COLLECTED | PASS_STRESS at standard rungs on verified Forge-recall calendar |
| 3 | Edge quality | ⏳ IN PROGRESS | PF, median, win-rate, mean computed pending |
| 4 | Lookahead | ⏳ IN PROGRESS | Verify entry is at +1 bar (post-event), not at event timestamp itself |
| 5 | **Calendar** | ❌ **DATA_REQUIRED** | **Operator must submit official BLS calendar per #140-C** |
| 6 | Survivorship | ✅ NOT APPLICABLE | Single instrument; not portfolio-survivor |
| 7 | Duplicate / family | ✅ COMPLETE | Family review vs NFP-MGC: corr -0.017, day-overlap 1.2% — independent |
| 8 | Output artifact stability | ⏳ IN PROGRESS | Verify cycle reproducibility |

**Verdict: PENDING (cannot go GREEN until #5 resolved).**

## 5. Calendar verification path (DATA_REQUIRED)

**Attempted automated fetch (2026-06-10):**
- `https://www.bls.gov/schedule/news_release/cpi.htm` → HTTP 403 Forbidden
- `https://www.bls.gov/cpi/news.htm` → HTTP 403 Forbidden
- `https://download.bls.gov/pub/time.series/cu/cu.txt` → HTTP 403 Forbidden
- `https://web.archive.org/...` → blocked by harness

**Forge-recall calendar** (used in cycle 10f): operator-verifiable but not production-grade per #140.

**Operator-acceptable paths:**
1. Operator supplies official BLS calendar export (CSV/PDF/screenshot) → Forge records source + re-runs cycle 10f-equivalent
2. Operator confirms specific dates against bls.gov in writing → Forge records confirmation
3. Operator provides authenticated access (e.g., FRED API key, BLS API key) → Forge machine-fetches and records

**Until #140 resolved, this packet remains DRAFT SHELL.**

## 6. Comparison to Packet #1 (EVT-NFP-MGC-Long-2h)

| Metric | Packet #1 NFP-MGC | CPI-MGC-Long-2h (verified Forge-recall) |
|---|---:|---:|
| n | 84 | 84 |
| PF | 2.264 | 1.569 |
| Median | $21.76 | $13.26 |
| Years positive | 8/8 | 6/8 |
| Concentration | (audit GREEN) | 33.5% (cleaner) |
| Independence | n/a | corr -0.017 to NFP, 1.2% overlap |
| Stress | (audit GREEN) | PASS_STRESS (Forge-recall calendar) |

CPI-MGC-Long-2h is moderately weaker than NFP-MGC at headline metrics but:
- **Independent of NFP-MGC** (correlation near zero)
- **Cleaner concentration** (33.5% vs prior 41-46% on rule-based)
- **Higher per-trade median** than rule-based version surfaced
- **Different event class** — adds genuine diversification to the event-window family

## 7. Operator decision matrix (when calendar verified)

| Calendar verification result | Disposition |
|---|---|
| Verified BLS dates EXACTLY match Forge-recall calendar | Re-run cycle 10f confirms metrics → proceed to remaining 8-dim audit dimensions → if all GREEN, packet status updates to ACCEPTED candidate |
| Verified BLS dates DIFFER from Forge-recall by ≤5 dates | Re-run; if metrics still pass all gates, proceed; otherwise classify based on new metrics |
| Verified BLS dates DIFFER materially (>5 dates) | Re-run; if metrics weaken to FAIL_STRESS or concentration >50%, ARCHIVE candidate. Long-EOD review as secondary. |

## 8. Constraints

- No registry mutation. No scheduler change. No portfolio allocation change. No paper/live promotion.
- No cost-assumption changes without operator-verified data.
- Cannot proceed to GREEN audit / packet acceptance without #140 calendar verification.
- Long-1h ARCHIVED (calendar-artifact false positive).
- Long-4h ARCHIVED (concentration fail).
- Long-EOD: SECONDARY/REFERENCE ONLY (per operator #139); not a candidate.

## 9. Source artifacts

- `research/forge_cycle_2026-06-10d_cpi_mgc_first_batch.py` (rule-based v1 cheap-screen)
- `research/forge_cpi_calendar_verified.py` (Forge-recall verified calendar — DATA_REQUIRED-flagged)
- `research/forge_cycle_2026-06-10f_cpi_mgc_verified_calendar.py` (head-to-head comparison)
- `research/data/fql_forge/reports/forge_cycle_2026-06-10d.json`
- `research/data/fql_forge/reports/forge_cycle_2026-06-10e_deep_screen.json`
- `research/data/fql_forge/reports/forge_cycle_2026-06-10f_verified_calendar.json`
- `research/data/fql_forge/reports/cpi_release_calendar_verified_2019_2026.json` (Forge-recall artifact for operator audit)
- `research/data/fql_forge/kill_taxonomy.json` keys `_HEADLINE_2026-06-10d/e/f_*`
