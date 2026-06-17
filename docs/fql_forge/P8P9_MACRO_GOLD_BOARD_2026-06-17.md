# P8/P9 Macro-Driver Gold — First-Cut Board — 2026-06-17

> Report-only. Locked sequence + mandatory date-split OOS (train≤2022 / test≥2023). Evidence: `forge_cycle_2026-06-17f_p8p9_macro_gold.json`. No sweep, no synthetic fill, no mutation. No-lookahead: DFII10/T10YIE lagged 1 trading day (merge_asof backward, allow_exact_matches=False, asserted). MGC days 2019+ = 1,956, all matched.

## Strict classification rule (predeclared)
`GOLD_SLEEVE_ENHANCER` if |corr to long-gold| ≥ 0.5 · `WH2_CANDIDATE` if corr-MNQ <0.3 AND corr-long-gold <0.5 (genuinely distinct behavior) · else `PORTFOLIO_DIVERSIFIER_CAND` · `KILL` if not quality or OOS inverts.

## Board
| Variant | PF | OOS train/test | corr MNQ / long-gold | Verdict |
|---|--:|---|---|---|
| P8 real-rate long/short gold | 1.022 | 1.106 / **0.987** | −0.05 / −0.05 | **KILL** (no edge, OOS-fail) |
| P8 real-rate long-only gate | 1.209 | 1.121 / 1.268 | 0.085 / **0.573** | **GOLD_SLEEVE_ENHANCER** (not WH2) |
| P9 breakeven rotation gold↔rates | 1.046 | 1.001 / 1.080 | 0.077 / **0.608** | **KILL** (no edge; mostly holding gold) |

## Honest read
- **No WH2 candidate, no portfolio diversifier.** The macro drivers (real rates, breakevens) do not produce distinct daily portfolio behavior on a clean first cut.
- The **only survivor (P8 long-only gate)** is a **marginal gold-timing overlay** — OOS-consistent (no inversion, unlike the killed ZN-price gate), but **0.57-correlated to long-gold** → it's better gold *timing*, not new behavior. Capped at `GOLD_SLEEVE_ENHANCER`, and marginal (PF 1.209, barely over gate). The "gold macro driver" loophole did NOT produce a WH2.
- Real rates / breakevens being the *actual* drivers (vs the killed ZN-price proxy) did help one variant survive OOS — but only as gold timing, which is exactly what the guardrail was built to catch.

## Disposition
- P8 long/short, P9 rotation → **archived (KILL)**, no-repeat.
- P8 long-only gate → logged as a **marginal GOLD_SLEEVE_ENHANCER** (available IF we later refine the gold sleeve's timing; NOT the WH2 target, not pursued as diversifier).
- **Do NOT over-focus into gold.** P10 (dollar-driven gold) would likely reproduce the same gold-timing outcome (and be collinear with P8) → deprioritized. **Rotate to genuinely NON-gold drivers** next: P12 (WTI–Brent energy dislocation on MCL) and resolving the EIA crude-inventory feed — these target a different asset/driver, where actual diversification could come from.

## State
`FRED_YIELD_CURVE_BRANCH_CLOSED__FORGE_DISCOVERY_CONTINUES`. True daily WH2 OPEN. WP-B1 auctions still first when CSV lands. No activation/registry/scheduler/portfolio/live/prop mutation.
