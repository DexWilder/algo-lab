# pre-OPEX long seasonal — robustness/prop verdict — 2026-06-15

> **Mode:** Lane B / REPORT-ONLY. No promotion/wiring/mutation. LONG-only (OPEX-week short leg KILLed).
> **Verdict: WATCH / `SEASONAL_BETA_TIMING`** — real, robust, beta-controlled seasonal alpha, but beta-laden (not a diversifier) AND fails prop $2K guardrail. **NOT packet-grade, NOT deployable as-is.**
> Artifacts: `research/forge_cycle_2026-06-15j_opex_robustness.py` + `.json`.

## Gate results (MES / MNQ primary)
| Gate | MES | MNQ | Pass? |
|---|---|---|---|
| Window-family (7 variants) | PF 1.76–2.11 | PF 2.16–2.67 | ✅ family, not overfit |
| Base 11→3 PF / WR | 2.09 / 67.5% | 2.52 / 66.3% | ✅ |
| Beta-control (vs generic 8-td) | 2.09 vs 1.42 | 2.52 vs 1.48 | ✅ alpha>beta |
| LOO PF range | 1.79–2.67 | 2.13–3.43 | ✅ all >1 |
| H1 / H2 PF | 1.39 / 2.91 | 1.52 / 3.66 | ✅ |
| Max-year concentration | 30.2% | 27.5% | ✅ <50% |
| Cost-stress PF 1x/2x/5x | 2.09/2.06/1.96 | 2.52/2.50/2.46 | ✅ insensitive |
| **2022 bear market** | **−$1,171 (PF 0.70)** | **−$2,697 (PF 0.60)** | ❌ **beta-laden** |
| **Prop $2K (1 micro, worst MTM DD)** | **−$2,340 BREACH** | **−$2,855 BREACH** | ❌ **fails** |

(MYM fits $2K at 1 micro (−$989) but fails concentration 52.7%; M2K breaches −$2,025. No single instrument clears all gates.)

## Interpretation
- **Real seasonal alpha above beta** (1.5–1.7× generic PF, robust across variants/years/halves, cost-insensitive). The effect is genuine and well-documented (replication confidence).
- **But it is a seasonally-timed equity LONG** — it loses in down years (2022) → `SEASONAL_BETA_TIMING`, not market-neutral, **not the non-MNQ diversifier** the campaign wants (still equity-index exposure).
- **Prop-blocked**: multi-day holds accumulate >$2K MTM drawdown at MES/MNQ 1-micro → fails Tradeify-style guardrail by construction.

## Disposition
- **WATCH / SEASONAL_BETA_TIMING.** Exact blockers: (1) beta-laden (fails 2022, not a diversifier); (2) prop $2K DD breach at MES/MNQ. Keep as review-only research lead; do NOT promote/wire.
- **Strategic value (per operator framing):** this validates a **new productive search family — seasonal/calendar effects** — outside the exhausted intraday primitive library. Future seasonal mining (turn-of-month, day-of-week, holiday, roll-window) may find lower-beta / smaller-DD seasonals; and a beta-hedged version of pre-OPEX could become a true diversifier (future work, not now).

## Next (rotating per standing rule)
Pre-OPEX is WATCH, not deployable → the non-equity diversification search continues. Next queued genuinely-new testable surface: **FX London-open session breakout** (6E/6J/6B — actual new asset class), then overnight gap-bucket.

Boundaries: report-only; no promotion/wiring/mutation; canonical feeds + active books untouched; Phase 1C frozen pending PHASE1C_24H_VERIFY (separate).
