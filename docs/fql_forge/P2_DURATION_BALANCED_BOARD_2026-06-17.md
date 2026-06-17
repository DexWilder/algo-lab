# P2 Duration-Balanced Curve Spread — One Retest — 2026-06-17

> The ONE approved predeclared retest (structurally-correct form of P2). Report-only. Evidence: `forge_cycle_2026-06-17e_p2_duration_balanced.json`. Not a rescue tweak — the naïve 1:1 spread was duration-contaminated (ZB-dominated); this is the dollar-duration-neutral expression. One variant only, no filters, no sweep, no mutation.

## Predeclared (fixed before running)
- DV01 ($/contract/bp, standard CME-ballpark): **ZF = 45, ZN = 65, ZB = 130**. Leg size = 1/DV01 → dollar-duration-neutral.
- Signal: long best-rolldown tenor, short worst-rolldown tenor (rolldown = own-tenor yield − next-shorter yield).
- Same 1-trading-day FRED lag; `merge_asof(backward, allow_exact_matches=False)`; 2019–2026; 1,969 rows, no-lookahead verified.

## Result
**KILL** — PF 0.889, median −$0.05, net −$332, H1/H2 0.859/0.926, years positive 1/8, era-thirds [0.84, 0.92, 0.92], yr-excl-min 0.862, corr-to-MNQ +0.037. Decorrelated, but **no edge** (slightly net-negative). The correct structural form fails as cleanly as the naïve one.

## Branch status: FRED YIELD-CURVE BRANCH CLOSED (mapped/dead)
All three FRED-yield-curve carry/curve expressions on ZN/ZF/ZB, 2019–2026, fail:
- `carry_rotation` — KILL
- naïve `carry_spread` (1:1) — KILL
- **duration-balanced spread — KILL**

→ The FRED yield-curve branch is **closed as mapped/dead.** No further curve-parameter tinkering (per operator: one clean retest justified, endless tinkering is not).

## What remains open (NOT closed by this)
- **P1 futures roll-yield** (commodity-style term-structure carry) — a *distinct* mechanism. FRED yields are NOT a substitute for futures roll yield. **Still feed-blocked** pending multi-contract per-expiry (F2) rates futures. Never tested → not dead.
- This result does **not** say "daily rates carry is dead" — only the FRED-yield-curve proxy forms are.

## State
`LEVER_B1_FEED_GATED_NOT_IDLE`. WP-B1 (auctions) runs first when `data/feeds/treasury_auctions.csv` lands. P6 (FX carry) feed-ready, unscreened, separate approval. True daily WH2 remains OPEN. No activation/registry/scheduler/portfolio/live/prop mutation.
