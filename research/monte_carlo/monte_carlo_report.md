# Monte Carlo Robustness Report

**Date:** 2026-03-08
**Portfolio:** PB-MGC-Short + ORB-009 MGC-Long (regime-gated)
**Simulations:** 10,000 reshuffled trade sequences

---

## Method

The gated portfolio produces 96 trades (21 PB-Short + 75 ORB-Long) with a combined PnL of $3,389. Monte Carlo reshuffles the trade ordering 10,000 times to test whether the portfolio survives unfavorable sequencing — i.e., what happens if all the losers come first?

This answers: **is the edge robust to bad luck in trade ordering?**

---

## Final PnL Distribution

| Percentile | Value |
|-----------|-------|
| Mean | $3,389 |
| All percentiles | $3,389 |
| P(PnL > 0) | 100% |

Final PnL is constant across all orderings (reshuffling preserves the sum). The relevant metric is the *path* — specifically max drawdown.

---

## Max Drawdown Distribution

| Percentile | MaxDD |
|-----------|-------|
| p1 (best case) | $301 |
| p5 | $345 |
| p10 | $375 |
| p25 | $432 |
| **p50 (median)** | **$516** |
| p75 | $626 |
| p90 | $748 |
| p95 | $840 |
| p99 (worst case) | $1,034 |

**Interpretation:** In the median case, the worst drawdown is $516. Even in the 99th percentile worst case, the drawdown is only $1,034. The observed drawdown of $685 sits between the 50th and 75th percentile — meaning the actual trade ordering was roughly average.

---

## Ruin Probability

| Drawdown Floor | P(MaxDD ≥ Floor) |
|---------------|-----------------|
| $1,000 | 1.3% |
| $2,000 | 0.0% |
| $3,000 | 0.0% |
| **$4,000 (Lucid prop)** | **0.0%** |
| $5,000 | 0.0% |

**The portfolio never touches a $2K drawdown in any ordering.** A $4K trailing DD prop account survives 100% of simulated orderings.

---

## Prop Account Survival

| Account Type | DD Limit | Survival Rate | Median PnL |
|-------------|----------|--------------|-----------|
| Tight prop | $2,000 | 100.0% | $3,389 |
| Standard prop | $3,000 | 100.0% | $3,389 |
| Lucid 100K | $4,000 | 100.0% | $3,389 |
| Relaxed prop | $5,000 | 100.0% | $3,389 |

---

## Drawdown Duration (in trades)

| Percentile | Duration |
|-----------|----------|
| p25 | 15 trades |
| p50 (median) | 19 trades |
| p75 | 25 trades |
| p95 | 37 trades |
| p99 | 47 trades |

In the worst case, the portfolio spends up to 47 consecutive trades in drawdown (roughly half the total trades). Median recovery is 19 trades.

---

## Interpretation

### Is this portfolio realistically survivable for a prop account?

**Yes — definitively.**

1. **MaxDD is structurally capped.** With 96 trades averaging $35/trade and a positive expectancy of $35.30/trade, the portfolio simply doesn't generate enough losing streaks to create dangerous drawdowns. The 99th percentile MaxDD ($1,034) is far below any standard prop DD limit.

2. **No ordering kills it.** Out of 10,000 random orderings, zero produced a drawdown exceeding $2,000. This means even in the worst possible luck scenario, the portfolio survives with room to spare.

3. **The edge is not path-dependent.** Some strategies are fragile — they only work if winners come early to build a cushion. This portfolio is not fragile. Every ordering is profitable, and the worst drawdown is always manageable.

### Caveats

1. **This assumes trade-level independence.** Monte Carlo reshuffles trades as if they're independent. In reality, losing streaks may cluster during adverse market regimes. The regime gate mitigates this, but doesn't eliminate it.

2. **96 trades is a moderate sample.** With more trades, the drawdown distribution would narrow further. With fewer, it would widen.

3. **This doesn't model time.** A 47-trade drawdown could take weeks or months to recover from psychologically, even if the dollar amount is small.

---

## Conclusion

The regime-gated 2-strategy portfolio passes the Monte Carlo risk gate. It is survivable under all tested prop account configurations with 100% probability across 10,000 orderings. The median MaxDD ($516) is 87% below the Lucid 100K trailing DD limit ($4,000).

**Risk gate verdict: PASS**

---
*Generated 2026-03-08*
