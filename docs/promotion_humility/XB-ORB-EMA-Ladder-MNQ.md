# Promotion Humility Packet — `XB-ORB-EMA-Ladder-MNQ`

*Probation since 2026-04-06. Anchor candidate of the workhorse trio.*
*All quoted PFs are net (cost-adjusted) per FQL evidence law.*

**Funnel result:** 10/13 paper-eligible (S1=4 / G4=3 / G5=1 / G6=2 / G7=0).
**Net PF (cost-aware, post-Piece-I):** 1.620 — Worst-half WF 1.445 — Stability 0.81 — Concentration top-3=9.2%, top-10=22.2%, max-year=21.1%.

## 1. Failure modes

- **MNQ index regime change.** Mechanical ORB + EMA-slope filter benefits from trending intraday character. A regime shift to choppy/range-bound MNQ (multi-month) would compress the strategy's edge across both legs.
- **Liquidity transition.** If MNQ liquidity profile changes materially (slip > 1 tick becomes routine), cost ratio rises from current 4.9% and the cushion shrinks.
- **Behavioral drift.** Per `XB_ORB_PROBATION_FRAMEWORK.md`: forward direction mix / time-of-day distribution drifting >20% from backtest signals execution-pattern issues.

## 2. Concentration caveat

Distribution is **clean**: top-3 = 9.2%, top-10 = 22.2% of total PnL. No single year > 21.1%. The strategy does NOT depend on outlier trades — broad participation across the 1207-trade sample. This is what concentration health looks like; treat as the bar for the rest of the pool.

## 3. Cost caveat

Cost basis: commission $0.62/side, slippage 1 tick (post-Piece-I consolidated). Cost is **4.9% of gross avg trade** — lowest of any candidate in the pool. Even a doubling of slippage (1t → 2t) would keep this above the 1.20 backtest gate. Robust to broker-rate uncertainty.

## 4. Forward-evidence caveat

**24 forward trades as of 2026-05-20** — below the Gate 7 threshold of 30. G7 = 0 today; needs **+6 more forward trades** to clear. Paper-eligible now; **promotion-eligible only after accumulation.** Per `XB_ORB_PROBATION_FRAMEWORK.md` review gate at 30 trades: full assessment of net PF / WR / concentration / drift triggers there.

## 5. Broker-rate caveat

MNQ commission and slippage are CME retail-broker typical estimates. **Replacement priority: medium** — MNQ is high-liquidity and the cost ratio is already small, so MNQ is the least sensitive of the probation pool to broker-rate uncertainty. Still: replace with actual broker rate sheet before live deployment.

## 6. Cluster / correlation caveat

**Distinct exposure cluster** — does not overlap with XB-ORB-EMA-Chandelier-MNQ or XB-ORB-EMA-TimeStop-MNQ (different exit family), nor with XB-PB-EMA-Ladder-MNQ (different entry family). No redundancy implication; this candidate occupies its own slot for top-3 selection.

## 7. What would invalidate the candidate

Per `XB_ORB_PROBATION_FRAMEWORK.md` thresholds (now explicit net PF per Piece H):

- **Forward net PF < 0.90 after 30+ trades** → downgrade to WATCH
- **Forward net PF < 0.80 after 50+ trades** → ARCHIVE
- **Forward WR < 40%** (vs backtest 56–61%)
- **3+ consecutive behavioral flags**
- **Max forward drawdown > 2× backtest max DD**
- **Zero trades for 20+ trading days** (signal generation broken)
- **Cost-ratio drift > 10%** (slippage assumption proven materially wrong)
