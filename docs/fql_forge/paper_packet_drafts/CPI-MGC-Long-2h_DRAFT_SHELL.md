# Paper-Readiness Packet #2 — CPI-MGC-Long-2h — DRAFT SHELL

> ## Status block
>
> | Field | Value |
> |---|---|
> | **Status** | **DRAFT SHELL** — PAPER_PACKET_CANDIDATE pending official BLS calendar verification + 8-dim audit |
> | **Operator decision** | Variant switch from Long-1h → Long-2h **ACCEPTED** per #139 |
> | **Calendar status** | **DATA_REQUIRED** per #140-C: machine-fetch of bls.gov returned HTTP 403; web archive blocked. Awaiting operator-supplied official BLS calendar (export / PDF / screenshot). Forge-recall calendar is NOT production-grade per #140. |
> | **Audit status** | Non-calendar dimensions running per #141; calendar dim cannot go GREEN until #140 resolved |
> | **Paper status** | NOT paper-approved |
> | **Live status** | NOT live-approved |
> | **Registry mutation** | NONE proposed |
> | **Scheduler change** | NONE proposed |
> | **Portfolio allocation change** | NONE proposed |
> | **Sprint position** | Day 13 of 30 |
> | **Authority** | T1 / Lane B / report-only |
> | **Source artifacts** | `research/forge_cycle_2026-06-10d.py` (rule-based v1), `research/forge_cycle_2026-06-10f_cpi_mgc_verified_calendar.py` (Forge-recall verified re-run) |

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
