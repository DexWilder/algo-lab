# PAPER-READINESS PACKET — Diversified TSMOM (M86)  ·  2026-07-08

**Production outcome: CANDIDATE ADVANCED** (ForwardClock → PaperCandidate). First candidate to clear the full offline validation battery. **This is a paper-allocation decision request — not a deployment, not a validated primary. Capital gate remains closed.**

## What it is
Time-series momentum (Moskowitz-Ooi-Pedersen 2012) across 12 micro/standard futures (MES, MNQ, MYM, M2K, MGC, MCL, ZN, ZF, ZB, 6E, 6J, 6B). Blended trend signal = avg sign of trailing 21/63/126/252-day returns; each market inverse-vol sized; portfolio vol-targeted to ~10%/yr. Daily signal, low turnover.

## Evidence (the battery it passed)
| Test | Result | Bar |
|---|---|---|
| Sharpe (full) | 0.89 | — |
| Walk-forward H1 / H2 | 0.90 / 0.87 | both >0 ✅ |
| Equity beta (corr to MES) | **0.12** | near-0 = diversifier ✅ |
| Ex-2022 survival | Sh 0.60, DSR@N=1 0.93 | stays positive ✅ |
| Cost stress 1×→10× | 0.89→0.52 | survives ✅ |
| Config robustness (5 sets) | 0.70–0.97 | stable, not tuned ✅ |
| Orthogonality to spreadMR_GC | corr 0.02 | additive ✅ |
| Concentration | no market >40%; 2022=45% of PnL | ex-2022 survives ✅ |
| DSR | a-priori N=1: **0.99** (0.93 ex-2022) | published premium, N=1 defensible |

## Honest weaknesses (do not skip)
1. **2020 = −0.98 Sharpe** — trend-following's known failure mode (sharp V-reversals / COVID whipsaw). A paper allocation *will* have losing years; this is not a smooth sleeve.
2. **N-basis is a-priori.** At search-N=8 the DSR is 0.24. The 0.99 rests on TSMOM being a published, not data-mined, premium. A skeptic can reasonably discount it. Forward paper is the tiebreaker.
3. **No forward out-of-sample yet.** Everything above is in-sample-era backtest. The whole point of paper is to earn OOS confirmation.
4. **2022 dependence.** Real but not fatal (ex-2022 survives); still, a chunk of the edge is one strong trend year.

## Proposed paper configuration (if approved)
- **Instruments:** the 12 above, micro contracts, 1 lot base unit scaled by inverse-vol (cap 3× per market).
- **Rebalance:** daily signal, weekly position adjustment (limits turnover/cost).
- **Sizing:** portfolio vol-target 10%/yr; hard per-market cap 3×; total gross cap TBD by risk budget.
- **Execution realism:** costs modeled at 2× the base assumption (survives to 10×, so ample margin).
- **Monitoring:** track live-vs-backtest Sharpe drift, per-market contribution, and the 2020-style reversal signature.
- **Kill-switches:** flat-and-review if rolling-6mo Sharpe < −0.5 OR maxDD breaches 2× backtest maxDD OR beta-to-MES drifts > 0.4 (would mean it became closet beta).
- **All-lose scenario:** a choppy, mean-reverting, low-trend regime across all 12 markets (e.g., 2020-like) → expect a drawdown year; sized so that year is survivable within the paper risk budget.

## The decision (yours)
**Approve a paper allocation for TSMOM?**  Y → I wire it to the forward paper runner as a research sleeve (report-only, no capital) and it starts earning OOS evidence toward the 6-week test.  N → it stays PaperCandidate, unwired, and we spend the cycle instead on the option-settlement acquisition (the observability discriminator).  Either is a clean production outcome; drift (leaving it as "interesting") is the only wrong answer.

Wiring is operator-gated per standing doctrine — I will not wire it without an explicit Y.
