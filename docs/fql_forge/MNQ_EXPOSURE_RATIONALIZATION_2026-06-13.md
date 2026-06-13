# MNQ Exposure Rationalization Packet — 2026-06-13

> **Authority:** Operator Option 1 (rationalize MNQ exposure first; do NOT raise the cap). Narrow governance cleanup BEFORE Phase 1C wiring.
> **Status:** COMPLETE. **VERDICT: MNQ_EXPOSURE_RATIONALIZED.**
> **Boundaries honored:** no stop_run_reversal wiring · no FOMC · no Wave 2/3 · no live/prop · no OpenClaw · no asset_config · no strategy-logic changes.
> **Artifacts:** `research/mnq_exposure_rationalization_2026-06-13.py` + `research/data/fql_forge/reports/mnq_exposure_rationalization_2026-06-13.json`. Pre-edit registry backup: `/tmp/strategy_registry_pre_mnq_cleanup_20260613.json`.

## 1. What the cap revealed

The constraint-11 MNQ cap surfaced **two undocumented MNQ daily books actively trading in paper** that were never promoted into paper probation:

| Book | How it got active | promotion_date | Documented as probation? |
|---|---|---|---|
| XB-ORB-EMA-Chandelier-MNQ | Wired 2026-05-28 as **Track 2 EXPERIMENTAL_FORWARD_CLOCK** (commit `640df6c`) | None | ❌ No (not in CLAUDE.md probation table) |
| XB-PB-EMA-Chandelier-MNQ | Wired 2026-05-28 as **Track 2** via Offensive Sprint v1 (`db67310`); notes say **`paper_ready=false, promotion_eligible=false`** | None | ❌ No |

Both were running as `status=probation` + `controller_action=REDUCED_ON` + `executable_state=EXECUTABLE` — i.e., trading — despite `lifecycle_stage=discovery` and no governed promotion. This is a Track-2-vs-probation status mismatch, exactly the governance drift the cap was meant to catch. They were deliberately wired (not random), but as a *lesser* status than probation, so per your rule ("deactivate unless documented approval *promoted them into paper probation*") they qualify for deactivation.

## 2. Before → After (active MNQ books in the forward runner)

| | BEFORE | AFTER |
|---|---|---|
| Active MNQ books (total) | **4** | **2** |
| — daily-workhorse class | 3: XB-ORB-EMA-Ladder-MNQ, XB-ORB-EMA-Chandelier-MNQ, XB-PB-EMA-Chandelier-MNQ | **1: XB-ORB-EMA-Ladder-MNQ** |
| — sparse-event class | 1: TV-NFP-High-Low-Levels | 1: TV-NFP-High-Low-Levels |
| Total active books (all assets) | 15 | 13 |
| Runtime `max_positions_per_asset` | 2 | 2 (unchanged) |

Computed live via `build_portfolio_config(include_probation=True)` — i.e., exactly what the runner trades.

## 3. Exact registry/controller changes (surgical — only these 2 entries)

For **both** XB-ORB-EMA-Chandelier-MNQ and XB-PB-EMA-Chandelier-MNQ:

| Field | Before | After |
|---|---|---|
| `status` | `probation` | `watch` |
| `controller_action` | `REDUCED_ON` | `OFF` |
| `controller_state` | `ACTIVE` | `VALIDATED` |
| `lifecycle_stage` | `discovery` | `watch` |
| `paper_execution` | — | `DEACTIVATED` |
| `deactivation_date` | — | `2026-06-13` |
| `deactivation_reason` | — | governance cleanup / undocumented MNQ exposure / never promoted into probation / records preserved |
| `state_history` | — | appended `DEACTIVATED_GOVERNANCE` entry |
| `notes` | (kept) | appended deactivation note |

**Records preserved** — nothing deleted; both remain reactivatable. Verified that only these 2 strategy entries differ from the pre-edit backup; all 166 strategies present; top-level registry structure identical. Written via `atomic_write_json`.

### Why this deactivation is durable (defeats the documented silent revert)
The codebase warns `portfolio_regime_controller.py` rewrites `controller_action` daily and was "observed silently reverting OFF → PROBATION over a weekend." The controller only evaluates `get_eval_strategies()` = `status ∈ {core, probation, testing}`. Moving these to `status=watch` removes them from the controller's eval set entirely, so it will **not** rewrite their `controller_action` back. `build_portfolio_config` then excludes them (`OFF` not eligible; `watch` not a dead status but action gates it out). Both layers confirmed empirically post-edit.

## 4. What stayed and why

- **KEPT ACTIVE — XB-ORB-EMA-Ladder-MNQ:** the canonical, documented probation workhorse (promoted 2026-04-06, `portfolio_role=workhorse`, in CLAUDE.md + XB_ORB_PROBATION_FRAMEWORK.md). Untouched.
- **KEPT SEPARATE — TV-NFP-High-Low-Levels:** legacy sparse-event MNQ sleeve. Untouched. **It still carries MNQ exposure** but is not a daily workhorse and is counted separately, per your instruction.

## 5. Resulting MNQ budget headroom

Daily-workhorse MNQ books are now **1 of the ≤2 cap**. There is room to wire `stop_run_reversal` later (1 existing + 1 new = 2) **within** the cap — but that is **Phase 1C, which is NOT performed here**.

## 6. Confirmations (boundaries)

- ✅ `stop_run_reversal` still **NOT wired** (absent from registry; verified)
- ✅ FOMC untouched · Wave 2 / Wave 3 untouched
- ✅ No live/prop changes · no OpenClaw · no asset_config · no strategy-logic changes
- ✅ No scheduler config (`fql_research_scheduler.py` JOBS) or launchd changes
- ✅ DSCL remains the live/prop gate; DATA_AUDIT_GREEN = feed-internal reproducibility only

## 7. Next steps (per your sequence — NOT auto-proceeding)

> Port verified ✅ → **exposure governance cleanup ✅ (this packet)** → **DSCL Source Verification (next priority)** → Phase 1C wiring.

Phase 1C wiring of `stop_run_reversal` is **on hold**. Per your direction, the next priority is **DSCL / canonical data-source verification for MNQ** before any new paper evidence begins. I will not proceed to Phase 1C automatically; I'll return with a clean approval request once MNQ exposure (done) and DSCL Source Verification are both complete.

## 8. Cross-reference

- `research/mnq_exposure_rationalization_2026-06-13.py` + `.json`
- `docs/fql_forge/paper_packet_drafts/WAVE1_PHASE1A_PORT_VERIFICATION_2026-06-13.md`
- `docs/fql_forge/lane_a_paper_deployment_plan_2026-06-13.md`
- `docs/fql_forge/data_source_control_layer_policy_2026-06-13.md`
- Track 2 provenance: commits `640df6c`, `db67310`; `docs/reports/2026-05-28_offensive_sprint_v1.json`; `docs/paper_readiness_packets/XB-ORB-EMA-Chandelier-MNQ.md`
