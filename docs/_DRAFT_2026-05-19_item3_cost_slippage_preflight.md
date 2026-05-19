# Pre-Flight: Item #3 — **Cost Integrity Reset** (was: Cost/Slippage Audit + Edge-Cushion Model)

**Filed:** 2026-05-19
**Authority:** T1 (pre-flight); T2 (build approval)
**Lane:** 2 (governance fix; affects backtest interpretation AND adds fail-closed enforcement)
**Status:** APPROVED 2026-05-19 — execute next session. **Upgraded to "cost integrity reset" scope** per operator (added Pieces E/F/G; fail-closed enforcement is now in-scope, not a follow-up). **Piece H added same day** after plumbing inspection found the probation/promotion docs use gross/net-ambiguous PF language. **No build today.**
**Sprint:** Phase 2 / Paper-Readiness Sprint, Item #3. Highest-priority task before pool expansion, validation funnel, or paper packets.
**Related doctrine:** `feedback_evidence_integrity_failsafe.md` (locked 2026-05-19) — the hard rule this work enforces.
**Execution order (operator-locked):** E → A → H → C/D/G. Piece E first so the engine fails closed before any other work touches cost-dependent code.

---

## Headline finding (surfaced while drafting; should reshape Item #3)

Cost is already in the engine — `engine/backtest.py` applies commission + slippage per trade. **But the cost config covers only 6 of 17 supported assets.**

```python
# engine/backtest.py:13-18
COST_DEFAULTS = {
    "MES": {"commission_per_side": 0.62, "tick_size": 0.25, "slippage_ticks": 1},
    "MNQ": {"commission_per_side": 0.62, "tick_size": 0.25, "slippage_ticks": 1},
    "MGC": {"commission_per_side": 0.62, "tick_size": 0.10, "slippage_ticks": 1},
    "ES":  {"commission_per_side": 1.24, "tick_size": 0.25, "slippage_ticks": 1},
    "NQ":  {"commission_per_side": 1.24, "tick_size": 0.25, "slippage_ticks": 1},
    "GC":  {"commission_per_side": 1.24, "tick_size": 0.10, "slippage_ticks": 1},
}
```

Assets that fall through to defaults of **zero commission, zero slippage**:
M2K, MCL, MYM, ZN, ZF, ZB, 6B, 6E, 6J, ZC, ZS, ZW, SI, HG, plus anything else.

**Direct probation-pool impact:**

| Strategy | Asset | Cost basis | Baseline PF |
|---|---|---|---|
| XB-ORB-EMA-Ladder-MNQ | MNQ | ✅ configured (0.62 + 1 tick) | 1.62 |
| XB-ORB-EMA-Ladder-MCL | MCL | ❌ **zero** | 1.33 |
| XB-ORB-EMA-Ladder-MYM | MYM | ❌ **zero** | 1.67 |

The MCL 1.33 PF and MYM 1.67 PF are **gross**, not net. Their real edge after realistic transaction cost is unknown. The MCL number is closer to the cushion boundary; MYM has more headroom but is also the lowest-sample probation candidate (340 trades).

This reframes Item #3 from "build a cost model" into **"audit and complete the cost configuration that already exists, then add an edge-cushion analysis layer."** Less infrastructure, more candidate-relevant.

---

## Counter-argument (per challenge-layer doctrine)

> *Updating cost defaults could destabilize the probation read. If MCL re-runs at PF 1.10 net, we have a forward-fitness question we didn't have before. Maybe leaving it gross was load-bearing for the "ADVANCE" calls and we should not touch it during the sprint.*

**Why we proceed anyway:**
- The truthful PF is the only PF that should drive paper-readiness packets. A gross PF advancing a candidate to paper is **exactly** the "cheap-screen evidence overrating itself" failure mode the 5/18 doctrine forbids.
- If MCL re-runs net at PF 1.10, that is data — not damage. Better to learn it now than in paper.
- Reversal criteria below limit the blast radius if the cost-update turns out to be uncalibrated.

## What would prove this decision wrong

- Building Item #3 takes longer than 1 session (estimate is 0.5-1 session; if it grows past 1, stop and re-pre-flight)
- The cost-config update flips >50% of existing verdicts → the cost inputs are uncalibrated, not the strategies broken. Pause and validate inputs before propagating.
- The edge-cushion layer adds noise instead of signal (e.g., all candidates "pass" cushion regardless) → cushion thresholds need recalibration.

## Reversal criteria

