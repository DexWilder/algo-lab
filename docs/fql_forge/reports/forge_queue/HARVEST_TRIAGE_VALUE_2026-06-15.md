# Harvest Triage — VALUE batch (full-search mode) — 2026-06-15

> **Mode:** Lane B / REPORT-ONLY full-search. Triaged the newest 12 VALUE-themed harvest items (of 850 pending). No promotion/wiring/mutation.
> **Headline:** Most VALUE ideas are feed-blocked (PPP/OECD/CPI-level/inventory/curve), BUT a **non-equity relative-value PAIRS/SPREADS cluster is testable NOW** on existing ZN/ZF/ZB data — a genuinely new, non-MNQ, non-momentum family. **This is the next real report-only build target.**

## Data I actually have (testability anchor)
Present: MES/MNQ/M2K/MYM/MGC/MCL, **ZN/ZF/ZB**, 6E/6J/6B (5m OHLCV, single continuous contract each).
**Absent:** SI, HG, RB, HO, ZC, ZS, ZT, 6A/6C/6S; any fundamental/PPP/OECD/CPI-level/inventory/term-structure (multi-contract curve) data.

## Ranked top 10 (testable-now first)

| # | Idea | What it needs | Testable now? | Diversification | Blocker |
|---|---|---|---|---|---|
| 1 | **Treasury cointegration pairs** (ZN/ZF) [h #03] | 2-leg pairs engine + cointegration residual/z-band entry | ✅ **YES** (have ZN/ZF) | **High** (rates RV, orthogonal to MNQ) | needs **new pairs primitive** (no external data) |
| 2 | **Kalman-filter pairs** (ZN/ZF) [h #01] | online Kalman hedge-ratio+intercept, residual z-band | ✅ YES | High | new pairs primitive |
| 3 | **Hurst-ranked spread + ARIMA confirm** (ZN/ZB) [h #02] | spread + multi-interval Hurst screen, ARIMA gate | ✅ YES (have ZN/ZB) | High | new pairs primitive (+ARIMA) |
| 4 | **Margin-capped pairs sizing** (ZN/ZF) [h #04] | pairs engine + family margin cap | ✅ YES (sizing layer on #1) | Medium | new pairs primitive |
| 5 | **Half-life-gated reversion** (MGC/MCL/ZN) [h #05] | BB breach→re-entry, exit at mid or half-life expiry | ✅ YES | Medium (reversion — caution: plain reversion already KILL) | new **half-life-gate primitive** |
| 6 | Cross-asset GTAA value+dual-mom rank [h #08] | adjusted-yield **value score** + monthly cross-asset rank | ⚠️ partial (momentum leg only) | High | **value/yield feed** for the value leg |
| 7 | Commodity curve-extremes + inventory [h #11] | roll-return/basis (**curve**) + **inventory** state | ❌ NO | High | **term-structure + inventory feeds** |
| 8 | FX value: PPP + macro residual agreement [h #07] | PPP gap + macro-driver decomposition | ❌ NO | High | **PPP/macro feed** |
| 9 | FX PPP basket (OECD + CPI) [h #06] | OECD fair value + monthly CPI levels | ❌ NO | High | **OECD/CPI-level feed** |
| 10 | Cross-asset value sleeve (AQR) [h #12] | asset-class value signals + overlay | ❌ NO | High | **value-signal feeds** + needs a value book |
| — | Value-tilt 40/60 & TE-budget overlays [h #09,#10] | an existing value book to overlay | ❌ NO | (construction) | needs value book first |

## The actionable finding
Ideas **1–4 collapse to one build**: a **minimal 2-leg relative-value spread/pairs engine** for rates (ZN/ZF, ZN/ZB, ZF/ZB) supporting hedge-ratio estimation (static OLS + online Kalman) and residual z-score-band entry/exit. That single primitive unblocks four harvest ideas at once, is **testable today with no external data**, is a **new mechanism family** (not a repeat of any exhausted lane), is **non-momentum/non-MNQ**, and aligns with the existing **Treasury-Rolldown carry** precedent. Idea 5 (half-life-gated reversion) is a separate smaller primitive — lower priority given plain reversion already KILLed.

The feed-blocked ideas (6–10) reinforce **WP-1/WP-2/WP-4** in the data-infra backlog (they're the demand side: VALUE supply is rich, data is the gate).

## Recommended next report-only action
**Build a minimal rates relative-value pairs/spread engine** (report-only, no external data, no execution mutation) and screen ZN/ZF, ZN/ZB, ZF/ZB with cointegration/z-band entries. This is the highest-value *testable-now, genuinely-new* path the triage surfaced. New-primitive build with a filter-pre-flight sanity check, MNQ-style control where applicable, and the clean-events/concentration discipline applied to results.

## Boundaries
Report-only; no promotion/wiring; no scheduler/registry/portfolio/live-prop mutation; canonical feeds + active books untouched; Phase 1C frozen pending PHASE1C_24H_VERIFY (surfaced separately). Negative results + no-repeat rules preserved. Did NOT re-run any exhausted lane.
