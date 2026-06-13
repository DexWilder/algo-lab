# Wave 1 — Phase 1A Port-Verification Packet (WH-MNQ-stop_run_reversal)

> **Authority:** Operator decision — Option 1 (build + verify, **hold wiring**), Phase 1A only, FOMC held out.
> **Status:** Build + verification COMPLETE. **VERDICT: PORT_VERIFIED_GREEN.** No registry / runner / scheduler / portfolio / live-prop / OpenClaw / asset_config mutation occurred. Strategy is **NOT wired** into paper execution — that requires separate Phase 1C approval.
> **Artifacts:** module `strategies/xb_stop_run_reversal_ema_ladder/strategy.py`; harness `research/forge_cycle_2026-06-13_phase1a_port_verification.py`; report `research/data/fql_forge/reports/forge_cycle_2026-06-13_phase1a_port_verification.json`.

## ⚠️ DATA_AUDIT_GREEN scope (locked 2026-06-13)

> **DATA_AUDIT_GREEN proved reproducibility WITHIN the current feed. It does NOT prove independent feed correctness.**
> Clean enough to paper. Not yet clean enough for capital. Live/prop gated by DSCL §7.

## 1. What was built

A runner-loadable executable module for the PRIMARY daily workhorse. It is a **thin adapter** that calls the **exact research primitive** the validated baseline used:

```python
generate_crossbred_signals(df, entry_name="stop_run_reversal",
                           exit_name="profit_ladder", filter_name="ema_slope", params={})
```

`params={}` → all primitive defaults (sweep_buffer=0.0, stop_mult=1.5, target_mult=3.0, ladder_style="classic"). Because the production module reuses the identical signal/exit code path as the research run, **logic divergence is structurally impossible**; only the live-execution adapter could diverge, and that is what the harness tests empirically.

## 2. Verification method — three paths + an authoritative reconstruction

| Path | What it runs | Purpose |
|---|---|---|
| **A — canonical** | Exact DATA_AUDIT_GREEN recipe (`generate_crossbred_signals` + `run_backtest` with explicit `get_cost_params("MNQ")`) on **current** data | Research/audit replica |
| **B — production** | The **real runner invocation path**: `importlib` load of the new module → `mod.generate_signals(full_df)` → `run_backtest(..., symbol="MNQ")` with **no explicit costs** (exactly as `run_forward_paper.run_strategy_on_new_bars`) | Catches any cost/point-value/mode resolution divergence in the production path |
| **C — committed** | cycle-11r baseline JSON (n=1414, PF 1.477, median 15.51, net 35368.64) | The validated target |
| **D — audit window (AUTHORITATIVE)** | Port run on the **exact data window DATA_AUDIT_GREEN used** (truncate current feed to ≤ 2026-06-10 19:55, in memory) | Apples-to-apples fidelity vs the audited baseline |

## 3. Results — PORT_VERIFIED_GREEN