- All cost-config changes land in a single commit so a single revert restores prior cost basis.
- The cost-adjusted PFs are written to a new `cost_adjusted_pf` field, NOT overwriting `profit_factor`. Original gross PF retained for diff analysis.
- If the gross→net delta is implausible (e.g., MCL drops from 1.33 to <0.9), treat the slippage estimate for MCL as suspect, not the strategy.

---

## Scope: Item #3 v0 (~1 session)

**Three discrete pieces. Ship together; reversion atomic.**

### Piece A — Cost config audit (~0.25 session)

For each of the 11 unconfigured assets, populate `COST_DEFAULTS` with:

- `commission_per_side`: from broker schedule (research/data/asset_config notes if present, else operator-confirmed values)
- `tick_size`: from `engine/asset_config.py` (already canonical)
- `slippage_ticks`: starting estimate by liquidity tier
  - Tier 1 (high liquidity, e.g., MES/MNQ/MGC): 1 tick
  - Tier 2 (medium, e.g., MCL/MYM/ZN/6E/6J): 2 ticks
  - Tier 3 (lower, e.g., M2K/SI/HG/ZC/ZW/ZS/6B/ZF/ZB): 2-3 ticks (operator-set)

Reference: `engine/asset_config.py` is the source of truth for tick_size and point_value. Don't duplicate. Pull tick_size from there if not already.

### Piece B — Edge-cushion analyzer (~0.5 session)

New file `research/cost_cushion.py`. For each strategy in the registry runner pool, compute:

```
gross_pf
net_pf (re-run backtest with current cost config)
avg_trade_net
cost_per_trade ($ and % of gross profit)
cushion_ticks_to_breakeven  -- how many additional ticks of slippage before PF drops to 1.0
cushion_pct  -- (gross_pf - net_pf) / gross_pf
verdict:
  - GREEN if net_pf >= 1.15 AND cushion_ticks >= 2
  - YELLOW if net_pf >= 1.15 AND cushion_ticks < 2  (passes today, fragile)
  - YELLOW if net_pf in [1.05, 1.15)                (marginal)
  - RED   if net_pf < 1.05
```

Output: `docs/reports/cost_cushion/YYYY-MM-DD_cost_cushion.md` table + JSON.

Re-uses existing `run_backtest` — does NOT reimplement. Just calls it with the now-correct cost config.

### Piece C — Probation re-read (~0.25 session)

Run the cushion analyzer against the 3 probation candidates (MNQ/MCL/MYM) explicitly. Report net PF, cushion, verdict. If MCL or MYM drops to YELLOW/RED, surface as decision packet — do NOT auto-mutate probation status.

### Piece D — Sprint-candidate cost-aware re-read (~0.25 session, added by operator approval 2026-05-19)

Run the cushion analyzer against the **12 correlation-matrix candidates** from Item #2 (the set that produced the 11-exposure-cluster dedup). These are the candidates feeding the top-3 selection at Item #8 — their cost-aware scoring is the gate for any paper-readiness ranking.

- Re-score all 12 under the now-correct cost config
- Emit cost-aware ranking alongside gross ranking
- Flag any rank-inversion between gross and net (candidate that looked top-tier on gross but drops out on net) — that finding is the value
- No registry mutation; no auto-status changes; results feed Item #8 selection only

Required because the operator-stated goal is: *"Fix cost assumptions before trusting any paper-readiness ranking."* Without Piece D, Item #8 (top-3 selection) inherits the same gross-PF artifact this whole pre-flight is correcting.

### Piece E — Fail-closed enforcement in engine + reports (~0.25 session, added 2026-05-19 per evidence-integrity doctrine)

Engine and report layers must refuse silent zero-cost substitution for any decision-grade evaluation.

- `engine/backtest.py::get_cost_params`: when called by a decision-grade caller (probation re-read, cushion analyzer, paper-readiness packet generator, runner-pool scoring) and the asset has no `COST_DEFAULTS` entry, raise `InvalidCostAssumption(asset)`. Exploration-tier callers may opt into a `allow_uncosted=True` flag with an explicit `EXPLORATION_TIER` label on the output.
- Forge daily reports, weekly scorecard, cushion analyzer, paper-readiness packet generator: print the cost block per asset at the top of the output. Absence of cost block = report is invalid; gate the writer.
- Tag any candidate whose evaluation tried to fall through as `INVALID_COST_ASSUMPTION` — not zero-cost.

Wires in the fail-closed rule from `feedback_evidence_integrity_failsafe.md` at the only two places it matters: the engine entry point and the report writer. Without this piece, the doctrine is decoration — exactly what the doctrine-completion-fallacy rule forbids.

