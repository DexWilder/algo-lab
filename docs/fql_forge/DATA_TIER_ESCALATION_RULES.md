# Data-Tier Escalation Rules (2026-07-01) — the anti-false-exhaustion gate (P0)

> **False exhaustion is the most dangerous remaining failure class.** A family killed on thin data is not dead — its thin
> *expression* is dead. This gate makes that distinction machine-enforced. Wired into `forge_system_guardrails.py`,
> `adversarial_result_review.py`, `forge_family_map.py`, `forge_dashboard.py`, and `learning_state.json`.

## Tiers
| Tier | Data | Example |
|---|---|---|
| T0 | close-only / daily close | 5m/daily close series |
| T1 | daily OHLC | daily bars |
| T2 | intraday bars (no volume) | 5m/1m OHLC |
| T3 | intraday + volume | 1m OHLCV (our 7.9M-bar frontier) |
| T4 | per-contract / term-structure | ZT/ZF/ZN/ZB/CL/GC curves |
| T5 | event / surprise / positioning / flow | COT, CPI, EIA, auctions, FOMC, NFP |
| T6 | options / OI / gamma / microstructure / order-book | ES.OPT OI, GEX, tick |
| T7 | paid / specialized | vendor feeds |

## Rules (fail-closed)
1. **No `FAMILY_EXHAUSTED`/`CLEAN_KILL` (family-level)** unless the richest *applicable* tier has been tested, OR that tier is certified irrelevant/unavailable (with reason recorded).
2. **Close-only (T0) kills are expression-level only.** Never a family kill.
3. **Daily (T0/T1) kills are expression-level** if richer intraday/volume/term-structure data applies to the mechanism.
4. If richer *validated* data exists and is unused, the report **must record why** (`tier_gap_reason`).
5. **Adversarial review must challenge data-tier sufficiency** (`DATA_TIER_INSUFFICIENT`).
6. **Family map must show tested tiers and untested richer tiers** (`tested_tiers`, `richest_applicable_tier`, `tier_gap`).
7. **Every queued strategy item must declare its data tier.**

## Guardrail triggers (warn/fail)
- family exhaustion without tier proof;
- close-only/daily kill treated as a family kill;
- queued item missing data-tier declaration;
- active family using weak data while richer validated data exists and no justification;
- stale family labels predating the tier system (no `data_tier` field).

## Per-family verdict scoping
`CLEAN_KILL` at tier Tn means: *the Tn expression is dead.* The family reopens as `TIER_INCOMPLETE` if `richest_applicable_tier > tested_max_tier`. Only when `tested_max_tier >= richest_applicable_tier` (or richer certified irrelevant) may `FAMILY_EXHAUSTED` apply.
