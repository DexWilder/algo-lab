# Paper-Readiness Packet #1 — Operator-Review Summary

> **Subject:** EVT-NFP-MGC-Long-2h
> **Status:** awaiting operator decision (accept / return / reject)
> **NOT paper-approved. NOT live-approved. NOT registry promotion.**
> Accepting as Paper-Readiness Packet #1 = the draft becomes a formal sprint
> deliverable and advances to the next validation rung. Paper/live deployment
> remains a separate, gated decision.
>
> Full evidence: `docs/fql_forge/paper_packet_drafts/EVT-NFP-MGC-Long-2h_2026-06-04.md`

---

## 1. Thesis (one paragraph)

The U.S. BLS Employment Situation report (Non-Farm Payrolls, NFP) is one of the largest scheduled macro information events for global rates and commodity markets. Post-release MGC drift is **biased long** on a 2-hour holding window from 08:35 → 10:35 ET. The bias is **direction-blind** — it does not depend on NFP being a beat or a miss; it depends on the post-release drift pattern being positive in expectation. Evidence (8/8 years positive, regime-uniform across DXY/vol/real-yield splits) is consistent with this being a structural drift phenomenon, not a discretionary directional bet.

## 2. Rule definition

| Field | Value |
|---|---|
| Asset | MGC (micro gold futures, CME) |
| Bar timeframe | 5-minute |
| Event | BLS Employment Situation release at 08:30 ET |
| Calendar | 1st Friday of each month with documented BLS holiday-deferral exceptions (Jan 2021, Jul 2025) |
| Entry | Long MGC at the open of the **+1 bar** after the event timestamp (08:35 ET) |
| Exit | Mechanical at close of **+24 bar** (~2h hold; 10:35 ET) |
| Size | 1 contract |
| Stop | None in v1 (mechanical time exit) |
| Filter | None — every documented NFP release is traded |

## 3. Key metrics

| Metric | Value | Gate status |
|---|---:|---|
| Sample period | 2019-06 → 2026-06 | 7-year span ✓ |
| n trades | **84** | minimum sample met |
| Profit factor (net) | **2.264** | well above STRONG (1.30) ✓ |
| Median trade | **+$21.76** | strongly positive ✓ |
| Net PnL | $8,664 | — |
| Max drawdown | -$1,179 | — |
| Win rate | 54.8% | above 50% ✓ |
| Avg win | $337.30 | — |
| Avg loss | -$180.32 | 1.87 R |
| Max-year concentration | 27.8% | well under 40% workhorse gate ✓ |
| Top-1 trade share | 17.0% | well under 30% ✓ |
| Years positive | **8/8** | unanimous ✓ |
| Era split (1/2/3) | PF 3.35 / 1.92 / 2.13 | all eras positive ✓ |
| Year-exclusion PF range | [2.006, 2.695] | removing any single year leaves PF ≥ 2.0 ✓ |
| Rolling 12-event PF > 1.0 | **89%** | strong robustness ✓ |
| Rolling 12-event PF > 1.2 | **85%** | ✓ |

## 4. Evidence-integrity audit result

**Overall verdict: GREEN** (artifact: `docs/reports/evidence_integrity/2026-06-04_forge_cost_integrity_audit.md`)

| Dim | Verdict | Note |
|---|---|---|
| A. Cost source | GREEN | MGC VALIDATED tier; no defaults/placeholders |
| B. Cost stress | GREEN | PF 2.21 at 3× cost + 2× slip; median stays $19.28 |
| C. Edge quality | GREEN | net median $21.76; gross $25.00; top-1 17.0%; pct trades net ≤ 0 = 45.2% (consistent w/ 54.8% win rate) |
| D. Lookahead | GREEN | entry strictly after event; exit strictly forward |
| E. Calendar | GREEN | 97.9% rule-actual match; ΔPF -0.057 immaterial |
| F. Survivorship | GREEN | MGC 2019-2026 full span; 2 big jumps (roll noise) |
| G. Duplicate exposure | GREEN | no similar candidate in cohort |
| H. Regime overlay (diagnostic) | INFO | all 6 regime splits PF > 1.0; weakest real-yield-rising still PF 1.503 |

## 5. Remaining risks / honest caveats

1. **Regime change risk** — thesis depends on post-NFP drift pattern persisting. Sibling FOMC-ZN family showed structural change post-2023; NFP-MGC has not, but the risk is real for any event-driven macro candidate.
2. **NFP surprise asymmetry not tested** — Option A (ship without consensus split) was chosen per direction-blind thesis; full beat/miss/inline split deferred to future vendor data (#37 Option A).
3. **Sample size** — n=84 is statistically credible at cheap-screen and deep-screen but **not large** by quant-finance standards. Forward-trading would add ~12 events/year.
4. **Selection bias** — this is the first PAPER_PACKET_DRAFT_CANDIDATE out of 250+ tested in 4-day campaign (~0.4% hit rate). High rejection suggests robust selection criteria; also means the candidate is near the upper edge of "good enough" rather than far above it.
5. **EOD sibling caveat** — `EVT-NFP-MGC-Long-EOD` (exit +72 bars) has higher metrics (PF 3.185, median $55.26) BUT Era 3 PF 6.69 is concentrated; classified WATCH_FOR_DEEP_SCREEN_CONTINUATION not sibling-packet. Operator may eventually want EOD or hybrid.
6. **Cost-stress survivability is strong but assumes Databento-tier cost basis** — broker rate verification before paper/prop is the next-rung blocker.

## 6. Exact next validation rung (if accepted)

If accepted as Paper-Readiness Packet #1:

1. **Broker / prop cost verification** — confirm `engine/asset_config.py` MGC cost assumptions match operator's intended execution venue.
2. **NFP calendar live-feed strategy** — decide whether automated BLS calendar pull (vs canonical-rule-based + manual operator confirmation) is needed before forward deployment.
3. **Forward-trade infrastructure decision** — operator-only: whether to wire EVT-NFP-MGC-Long-2h into `forward_paper.py` runner. This is a registry mutation and Lane A change; explicitly OUT of scope for Forge Lane B.
4. **EOD-sibling final decision** — keep WATCH or escalate as separate candidate.
5. **NFP surprise series acquisition** — defer per Option A unless operator changes direction.

## 7. Explicit decision options

| # | Decision | Implication |
|---|---|---|
| **1** | **Accept** as Paper-Readiness Packet #1 — formal sprint deliverable, ready for next validation rung | Lock in artifact; advance to operator-led broker/prop verification + forward-trade infrastructure conversation. **No paper/live deployment.** |
| 2 | Return for additional validation | Specify which dimension is insufficient; Forge runs targeted refinement |
| 3 | Reject | Rare; would require identifying a specific evidence flaw not caught by audit GREEN |

**Recommendation:** Option 1 — packet meets every quantitative gate the campaign has set, by wide margins, with no single dimension marginal. The audit GREEN means no missing-cost, lookahead, or calendar trap. Risks (§5) are honest caveats, not blockers. Accepting as Packet #1 does NOT commit to paper/live trading — it simply locks the artifact as the first formal sprint deliverable.