### Piece F — Expanded re-read coverage (~0.25 session, added 2026-05-19)

Pieces C and D cover probation (3) and correlation-matrix set (12). The full at-risk surface is wider:

- All `active` and `core` strategies (3 core + any active per registry)
- All `probation` strategies (8 total per current count, not just XB-ORB-Ladder MNQ/MCL/MYM)
- All `monitor` / watch strategies (2 per current count)
- Any strategy in the Forge runner pool (19 per supply-chain audit)
- The 12 correlation-matrix candidates

Deduplicate the union; re-score each under correct cost config; report gross-vs-net delta. Anything outside this surface (rejected, archived, idea-status-only) defers to a later sweep — not blocking the sprint.

### Piece H — Patch probation/promotion docs to explicit net-PF language (~10 min, added 2026-05-19 per plumbing inspection)

Surfaced 2026-05-19 in the proactive inspection follow-up: every probation/promotion gate doc currently says "PF" without a gross/net qualifier. Examples:

- `docs/XB_ORB_PROBATION_FRAMEWORK.md:60` — "Forward PF ≥ 1.15"
- `docs/XB_ORB_PROBATION_FRAMEWORK.md:75,83` — "Forward PF < 0.90 after 30+ trades" / "Forward PF < 0.80 after 50+ trades"
- `docs/ELITE_PROMOTION_STANDARDS.md:64,101,140` — "Backtest PF: >= 1.2 / >= 1.4 / >= 1.1"
- `docs/ELITE_PROMOTION_STANDARDS.md:78,118,159` — "Forward PF < 0.7 after N trades"
- `docs/PROBATION_REVIEW_CRITERIA.md:50,56` — "Forward PF > 1.2" / "PF 1.0-1.2"

The decision doctrine must match the engine behavior. After Piece E fail-closes the engine, the gate docs need to explicitly say **net PF (cost-adjusted)** so future operator reads can't ambiguously interpret a gross number as gate-passing.

**Concrete edits:**

- For every "PF" reference in a gate or threshold context: prefix with "net" or append "(cost-adjusted)"
- Add a one-line preamble at the top of each doc: *"All PF references in this document are net (cost-adjusted) PFs. Gross PFs are not gate-eligible; see `feedback_evidence_integrity_failsafe.md`."*
- The spread-template doc (`ELITE_PROMOTION_STANDARDS.md:241`) already says "Cost-adjusted PF" — make that the canonical phrasing across all docs.
- No registry edits, no threshold value changes — language only.

10 minutes. Doc-only. Fits in the existing Item #3 session without scope creep.

### Piece G — Formal gross-vs-net impact report (~0.25 session, added 2026-05-19)

Single canonical report — `docs/reports/cost_integrity_reset/2026-MM-DD_cost_integrity_reset.md` — that aggregates the Pieces C/D/F results into the operator-required structure:

**Per-candidate table:**
| Strategy | Asset | Gross PF | Net PF | Gross PnL | Net PnL | Gross avg trade | Net avg trade | Cost % of avg trade | Rank before | Rank after | Verdict changed? |

**Conclusion section (mandatory):**
- **Unaffected candidates** — gross ≈ net, cost <5% of avg trade, no rank movement
- **Weakened but still viable** — net PF ≥ 1.15, cushion intact, decision unchanged
- **Marginal after costs** — net PF in [1.05, 1.15); decision packet required
- **Failed after costs** — net PF < 1.05; decision packet required; status review queued
- **Previous conclusions requiring revision** — explicit list of prior calls (probation ADVANCE, ranking decisions, paper-readiness claims) that the new evidence invalidates or weakens

This conclusion section is the operator-readable deliverable. The per-candidate table is the audit trail.

---

## Explicitly NOT in v0

- ❌ Per-strategy slippage estimates (treats slippage as asset-level constant; strategy-level is Phase 3)
- ❌ Session-conditional slippage (e.g., higher slippage during news windows)
- ❌ Order-book-aware fill modeling (full execution simulator is out of scope)
- ❌ Spread-aware FX cost (FX defaults use a flat slippage estimate; refinement is Phase 3)
- ❌ Recompute cost-adjusted PFs for the 60+ rejected/archived strategies (only runner pool matters for sprint)
- ❌ Any registry status changes from this work — purely analytical, decisions are separate

---

## How Item #3 unlocks the rest of the sprint

