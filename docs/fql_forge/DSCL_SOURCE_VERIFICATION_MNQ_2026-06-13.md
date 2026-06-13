# DSCL Source Verification Packet — MNQ (in-repo scope) — 2026-06-13

> **Authority:** Operator — start DSCL Source Verification for MNQ with in-repo components now; mark external-feed components BLOCKED (not skipped/faked).
> **Status:** **DSCL_IN_REPO_VERIFIED.** MNQ is confirmed Databento-backed and the current processed file is **acceptable as canonical for PAPER** (not capital). Live/prop remains BLOCKED until external DSCL §7.
> **Artifacts:** `research/dscl_source_verification_mnq_2026-06-13.py` + `research/data/fql_forge/reports/dscl_source_verification_mnq_2026-06-13.json`.
> **Boundaries:** report-only · no registry/runner/scheduler/portfolio mutation · no stop_run wiring · external components honestly BLOCKED.

## ⚠️ Scope reminder
DATA_AUDIT_GREEN + this in-repo DSCL prove **feed-internal reproducibility and lineage**. They do **not** prove external feed correctness vs CME. Clean enough to paper. Not clean enough for capital until DSCL §7 (components 7–9) pass.

## 1. Is MNQ data Databento-backed? — YES (traced from code)

| DSCL component (1–6) | MNQ value | Source |
|---|---|---|
| 1. Feed/vendor | **Databento**, dataset **`GLBX.MDP3`** | `data/databento_loader.py` |
| 2. Symbol mapping / continuous | raw symbol **`MNQ.c.0`** — front-month continuous, **CALENDAR roll**, **raw stitch (NOT back-adjusted)** | `databento_loader.SYMBOLS`, `stype_in="continuous"` |
| 3. Session template | strategy trades RTH 09:30–15:45 ET (flatten 15:30); file stores full Globex session to ~19:55 | `crossbreeding_engine.compute_features` |
| 4. Timezone | UTC → US/Eastern, tz-stripped (naive Eastern); DST via pandas `tz_convert` | loader |
| 5. Roll logic | calendar-roll continuous `.c.0`, raw stitched → **roll-day price gaps possible**, gap-preserve | loader |
| 6. Bar construction | trade-based **1m OHLCV → resampled 5m** (`label=left, closed=left`; O=first/H=max/L=min/C=last/V=sum); fixed-point /1e9 guard | `resample_5m`, `update_daily_data.resample_and_append` |
| — Cost model | commission **$0.62/side**, slippage **1 tick**, tick **0.25**, point **$2.0**, `cost_tier=VALIDATED` | canonical `engine/asset_config.py` |
| — Daily append | same Databento path via `scripts/update_daily_data.py`, `mode="a"` | — |

**Both the historical backbone and the daily appends are Databento.** The FMP fetcher (`data/fetch_fmp.py`) is an MES-only legacy path and is **not** in the MNQ pipeline.

## 2. Can the lineage be proven? — Mostly, with one provenance gap

- ✅ The pipeline is Databento end-to-end (code-traced).
- ✅ Append-only since DATA_AUDIT_GREEN is **proven** (see §4 — truncating the live file to the audit window reproduces the audit's exact 487,168 rows + exact signal hash).
- ⚠️ **Provenance gap:** the processed CSV is appended **in place** (`mode="a"`) and incremental raw 1m bars are **not retained** (bulk raw `data/databento/MNQ_1m.csv` is frozen at 2026-03-07). So post-March bars are reproducible only by **re-querying Databento**, not from a retained raw artifact. Recommend the DSCL build queue add a retained-raw / lineage-snapshot step.

## 3. In-repo data audits (current file: 487,444 bars, 2019-06-30 → 2026-06-11)

| Check | Result |
|---|---|
| Duplicate timestamps | **0** |
| Monotonic increasing | **True** |
| Exact 5-min bars | 484,958 |
| Sub-5-min bars | 0 |
| Session-boundary gaps (>60min) | 1,799 (normal overnight/weekend) |
| Gaps >1 day / >3 days | 369 / 11 (weekends, holidays, long weekends) |
| Session-boundary **price** gaps >50 pt | 96 |
| Rollover-candidate gaps >100 pt | 46 |
| Full-file OHLCV hash | `4b7cc2503fc0820a` |
| Current file hash | `5233e103fbccd7b6` |

The 46 large roll-candidate gaps are **expected** for `.c.0` raw-stitch (non-back-adjusted) continuous data — they are exactly why DSCL §5 mandates **rollover-adjacent days** as an external-verification sample category. In-repo, the data is internally clean (no dupes, monotonic); the *correctness* of roll-day values vs CME is an external-feed question (component 7/8, blocked).

## 4. Rebuild + compare the DATA_AUDIT_GREEN window

Reconstructed the exact audit window (≤ 2026-06-10 19:55, in memory; file untouched):

| Metric | Rebuilt | Committed baseline | Match |
|---|---|---|---|
| n_bars (window) | 487,168 | 487,168 | ✅ append-only |
| first / last ts | 2019-06-30 20:00 / 2026-06-10 19:55 | — | ✅ |
| signal hash | `d2d31c3f0e7e86bb` | `d2d31c3f0e7e86bb` | ✅ exact |
| trade count | 1414 | 1414 | ✅ |
| PF | 1.477 | 1.477 | ✅ |
| median trade | $15.51 | $15.51 | ✅ |
| net | $35,368.64 | $35,368.64 | ✅ |
| largest single-trade loss | -$1,457.24 | -$1,457 | ✅ |
| largest single-day loss | -$1,457.24 | (intraday-flat) | ✅ |

## 5. External DSCL components — honestly BLOCKED (not passed)

| Component | Status |
|---|---|
| 7. CME official settlement comparison | **BLOCKED_ON_EXTERNAL_FEED_ACCESS** (CME DataMine) |
| 8. Secondary-vendor spot-check | **BLOCKED_ON_EXTERNAL_FEED_ACCESS** (e.g. dxFeed) |
| 9. Paper-execution reconciliation | **BLOCKED_PENDING_PAPER_PERIOD** |

These are **not** claimed as passed. They gate live/prop, not paper.

## 6. Verdicts

- **MNQ Databento-backed:** ✅ confirmed.
- **Current processed data acceptable as canonical for PAPER:** ✅ yes (feed-internal reproducibility + lineage proven; append-only confirmed).
- **Acceptable for LIVE/PROP capital:** ❌ BLOCKED until DSCL §7 (components 7–9).
- **May stop_run_reversal proceed to Phase 1C?** Not yet — **only after** the Organizational Hygiene / Elite Classification Audit confirms no remaining activation-risk mismatches (next governance gate). DSCL in-repo is necessary but not sufficient.

## 7. Cross-reference
- `docs/fql_forge/data_source_control_layer_policy_2026-06-13.md` (the policy)
- `docs/fql_forge/MNQ_EXPOSURE_RATIONALIZATION_2026-06-13.md`
- `docs/fql_forge/paper_packet_drafts/WAVE1_PHASE1A_PORT_VERIFICATION_2026-06-13.md`
