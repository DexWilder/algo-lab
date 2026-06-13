# Data Source Control Layer (DSCL) Policy — 2026-06-13

> **Authority:** Operator decision 2026-06-13.
> **Status:** Locked policy. Lane A paper deployment is GO; live/prop is GATED until DSCL passes.

## §1 — Critical clarification

> **DATA_AUDIT_GREEN proved reproducibility WITHIN the current feed.**
> **It does NOT prove independent feed correctness.**
> Clean enough to paper. Not yet clean enough for capital.

This sentence MUST appear in every Lane A candidate's deployment notes. No promotion authority may interpret DATA_AUDIT_GREEN as "the data problem is fully solved forever."

## §2 — The split decision (load-bearing)

| Stage | Status |
|---|---|
| **Lane A paper deployment** | **ALLOWED** on current DATA_AUDIT_GREEN evidence (candidates reproducible within current feed) |
| **Live / prop promotion** | **BLOCKED** until DSCL passes (feed correctness independently verified) |
| **Lane B research / new candidates** | **PAUSED** until Lane A paper deployment plan is reviewed |

## §3 — DATA_AUDIT_GREEN scope (locked definition)

DATA_AUDIT_GREEN means ALL of:
- Signal hashes deterministic across re-runs
- Regen metrics match committed exactly (n, PF, median)
- File hash recorded for provenance
- Cost model canonical (`engine/asset_config.py`)
- No silent missing-data fallbacks

DATA_AUDIT_GREEN does NOT mean:
- The vendor's data is correct vs CME official settlements
- The vendor's data matches a secondary vendor's data
- Rollover and session-boundary handling produces canonical values
- Paper-execution will reproduce backtest fills

These are DSCL responsibilities, not data-audit responsibilities.

## §4 — DSCL components (9 required)

Every candidate proposed for live/prop must have a written DSCL packet covering:

| # | Component | What it answers |
|---|---|---|
| 1 | **Exact feed/vendor declaration** | What dataset (e.g., Databento GLBX.MDP3 historical)? |
| 2 | **Symbol mapping** | How is the continuous contract constructed? Which child contracts? |
| 3 | **Session template** | RTH start/end, special-session handling (early close, holidays) |
| 4 | **Timezone handling** | Bar timestamps timezone, DST transitions, midnight rollover |
| 5 | **Roll logic** | Calendar-roll vs volume-roll, back-adjustment method, gap-clip vs gap-preserve |
| 6 | **Bar construction method** | Trade-based vs quote-based, last-trade vs midpoint, missing-bar policy |
| 7 | **CME settlement / reference comparison** | Daily OHLCV vs official CME settlements, sampled per §5 bucket categories |
| 8 | **Secondary vendor spot-check** | Independent licensed CME feed comparison on sampled days per §5 |
| 9 | **Paper execution reconciliation** | Expected vs actual fills, slippage, rejected orders, session handling during paper period |

## §5 — Named sample categories (MANDATORY, not random)

DSCL reference checks (component 7) and secondary vendor spot-checks (component 8) MUST cover ALL of these named categories. Random sampling alone is INSUFFICIENT.

| # | Category | Why mandatory |
|---|---|---|
| 1 | **Largest loss days** | If reality differs from backtest on losses, paper-to-live transition is unsafe |
| 2 | **Largest win days** | If reality differs from backtest on wins, expectancy estimates are wrong |
| 3 | **Candidate signal days** | The exact days the strategy traded must be verifiable |
| 4 | **Event / news-adjacent days** | FOMC, NFP, CPI ± 1 day — vendor-specific anomalies cluster here |
| 5 | **Rollover-adjacent days** ⚠️ | Mandatory per R4 + campaign experience — roll/gap behavior is a distinct vendor-specific failure mode that random sampling will MISS |
| 6 | **Session-boundary / overnight-gap days** | Long-weekend opens, post-holiday opens, half-day sessions |

**Per operator:** "Rollover-adjacent days are mandatory, not optional random samples, because prior campaign findings showed roll/gap behavior can be a distinct vendor-specific failure mode."

## §6 — Recommended source stack (operator-specified)

| Layer | Purpose | Recommended source |
|---|---|---|
| Primary research/backtest feed | Main OHLCV/tick source for strategy generation | Databento CME Globex / GLBX.MDP3 |
| Official settlement/reference check | Daily session close, settlement, volume, high/low sanity | CME Group daily settlements / CME DataMine |
| Secondary vendor spot-check | Independent cross-check on named categories | dxFeed / second licensed CME feed |
| Broker execution reality | Paper/live fill comparison | Tradeify / NinjaTrader / Tradovate execution logs |

## §7 — Promotion-gate rule

No candidate may move from paper to live/prop unless ALL of:

1. Components 1-6 of DSCL are written and committed
2. Component 7 (CME settlement comparison) covers all 6 named sample categories from §5 with documented evidence
3. Component 8 (secondary vendor spot-check) covers all 6 named sample categories from §5 with documented evidence
4. Component 9 (paper execution reconciliation) shows no material deviation between expected and actual fills during the paper observation period
5. Written operator review of the complete DSCL packet

## §8 — Lane B build queue if reopened

If Lane B research is reopened, the DSCL infrastructure becomes the **preferred Forge build queue** before any new candidate research:

| Priority | Build target | Reusability |
|---|---|---|
| 1 | Data-lineage declaration template (markdown form for components 1-6) | All future candidates |
| 2 | Automated CME settlement cross-check script (component 7) | All futures candidates |
| 3 | Rollover-day audit harness (§5 category 5) | All futures candidates with hold > 0 |
| 4 | Paper execution reconciliation reporter (component 9) | All paper-deployed candidates |
| 5 | Promotion-gate report generator (synthesizes §7 above) | All live/prop promotion decisions |

These are reusable infrastructure, not single-candidate builds. They benefit every future Lane A candidate, not just the current 4.

## §9 — Constraint matrix during HOLD

| Activity | Status |
|---|---|
| Lane A paper deployment planning | ALLOWED |
| Lane A paper trading (after plan review) | ALLOWED |
| Lane A live/prop promotion | BLOCKED until DSCL §7 satisfied |
| Lane B new candidate research | PAUSED until Lane A paper plan reviewed |
| Lane B DSCL infrastructure build | ALLOWED only if Lane B is explicitly reopened with DSCL build mandate |
| Registry / scheduler / portfolio mutation | NONE |
| OpenClaw / asset_config / calendar overrides | NONE |

## §10 — Sprint state implications

Lane A's 4 packaged candidates remain the campaign deliverable. The DSCL policy adds a future gate without blocking the current paper-deployment path.

- Paper observation period gives natural runway (typically 30-90 days) to stand up DSCL infrastructure
- DSCL components 1-6 (declaration) can be drafted BEFORE paper starts for each Lane A candidate as part of deployment notes
- DSCL components 7-9 (verification) can proceed during paper observation
- Live/prop decision gated by §7 review

## §11 — Cross-reference

- `docs/fql_forge/paper_packet_drafts/LANE_A_BATCH_2026-06-12.md` — candidates being deployed
- `docs/fql_forge/sprint_state_hold_2026-06-13.md` — sprint state synthesis
- [[feedback_evidence_integrity_failsafe]] — fail-closed plumbing rule
- [[feedback_proactive_plumbing_inspection]] — inspect-don't-infer
- [[feedback_hold_continuity_canonical_filter]] — R1 doctrine (data integrity)
- R4 finding (cycle 11k) — multi-day gap on MGC NFP that motivated rollover-mandatory clause
