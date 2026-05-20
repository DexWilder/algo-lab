# Cost Integrity Impact Report — 2026-05-20

**Filed:** 2026-05-20
**Authority:** T2 (decision-grade evidence correction; no auto-status mutation)
**Sprint:** Phase 2 / Paper-Readiness Sprint, Item #3 Piece G — the canonical aggregation of Pieces C + D.
**Status:** Strategy evidence integrity quantified. **No registry/probation/paper decisions taken** — see "Required operator decisions" section.
**Cost source of truth:** `engine/asset_config.py` (post-Item-#3 Piece I consolidation).

---

## Executive summary

**The damage is less severe than the worst-case scare, but real on MCL non-ORB variants.**

- **Probation pool (3 candidates):** ALL GREEN. MNQ unchanged. MCL/MYM survived the conservative slippage increase. **No verdict changes.** Probation evidence is intact.
- **Correlation set (12 candidates):** 9 GREEN / 1 YELLOW / 2 RED. **3 verdict changes — all on MCL non-ORB variants** that were previously evaluated at silent zero cost via `correlation_matrix.py`. Their published PFs were **gross**, not net; under cost-aware screening they fail the 1.20 backtest gate.
- **Cost assumption caveat:** all values are **conservative estimates**, not broker rate sheets. MCL especially is fragile to assumption error — broker rate sheet should replace estimates before any MCL candidate enters paper.

**Bottom line:** the 3 probation candidates remain viable. The correlation work concluded "12 distinct candidates available for top-3 selection" — that conclusion needs revision because **3 of the 12 are not gate-passing under cost-aware screening.** The clean candidate set for Item #8 top-3 selection is now **9, not 12.**

---

## Methodology

For each strategy, run the identical backtest three times:

1. **GROSS** — `commission_per_side=0, slippage_ticks=0` (the silent-default state for callers that didn't pass cost overrides: `fql_forge_batch_runner.py`, `correlation_matrix.py`, `run_forward_paper.py`)
2. **PRIOR** — pre-Piece-I `asset_config` values (`slip=1` universally) — what `xb_orb_sweep.py` was actually using via explicit overrides
3. **NEW** — post-Piece-I consolidated `asset_config` values (conservative bias: `slip=2` for less-liquid assets including MCL/MYM)

Reports two deltas:
- **Δ-A = PRIOR → NEW** — the actual shift in probation baselines (since xb_orb_sweep already used PRIOR)
- **Δ-B = GROSS → NEW** — what callers using the silent zero-cost path were missing

Concern levels evaluated on NEW net PF against the backtest workhorse gate (1.20 per `ELITE_PROMOTION_STANDARDS.md`):
- 🟢 **GREEN:** net PF ≥ 1.20
- 🟡 **YELLOW:** net PF in [1.05, 1.20)
- 🔴 **RED:** net PF < 1.05

Source data: `docs/reports/cost_integrity_reset/2026-05-20_cost_integrity_reread_probation.{md,json}` and `2026-05-20_cost_integrity_reread_correlation.{md,json}`.

---

## Probation pool (3 candidates)

| Strategy | Asset | Gross PF | Prior net PF | New net PF | Δ-A | Δ-B | Cost % gross avg | Cost assumption | Concern |
|---|---|---|---|---|---|---|---|---|---|
| XB-ORB-EMA-Ladder-MNQ | MNQ | 1.661 | 1.620 | **1.620** | 0.000 | -0.041 | 4.9% | comm=$0.62, slip=1t | 🟢 GREEN |
| XB-ORB-EMA-Ladder-MCL | MCL | 1.489 | 1.368 | **1.298** | -0.070 | -0.191 | **34.7%** | comm=$0.62, slip=2t | 🟢 GREEN |
| XB-ORB-EMA-Ladder-MYM | MYM | 1.753 | 1.663 | **1.625** | -0.038 | -0.128 | 13.4% | comm=$0.62, slip=2t | 🟢 GREEN |

**MNQ:** Cost basis unchanged (slip=1 in both PRIOR and NEW). 1.620 holds. Backtest PF 1.62 cited in CLAUDE.md is confirmed as the NEW net PF — **the canonical number was right all along.**

**MCL:** Slip 1→2 drops PF by 0.07. Cost is **34.7% of gross average trade** — the highest of any probation candidate. New net PF 1.298 is only 0.10 above the 1.20 gate. **MCL is the most fragile probation candidate.** If the actual broker rate sheet has worse slippage than 2 ticks, MCL drops to YELLOW.

**MYM:** Slip 1→2 drops PF by 0.04. Cost is 13.4% of gross average trade. Comfortable margin above the gate. Lowest-volume probation candidate (340 trades) but cost impact is modest.

---

## Correlation set (12 candidates)

| Strategy | Asset | Gross PF | New net PF | Δ-B | Cost % | Verdict Δ-B | Concern |
|---|---|---|---|---|---|---|---|
| XB-PB-EMA-Ladder-MNQ | MNQ | 1.461 | **1.406** | -0.055 | 10.0% | no | 🟢 GREEN |
| XB-PB-EMA-Ladder-MCL | MCL | 1.297 | **1.058** | -0.239 | **78.3%** | **yes** | 🟡 YELLOW |
| XB-PB-EMA-Ladder-MYM | MYM | 1.346 | **1.202** | -0.144 | 37.9% | no | 🟢 GREEN |
| XB-BB-EMA-Ladder-MNQ | MNQ | 1.283 | **1.237** | -0.046 | 14.6% | no | 🟢 GREEN |
| XB-BB-EMA-Ladder-MGC | MGC | 1.749 | **1.592** | -0.157 | 16.5% | no | 🟢 GREEN |
| XB-BB-EMA-Ladder-MCL | MCL | 1.203 | **0.983** | -0.220 | **109.2%** | **yes** | 🔴 RED |
| XB-BB-EMA-Ladder-MYM | MYM | 1.745 | **1.551** | -0.194 | 20.4% | no | 🟢 GREEN |
| XB-VWAP-EMA-Ladder-MGC | MGC | 1.416 | **1.297** | -0.119 | 24.9% | no | 🟢 GREEN |
| XB-VWAP-EMA-Ladder-MCL | MCL | 1.276 | **1.040** | -0.236 | **83.7%** | **yes** | 🔴 RED |
| XB-VWAP-EMA-Ladder-MYM | MYM | 1.482 | **1.325** | -0.157 | 28.3% | no | 🟢 GREEN |
| XB-ORB-EMA-Chandelier-MNQ | MNQ | 1.637 | **1.574** | -0.063 | 7.6% | no | 🟢 GREEN |
| XB-ORB-EMA-TimeStop-MNQ | MNQ | 1.570 | **1.507** | -0.063 | 8.8% | no | 🟢 GREEN |

**Pattern:** Every MCL non-ORB candidate falls. Every MNQ candidate survives easily. MGC and MYM survive but with material PF degradation. The cost-to-gross-edge ratio for MCL non-ORB candidates is **78–109%** — cost is eating most or all of the gross edge.

---

## Conclusions (per operator-required structure)

### Unaffected candidates

These resolve as expected — Δ-A is zero (no slippage change) and Δ-B is small relative to gross PF:

- **All MNQ candidates** (5 total across probation + correlation): MNQ slippage was already 1 tick in both prior and new. Cost is 5–15% of gross avg trade. Δ-B is the only meaningful delta and it's modest. **No revision required.**
- **MGC candidates** (2): MGC slippage unchanged at 1 tick. Cost 17–25% of gross avg. **No revision required.**

### Weakened but still viable

Material PF degradation, but stays above the 1.20 backtest gate:

- **XB-ORB-EMA-Ladder-MCL** (probation): 1.298 net PF, **slim 0.10 margin above gate**, 34.7% cost ratio. **Decision packet required if operator considers paper deployment** — this is the highest-priority asset to replace conservative estimates with actual broker rate sheet before any paper decision.
- **XB-ORB-EMA-Ladder-MYM** (probation): 1.625 net PF, comfortable margin. Lowest-sample probation (340 trades) but cost impact is modest.
- **XB-PB-EMA-Ladder-MYM** (correlation): 1.202 net PF — right at the 1.20 gate. Borderline.
- **XB-BB-EMA-Ladder-MGC, XB-BB-EMA-Ladder-MYM, XB-VWAP-EMA-Ladder-MGC, XB-VWAP-EMA-Ladder-MYM** (correlation): all hold above 1.25 net PF.

### Marginal after costs (decision packet required)

Net PF in [1.05, 1.20) — was previously claimed PASS, now ineligible for top-3 selection:

- **XB-PB-EMA-Ladder-MCL** (correlation): net PF **1.058**, cost = 78.3% of gross avg trade. Was reported as PASS in correlation_matrix.py but PF was gross. **Not eligible for paper-readiness top-3.**

### Failed after costs (decision packet required)

Net PF < 1.05 — strategy is not profitable net of cost:

- **XB-BB-EMA-Ladder-MCL** (correlation): net PF **0.983**, cost = 109.2% of gross avg trade. **Cost exceeds gross edge per trade.** Strategy was never profitable under cost-aware screening. The correlation_matrix.py PASS verdict was a false positive.
- **XB-VWAP-EMA-Ladder-MCL** (correlation): net PF **1.040**, cost = 83.7% of gross avg trade. Same class of false-positive PASS.

### Previous conclusions requiring revision

1. **"All 12 correlation candidates are distinct & gate-passing" — REVISE.** The correlation-distinctness conclusion still holds (correlation is about return co-movement, not PF level). But the *gate-passing* implication is wrong: **3 of 12 fail cost-aware screening.** Item #8 top-3 selection should pick from the **9 gate-passing candidates**, not the raw 12.

2. **"MCL non-ORB candidates as portfolio diversifiers" — REVISE.** XB-PB-MCL, XB-BB-MCL, XB-VWAP-MCL were treated as potential diversifying additions on the energy axis. **They are not viable** — only XB-ORB-EMA-Ladder-MCL (probation) remains a viable MCL strategy. MCL energy diversification rests on the probation candidate alone.

3. **"ORB-EMA-Ladder is the load-bearing XB family" — REINFORCED.** The 3 probation candidates (all ORB-EMA-Ladder) hold net of cost. The ORB-EMA exits Chandelier and TimeStop on MNQ also hold (1.574, 1.507). PB / BB / VWAP variants degrade more, especially on MCL. The XB-ORB-EMA family is more cost-robust than the alternatives — consistent with `project_proven_trio_architecture.md` memory.

4. **CLAUDE.md baseline PFs (MNQ 1.62 / MCL 1.33 / MYM 1.67) — RECONFIRMED, not revised.** These came from `xb_orb_sweep.py` which used explicit cost overrides via `get_asset()` — so they were already net under PRIOR asset_config (slip=1). My earlier pre-flight framing that "MCL/MYM probation baselines were silently zero-cost" was wrong. The values were always prior-net. **Update needed:** CLAUDE.md should note these are PRIOR-net (slip=1); the new conservative net values are MNQ 1.62 / MCL 1.30 / MYM 1.63.

5. **The pool-expansion packet (top-3 recommendation: VWAPPullback-MES-Long / BBW-Percentile / FX-Daily-Donchian) — UNAFFECTED.** None of those three are in the correlation set or probation pool, so their cost basis isn't yet quantified. They will run on the post-Piece-I consolidated cost basis when added to the runner — that's the correct sequence.

### Requires actual broker/firm rates before paper/prop

All cost values in this report are **conservative estimates**, not broker rate sheets. Replace before paper/prop:

- **MCL** — highest priority. Probation candidate sits 0.10 above gate; non-ORB MCL candidates already fail. Sensitivity to broker-rate truth is highest here.
- **MYM** — secondary priority. Lowest-sample probation candidate. Cost impact is modest but unknowns are larger.
- **ZN/ZF/ZB** — anticipated for future treasury candidates (none in current set, but future Forge candidates on rates need real rates first).
- **FX trio (6B/6E/6J)** — same; future readiness concern.

---

## Required operator decisions

The operator-locked guardrail forbids auto-status mutation. The findings below require explicit decisions:

1. **XB-BB-EMA-Ladder-MCL (RED):** registry status currently `idea` per the correlation matrix work. Recommend **archive** as cost-aware non-viable. Decision packet pending.
2. **XB-VWAP-EMA-Ladder-MCL (RED):** same — recommend archive.
3. **XB-PB-EMA-Ladder-MCL (YELLOW):** recommend tag as cost-fragile, **defer** from top-3 consideration; keep registered for potential broker-rate revision later.
4. **XB-ORB-EMA-Ladder-MCL (probation, GREEN at 1.298):** **flag as fragile-to-broker-rate before any paper deployment**; no probation status change today.
5. **CLAUDE.md baseline PF block:** update to note baselines are PRIOR-net (slip=1) and reference the post-consolidation net values.
6. **Top-3 selection (Item #8):** select from the **9 gate-passing correlation candidates** plus the 3 probation candidates, not the raw 12.

No registry mutation taken in this report. All decisions queued for operator review.

---

## What's NOT in this report

- ❌ Forge daily report re-read on the 11 previously unconfigured assets (was silent zero-cost via `fql_forge_batch_runner.py`). Deferred to Item #3.5 or Piece F-tail.
- ❌ Forward paper P&L re-read (was silent zero-cost via `run_forward_paper.py`). Deferred to Item #3.5.
- ❌ Walk-forward / OOS validation of any candidate. That is Item #7 validation funnel work.
- ❌ Cushion-to-breakeven ticks (Piece B verdict layer). Deferrable per pre-flight; the concern levels in this report use net PF only.

---

## Status after this report

- ✅ Engine fails closed on missing cost
- ✅ All 17 trading-universe assets cost-configured (conservative estimates)
- ✅ Single source of truth: `engine/asset_config.py`
- ✅ Probation/promotion docs require explicit net PF
- ✅ Probation evidence verified intact under cost-aware screening
- ✅ Correlation set evidence corrected — 9 viable, not 12
- 🔁 Forge daily / forward paper re-read deferred to Item #3.5
- 🔁 Broker rate sheet replacement queued before paper/prop

**Status:** Plumbing repaired, strategy evidence quantified. **Paper-readiness ranking is now defensible** for the 9 viable correlation candidates + 3 probation candidates, conditional on operator decisions for the YELLOW/RED items above.

---

*Filed 2026-05-20. Item #3 cost integrity reset Piece G — canonical impact report. No status mutation. Decision packets queued.*
