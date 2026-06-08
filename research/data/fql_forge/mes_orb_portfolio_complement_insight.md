# Portfolio-Complement Insight — XB-ORB-EMA-Ladder-MES

> **Status:** OBSERVATIONAL pending operator decision.
> **Recorded:** 2026-06-08 per operator decision #86 (directional asymmetry expansion).
> **NOT a paper-packet candidate.** Moderate correlation to existing MNQ probation strategy.

## Finding

XB-ORB-EMA-Ladder applied to MES (Micro E-mini S&P 500) survives prop-stress on both directional splits, but its daily-PnL correlation to the existing XB-ORB-EMA-Ladder-MNQ probation workhorse is moderate, **not low enough to claim genuinely independent edge.**

### Backtest performance

| Configuration | n | PF | Median | Net | Prop-stress |
|---|---:|---:|---:|---:|---|
| DIR-MES-ORB-Long-PL | 854 | 1.394 | $12.51 | $10,394 | **PASS_STRESS** |
| DIR-MES-ORB-Short-PL | 393 | 1.482 | $28.76 | $11,500 | **PASS_STRESS** |
| (Reference: MNQ-both probation) | 1216 | 1.608 | $42.76 | $49,495 | (already live) |

### Family overlap vs MNQ-both probation

| Test | MES-Long vs MNQ-both | MES-Short vs MNQ-both |
|---|---:|---:|
| Trade-day overlap (% of MES days that overlap with MNQ days) | 85% | 89% |
| Daily-PnL Pearson correlation | **0.42** | **0.62** |
| Both-traded days | 723 | 348 |
| **Classification** | **PORTFOLIO_COMPLEMENT (low-mod corr)** | **PORTFOLIO_COMPLEMENT (mod corr)** |

## Interpretation

- MES is a Micro E-mini S&P 500 contract. MNQ is a Micro E-mini Nasdaq-100 contract. Both are equity-index micros. **Sector correlation alone explains most of the 0.42-0.62 daily-PnL correlation.**
- High day-overlap (85-89%) means MES rarely trades on days that MNQ does not. This is consistent with equity-index cross-asset behavior.
- The ORB+EMA-slope+profit-ladder edge transfers to MES — confirming the family's cross-asset robustness — but does **not** add independent diversification on the scale required for a separate paper-packet candidate.

## Disposition

- **DIR-MES-ORB-Long-PL → OBSERVATIONAL** as PORTFOLIO_COMPLEMENT_CANDIDATE. Bounded diversification value.
- **DIR-MES-ORB-Short-PL → OBSERVATIONAL** as PORTFOLIO_COMPLEMENT_CANDIDATE. Moderate correlation reduces diversification claim.
- **Per doctrine:** "Same-family subset = insight, not packet." MES is the cross-asset cousin of the existing MNQ probation, not a new family. Family overlap is material.
- **No paper-packet promotion.** Both MES candidates retain operator-decision optionality as future sleeves but not as standalone paper packets.

## Future operator decisions (require separate approval)

1. **Add MES to existing XB-ORB-EMA-Ladder family** as an additional asset slot in the probation framework (similar to MYM expansion 2026-04-13). Would require fresh forward-trade observations.
2. **Add MES as separate paper-packet sleeve** only if independent diversification clarification emerges (e.g., regime-specific or session-specific behavior that differentiates from MNQ).
3. **No deployment.** MES remains research-only; existing MNQ/MCL/MYM probation handles equity-index/energy exposure.

## Constraints

- **No registry mutation.** No probation strategy change.
- **No portfolio allocation change.**
- **No paper/live promotion.**
- Research-only Lane B finding.

## Source artifacts

- `research/forge_cycle_2026-06-08a.py` (directional batch with prop-stress)
- `research/forge_cycle_2026-06-08a_family_review.py` (family overlap analysis)
- `research/data/fql_forge/reports/forge_cycle_2026-06-08a_family_review.json`
- `research/data/fql_forge/reports/forge_cycle_2026-06-08a.json`