| Verification criterion (operator list) | Result |
|---|---|
| **Production path == research path** (A==B), metrics **and signal hash**, EXACT | ✅ identical — both `n=1415, PF 1.479, median $15.76, net $35,469.90, hash 0c0c135ab04f3005` on current data |
| **Signal hash match** to DATA_AUDIT_GREEN | ✅ EXACT — port on audit window reproduces `d2d31c3f0e7e86bb` (no "framework formatting" excuse needed; it is byte-identical) |
| **n = 1414** | ✅ on the audit data window |
| **PF = 1.477** | ✅ on the audit data window |
| **median = +$15.51** | ✅ on the audit data window |
| **largest single-trade loss = -$1,457** | ✅ -$1,457.24 (and largest single-DAY loss = -$1,457.24 — intraday-flat, one trade/day) |
| **same session template, timezone, roll, costs, slippage, bar construction** | ✅ identical primitive + canonical `engine/asset_config.py` costs: `cost_tier=VALIDATED`, commission $0.62/side, slippage 1 tick, tick 0.25, point_value $2.0 |
| append-only data integrity | ✅ truncated current feed to audit window = **exactly 487,168 bars** (audit's recorded count) → automation only *appended*; no historical bars rewritten |

**Bottom line:** the executable module reproduces DATA_AUDIT_GREEN **byte-for-byte** on the audited data window (cryptographic signal-hash match), and the production runner invocation introduces **zero** additional divergence. The port is faithful.

## 4. Secondary finding — data-drift provenance (for DSCL, not a blocker)

During verification the harness found the live MNQ feed has **changed since DATA_AUDIT_GREEN was recorded**:

| | DATA_AUDIT_GREEN (2026-06-12) | Current (2026-06-13) |
|---|---|---|
| MNQ file hash | `739875437ded8a76` | `5233e103fbccd7b6` |
| span end | 2026-06-10 19:55 | 2026-06-11 19:55 |
| n bars | 487,168 | 487,444 (+276) |
| stop_run n | 1414 | 1415 |

This is **append-only** drift (the 2026-06-11 session was added by the forward-day automation *after* the audit; historical bars are byte-intact, proven by the exact truncated-window hash match). It is **not** a port defect and does not block paper. But two implications worth noting:

- The DATA_AUDIT_GREEN file hash is **point-in-time**. The audited baseline (n=1414) is a snapshot; the same strategy on live data is n=1415 and will keep ticking up as sessions append. This is normal and expected for a live-growing feed.
- This is exactly the kind of feed-provenance reality the **DSCL** (`data_source_control_layer_policy_2026-06-13.md`) is meant to govern. DSCL component 1–6 deployment notes should record that the research feed is append-only and that baseline metrics are snapshot-dated.

## 5. Critical wiring note for Phase 1C (DO NOT skip)

The forward runner has a **trap**: in `run_forward_paper.run_strategy_on_new_bars`, when a strategy's `execution_config.exit_variant == "profit_ladder"`, the runner **ignores the strategy module** and hardcodes `donchian_entries(full_df)` from `research.exit_evolution`. That would silently replace stop_run_reversal entries with **donchian** entries.

➡️ **When wiring (Phase 1C), the registry `execution_config.exit_variant` MUST be `None`** (matching the incumbent `xb_orb_ema_ladder`, which also uses `exit_variant=None` and embeds profit_ladder inside its module). With `exit_variant=None` the runner correctly calls `mod.generate_signals` — the path verified above. This requirement is documented in the module docstring.

## 6. Proposed Phase 1C atomic registry transition (NOT executed — for your approval)

On approval, exactly these fields would be created/set together in one commit (no partial updates):

- New registry entry `strategy_id: WH-MNQ-stop_run_reversal-ema_slope-PL`
  - `strategy_name: "xb_stop_run_reversal_ema_ladder"` (must equal the module dir)
  - `asset: "MNQ"`, `direction: "both"` (→ runner `mode="both"`)
  - `status: "probation"`, `controller_action: "PROBATION"`, `executable_state: "EXECUTABLE"`
  - `execution_config: {... "exit_variant": null, "avoid_regimes": [], "preferred_regimes": [] ...}` (fail-closed decision-grade fields explicit)
  - `promoted_date`, `lifecycle_stage`, portfolio_role `workhorse`
- Add to `research/live_drift_monitor.py` BASELINE with workhorse classifier
- Confirm scorecards/digest recognize the new ID
- 1-contract paper sizing; MNQ aggregate exposure cap (≤2 books) enforced
- Post-wiring verification within 24h (appears in runner + monitor + scorecards)

## 7. Boundaries — what this phase did NOT do

- ❌ No registry / runner / scheduler / portfolio mutation
- ❌ No paper or live execution; strategy is NOT in the runner universe
- ❌ FOMC (#4) not built — held out as a separate event-executor task
- ❌ No Lane B research resumed; no live/prop change; no OpenClaw / asset_config change
- ❌ No automation-owned data files modified (audit-window reconstruction done in memory only)

## 8. Operator decision

The port is proven faithful. **Awaiting your explicit Phase 1C approval** to perform the atomic paper-wiring above (the first registry/runner mutation). Until then, registry and runner remain untouched.

## 9. Cross-reference

- `strategies/xb_stop_run_reversal_ema_ladder/strategy.py`
- `research/forge_cycle_2026-06-13_phase1a_port_verification.py` + `.json` report
- `docs/fql_forge/lane_a_paper_deployment_plan_2026-06-13.md`
- `docs/fql_forge/data_source_control_layer_policy_2026-06-13.md`
- `docs/fql_forge/paper_packet_drafts/LANE_A_BATCH_2026-06-12.md`
