# P1/P2 Rates Carry/Curve — First-Cut Board — 2026-06-17

> One approved locked screen cycle against the acquired FRED yield curve (`treasury_yield_curve.csv`). Report-only. Evidence: `forge_cycle_2026-06-17d_p1p2_rates_carry.json`. No sweep, no synthetic fill, no mutation. Structural feed readiness was NOT treated as evidence.

## Audit trail (clean)
- **Feed:** 16,815 rows (1962→2026-06-15); missing = early-history series starts only; 2019+ overlap complete.
- **No-lookahead:** DGS dated D published ~EOD D → lagged one trading day; `merge_asof(backward, allow_exact_matches=False)` → **0 leak violations** (asserted). Decision on futures day D uses curve through D−1.
- **Join to ZN/ZF/ZB daily:** 2,053 futures days, **all matched**, median lag 1d / max 3d (holiday gaps absorbed). Coverage 135–289 rows/year, 2019–2026.

## Board (minimal predeclared variants)
| Variant | Mechanism | n | Verdict |
|---|---|--:|---|
| `carry_rotation` | long the best-rolldown tenor of {ZF,ZN,ZB} daily | 1,968 | **KILL** |
| `carry_spread` | long best / short worst rolldown (1:1, not duration-balanced) | 1,968 | **KILL** |
| _benchmark_ ZN buy&hold | context only — not a candidate | 1,968 | PF 0.94, −$17.8k (bonds bear market 2019–22) |

Rolldown proxy: own-tenor yield − next-shorter yield (ZF=dgs5−dgs2, ZN=dgs10−dgs5, ZB=dgs30−dgs10).

## What is and isn't ruled out (honest)
- **KILLED:** the simple daily **yield-curve-rolldown** carry (rotation + 1:1 spread) on ZN/ZF/ZB. Evidence-clean (no-lookahead audited, full coverage) — not a plumbing artifact.
- **NOT auto-run (logged as single RETEST pending approval):** the **duration-balanced** spread — the structurally-correct P2 form. Running it now to rescue a KILL would be within-cycle tweaking → withheld per discipline.
- **STILL FEED-BLOCKED:** the **futures roll-yield** version of P1 (term-structure carry) needs multi-contract per-expiry futures (F2). FRED provides yields, not futures roll. So FRED unlocked the yield-curve form (killed), not the roll-yield form.

## Verdict (NARROW — do not over-generalize)
This KILLs **only** the simple FRED-yield-curve versions — `carry_rotation` and the naïve best-vs-worst `carry_spread` — on **ZN/ZF/ZB, 2019–2026, under the approved first-cut lag/join assumptions.** It does **NOT** establish "daily rates carry/curve is dead." Two distinct branches remain unscreened:
- **duration-balanced P2 spread** — the structurally-correct curve expression (the naïve 1:1 spread is duration-contaminated, dominated by the ZB leg). Approved as ONE predeclared RETEST → see `P2_DURATION_BALANCED_BOARD_2026-06-17.md`.
- **futures roll-yield P1** — commodity-style term-structure carry; FRED yields are NOT a substitute for futures roll. **Still feed-blocked** (needs multi-contract F2). Kept separate.

If the duration-balanced retest also fails, the **FRED yield-curve branch** closes as mapped/dead — the futures roll-yield P1 stays open pending its feed.

## State
`LEVER_B1_FEED_GATED_NOT_IDLE` holds. WP-B1 (auctions) still first when `treasury_auctions.csv` lands. True daily WH2 remains OPEN. No activation/registry/scheduler/portfolio/live/prop mutation.
