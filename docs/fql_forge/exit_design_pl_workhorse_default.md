# Exit-Design Heuristic — profit_ladder as Daily-Workhorse Default

> **Status:** CODIFIED FQL doctrine. Locked 2026-06-08 per operator decision #90.
> **Authority:** Lane B research heuristic; informs candidate design and search prioritization. Does NOT mutate existing strategies, registry, or runtime.
> **Scope:** Daily-workhorse archetype only. Not a universal law.

## Rule

**When designing a daily-workhorse strategy candidate (trades-per-year ≥ 100, intraday or daily holding period, target Sharpe ≥ 1.0), use `profit_ladder` as the default exit. Use `fixed_ratio` only when the candidate's thesis explicitly requires full-target capture (e.g., breakout-thrust completion, mean-reversion to specific level), and document the thesis-specific justification.**

## Evidence basis

Two cycles (2026-06-05c and 2026-06-08b) compared `profit_ladder` (PL) vs `fixed_ratio` (FR2, ratio=2.0) under a 5-rung cost-stress break-even ladder across 10 candidate pairs spanning 4 entry families (orb_breakout, donchian_breakout, prior_day_break, prior_day_fade) on 4 assets (MGC, MCL, MES, MYM):

| # | Pair | PL break-even rung | FR2 break-even rung | Winner |
|---:|---|---|---|---|
| 1 | MCL-ORB-Short | 2× + 2 ticks | 1.5× + 1 tick | **PL +2** |
| 2 | MGC-ORB-Short | beyond 4× | beyond 4× | TIED |
| 3 | MGC-ORB-Long | 2× + 2 ticks | 2× + 2 ticks | TIED |
| 4 | MGC-PriorDayBreak-Long | 2× + 2 ticks | 1.5× + 1 tick | **PL +2** |
| 5 | MCL-Donchian-Short | 1.5× + 1 tick | 1× baseline (already neg) | **PL +1** |
| 6 | MES-ORB-Long | beyond 4× | beyond 4× | TIED |
| 7 | MYM-ORB-Both | beyond 4× | beyond 4× | TIED |
| 8 | MGC-Donchian-Long | 4× + 2 ticks | 2× + 1 tick | **PL +2** |
| 9 | MGC-PriorDayBreak-Short | beyond 4× | beyond 4× | TIED |
| 10 | MGC-ORB-Both | 4× + 2 ticks | 4× + 2 ticks | TIED |

**Aggregate: PL wins 4/10, TIED 6/10, FR2 wins 0/10. PL_or_tied = 10/10.**

## Codification threshold

Operator-set threshold (#90): codify if PL_or_tied ≥ 8/10 AND FR2_wins = 0. Threshold met **conclusively** at 10/10 and 0.

## Mechanism

PL captures partial profit at multiple thresholds (e.g., 1R, 2R, 3R), so cost increases only erode the MARGINAL trades that no longer reach a given threshold. FR2 requires achieving the full ratio target, so any cost increase shifts the entire profit calculation directly. Under cost stress, PL retains more of its baseline edge.

## What this rule is NOT

- **NOT** a universal law. Tail-engine, sparse-event, and carry-spread archetypes are not in scope.
- **NOT** a registry mutation. Existing strategies retain their original exit configurations.
- **NOT** a primitive deletion. `fixed_ratio` remains in EXIT_MAP for thesis-specific use.
- **NOT** binding on operator decisions to retain FR2-exit candidates if their thesis warrants.

## Application

When generating new candidate specs in Forge cycles:
1. Default new daily-workhorse candidates to `profit_ladder` exit unless a thesis-specific reason favors FR2.
2. When a `fixed_ratio` candidate appears in the cheap-screen with similar PF to a `profit_ladder` sibling, prefer the PL variant for promotion-track evaluation; treat FR2 as a sensitivity comparison.
3. When a sparse archetype (event, carry, session-transition) is being designed, this rule does NOT apply — choose the exit by thesis.

## Counter-example clause

If a future PL vs FR2 pair shows FR2 STRICTLY more cost-robust than PL (FR2_wins = 1 in a fresh study of 5 pairs), this rule is REVOKED pending re-evaluation. Until then, the rule stands.

## Source artifacts

- `research/data/fql_forge/pl_vs_fr2_cost_fragility_investigation.md` (n=5 prior cycle)
- `research/data/fql_forge/reports/forge_cycle_2026-06-08a.json` (n=5)
- `research/data/fql_forge/reports/forge_cycle_2026-06-08b.json` (n+5)
- `research/data/fql_forge/kill_taxonomy.json` key `_HEADLINE_2026-06-08b_PL_DEFAULT_CODIFIED`
