# Forge Report — Rates RV pairs engine v1 (new family) — 2026-06-15

> **Mode:** Lane B / REPORT-ONLY full-search. New mechanism family built (2-leg pairs). No promotion/wiring/mutation.
> **Verdict:** Engine built + validated. **Base cointegration-z-band mechanism = NO EDGE** on ZN/ZF/ZB (daily, fair test). 5m pass was a cost/timeframe artifact (caught, not reported as a kill).
> **Artifacts:** `research/forge_cycle_2026-06-15h_rates_pairs_engine.py` + `.json`; daily re-test inline.

## What was built
A minimal 2-leg relative-value pairs engine (trailing OLS dollar-hedge ratio, residual z-band entry/exit, per-leg costs) — unblocks harvest #01–04. This is the first **multi-instrument** mechanism in Forge (engine was single-instrument). Report-only, no external data.

## 5m pass = timeframe/cost artifact (NOT a verdict)
At 5m (z-win 100 bars), all 3 pairs showed PF 0.15–0.26, WR 16–24% — the "near-perfect anti-prediction" smell. Cause: the RV thesis is **slow** (cointegration reversion over days/weeks; harvest notes say monthly), but 5m churns tiny intraday spread reversions that **can't cover ~$64/round-trip 2-leg costs**. I did **not** report this as a kill — I re-ran on the correct frequency.

## Daily fair test (the honest verdict)
| Pair | n | PF | median | WR | med hold | verdict |
|---|---|---|---|---|---|---|
| ZN/ZF | 55 | 0.96 | -$114.5 | 47.3% | 25d | KILL |
| ZN/ZB | 66 | 0.846 | +$72.75 | 54.5% | 22d | KILL |
| ZF/ZB | 55 | 0.648 | +$3.42 | 52.7% | 27d | KILL |

PF≈0.65–0.96 with WR≈50% = **no edge** (coin-flip after costs), and the sane WR confirms the daily test is methodologically sound (vs the 5m artifact). The engine works; the **base mechanism has no edge** on these rates pairs at default params. Sample is small (n=55–66 over ~7y at ~25d holds → limited power).

## Disposition
- **Rates RV base (OLS-hedge cointegration z-band): NO EDGE / KILL** on ZN/ZF/ZB (daily). Preserve as negative result; no-repeat at these params.
- **Deprioritized follow-ups** (harvest #01/#02 refinements — low prior given weak base + small n): Kalman-intercept hedge + veto, Hurst/cointegration pre-selection (only trade statistically mean-reverting regimes), ARIMA confirmation. Worth at most one refinement pass *if* re-prioritized; not chasing now.
- **Engine retained** — reusable for any future pairs work (e.g., once more rate/commodity contracts or a refinement is funded).

## Meta — the testable-now surface is thinning
Full-search has now covered: momentum cross-asset (exhausted), structural (exhausted), vol (exhausted), event/CPI (KILL), **rates RV pairs (no edge)**. The remaining high-diversification harvest ideas (commodity curve/inventory value, FX PPP, cross-asset value sleeves) are **feed-blocked**. So the *testable-now* frontier is narrowing toward either (a) RV refinements (low prior), (b) broader harvest triage for other testable-now families (continue), or (c) the **data-infra builds** (operator-supplied feeds) that unlock the rich feed-blocked VALUE/CARRY/EVENT supply.

## Boundaries
Report-only; no promotion/wiring/mutation; canonical feeds + active books untouched; Phase 1C frozen pending PHASE1C_24H_VERIFY (surfaced separately). No exhausted lane re-run.
