# Pre-Flight: Item #3 — Cost/Slippage Audit + Edge-Cushion Model

**Filed:** 2026-05-19
**Authority:** T1 (pre-flight); T2 (build approval)
**Lane:** 2 (governance fix; affects backtest interpretation, not strategy logic)
**Status:** APPROVED 2026-05-19 — execute next session. Scope finalized with Piece D added per operator. **No build today.**
**Sprint:** Phase 2 / Paper-Readiness Sprint, Item #3.

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

- Target ~1.25 sessions execution (A+B+C+D). If exceeded:
  - Pieces A, C, D are blocking for sprint and must ship together.
  - Piece B (cushion analyzer) may defer if it overruns past 0.5 session — A+C+D can still produce net PFs without the cushion verdict layer (just no GREEN/YELLOW/RED grading).
- Single commit per piece, atomic revert path retained per piece.
- For Piece A: explicitly document each assumption (commission, slippage tier, source) in code comments alongside the dict entry, so the operator can audit assumptions without grepping.
- For Piece D: include a side-by-side gross vs net rank-change column. The rank inversions are the operator-readable finding.

---

## Operator decision

**APPROVED 2026-05-19** — execute A+B+C+D next session. Scope adjustment per operator: added Piece D (sprint-candidate cost-aware re-read) so the 12/11 correlation-matrix set gets cost-aware scoring before Item #8 top-3 selection inherits any gross-PF artifact.

Guardrails locked:
- No pool expansion before Item #3 ships
- No Sentinel build before Item #3
- No status mutation (probation or otherwise) — re-reads produce decision packets, not state changes
- No Lane A changes
- No scheduler / source-helper changes

---

*Filed 2026-05-19, approved same day. Lane 2 governance/audit. Pre-flight only — execute next session per proven pre-flight pattern. Net of audit: cost is already in the engine but 11 of 17 assets run at zero — including 2 of 3 probation candidates. Item #3 fixes that, adds edge-cushion analysis, and re-reads probation + the 12 correlation-matrix candidates so the entire paper-readiness ranking sits on cost-aware evidence.*