| Downstream item | Why it needs Item #3 |
|---|---|
| Item #5 pool hygiene | Needs net PFs to assess whether pool members are still pass-grade |
| Item #6 stale-WATCH | Same — re-read watch list with net PFs |
| Item #7 validation funnel v0 | Sprint sequence explicitly lists "cost-adjusted PF" as a funnel input |
| Item #8 top-3 selection | Top-3 picked on net PF + cushion, not gross |
| Item #9 paper-readiness packets | Packet template requires `cost-adjusted metrics` field |
| Pool-expansion batch (post-Item-#3) | The 3-pick batch from `_DRAFT_2026-05-19_pool_expansion_packet.md` runs under correct cost from day one |

So this single 1-session item is a gate to all downstream sprint work.

---

## Output format (what the operator sees)

`docs/reports/cost_cushion/YYYY-MM-DD_cost_cushion.md`:

```
# Cost Cushion — YYYY-MM-DD

## Probation pool (priority)
| Strategy | Asset | Gross PF | Net PF | Cushion (ticks) | Verdict |
|---|---|---|---|---|---|
| XB-ORB-EMA-Ladder-MNQ | MNQ | 1.62 | <net> | <n> | <v> |
| XB-ORB-EMA-Ladder-MCL | MCL | 1.33 | <net> | <n> | <v> |
| XB-ORB-EMA-Ladder-MYM | MYM | 1.67 | <net> | <n> | <v> |

## Runner pool (full)
| <19 strategies, same columns> |

## Findings & routing
- <surfaced issues per finding>
- <fix-now / sprint-backlog / decision items>
```

---

## Build rule

- Target **~2 sessions execution** (A+B+C+D+E+F+G+H). The reset is the highest-priority sprint task; the session estimate reflects scope expansion, not scope creep.
- **Execution order is operator-locked: E → A → H → C/D/G**, with B and F-tail interleaved opportunistically. Rationale: E first so the engine fails closed before any cost-dependent code runs; A second so the engine has real defaults to use; H third so the doctrine language matches engine behavior; then C/D/G produce the actual re-read evidence on a foundation that is now correct in all three layers (engine / config / doctrine).
- Blocking vs deferrable if overrun:
  - **Blocking (must ship before any candidate is re-quoted):** E (fail-closed enforcement), A (cost config), H (doc patch), C (probation re-read), D (correlation set re-read), G (impact report)
  - **Deferrable to a follow-up session:** B (cushion verdict layer — net PFs work without it), F's "watch/monitor" tail (probation + runner + correlation set still cover the urgent surface)
- Single commit per piece, atomic revert path retained per piece.
- Piece A: explicitly document each assumption (commission, slippage tier, source) in code comments alongside the dict entry. Conservative bias: when uncertain, lean higher slippage. Document the source — operator-confirmed value, broker schedule, public CME data, etc.
- Piece E: the `InvalidCostAssumption` exception path must be exercised by a test before any other piece is considered done.
- Piece G: the conclusion section is the deliverable. If the per-candidate table generates but the conclusion section is empty, the report is incomplete — do not ship.
- **Scope is now closed.** No further scope expansion during Item #3. Additional silent-default fixes belong in Item #3.5 (next session after #3).

## Hard constraint: no probation/paper/promotion decisions until the reset ships

While Item #3 is in flight, all probation reads, paper-readiness rankings, top-3 selections, and promotion considerations are **suspended on cost-related grounds.** Existing forward trades, evidence-tier labels, and qualitative analysis remain valid; PF-dependent decisions do not. This is operator-locked.

---

## Operator decision

**APPROVED 2026-05-19, upgraded same day** — execute A+B+C+D+E+F+G next session. Operator-locked scope expansion: this is now a **cost integrity reset**, not just an audit. The reset is the highest-priority sprint task before pool expansion, validation funnel, or paper packets.

Guardrails locked (unchanged + reinforced):
- No pool expansion before reset ships
- No Sentinel build before reset ships
- No status mutation (probation or otherwise) — re-reads produce decision packets, not state changes
- No Lane A changes
- No scheduler / source-helper changes
- **No probation/paper/promotion PF-dependent decisions while reset is in flight**

---

*Filed 2026-05-19, approved and upgraded same day. Lane 2 governance/audit + fail-closed enforcement. Pre-flight only — execute next session per proven pre-flight pattern. The reset corrects an evidence-integrity gap (11 of 17 assets ran at zero cost, including 2 of 3 probation candidates), enforces fail-closed defaults so the gap cannot silently recur, and produces a canonical impact report so the operator can see which prior conclusions need revision. After the reset, the pool-expansion 3-pick batch lands on correct cost from day one.*
