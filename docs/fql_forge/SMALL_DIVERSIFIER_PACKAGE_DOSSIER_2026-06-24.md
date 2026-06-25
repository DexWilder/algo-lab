# Deployment-Decision Dossier — Small Diversifier Package (DRAFT, report-only)

> **STATUS: research evidence is strong enough to BUILD this dossier — it is NOT "deployment-ready" / "turn it on."** This is a decision-support artifact. Building it is report-only research. NO promotion, wiring, scheduler, registry, sizing, paper, or live/prop mutation. Any deployment is a separate, explicitly operator-gated capital decision. Per [[feedback_validated_candidate_vs_deployment_dossier]].

## 1. Objective & portfolio role
Add small, decorrelated, **regime-complementary stabilizer sleeves** alongside the deployed ORB primary engine — to modestly improve combined risk-adjusted return (Sharpe/MAR) and rescue ORB's weak *grind* years, WITHOUT damaging prop-firm daily-loss constraints. **These are NOT new workhorses and NOT replacements for ORB.** Satellite stabilizers, sized small.

## 2. Instruments & exact construction
- **Primary (incumbent, unchanged):** ORB = `orb_breakout | ema_slope | profit_ladder`, MNQ, params stop_mult 0.5 / target 4.0 / trail 2.5. 1 contract baseline.
- **Sleeve A — TSMOM:** time-series momentum, 126-day (6mo) trailing-return SIGN, held, daily, pooled equal-contract across MNQ/MES/MGC/MCL. No flip. (MCL leg is the weakest — see open items.)
- **Sleeve B — Vol-carry:** contango-only short-vol. Signal = VIX3M/VIX slope > 0 (prior close, no lookahead) → long short-vol. **Expression caveat:** tested via SVXY ETP (ETP decay/leverage-reset artifacts) — a true VIX-futures-curve vehicle is the class-C upgrade; do NOT deploy the raw ETP without the execution-realism section below.

## 3. Trade schedule / cadence
- ORB: intraday (existing). TSMOM: daily close evaluation, position held overnight, flips infrequent (~6mo signal). Vol-carry: daily close evaluation of slope, position held while contango. All signals computed at/after prior close, acted next session — no lookahead (verified).

## 4. Sizing — now PRINCIPLED (2026-06-25 CV1/CV2): vol-target, not hand-tuned
The hand-tuned 0.05×TSMOM / $2k vol-carry is REPRODUCED by principled risk-budgeting: **vol-target each decorrelated diversifier to ~10-15% of ORB's daily $-risk**. Weights derived on H1 ONLY, evaluated OOS on H2 → vol-target k=0.15 (wt 0.047/$1400) H2 Sharpe 3.59 vs hand-tuned 3.61 (within noise); k=0.10 (wt 0.031/$933) marginally better risk (maxDD −2283, MAR 15.51). 0 DLL all variants. NOT overfit (H1-derived, H2-confirmed, no optimizer). Package upgraded from hand-tuned discovery → principled construction. Recommend vol-target k≈0.10-0.15 as the canonical sizing rule.

## 4b. (prior hand-tuned reference)
- TSMOM ≈ **0.05–0.10×** the pooled-1-contract notional (MAR-optimal ~0.025–0.05×, Sharpe-optimal ~0.10×).
- Vol-carry ≈ **$1–3k** notional.
- **Hard finding: oversizing destroys it** — TSMOM ≥0.25× and vol-carry ≥$5k introduce DLL breaches and Sharpe degradation. Sizing discipline is load-bearing.

## 5. Execution & financing / ETP realism
- ORB/TSMOM: micro/standard futures — no borrow; overnight = margin only (negligible financing); flip costs (commission + slippage) ARE included in the backtests.
- Vol-carry via SVXY: long-only (no borrow needed), ETP expense + roll-decay are embedded in the ETP's own return series (already captured). **OPEN:** confirm bid/ask + capacity at small size; evaluate true VIX-futures-curve vehicle vs ETP. [pending]
- TSMOM overnight gap risk across 4 markets: covered in drawdown expectations.

## 6. Validation evidence (CONFIRMED, report-only)
- Combined book (ORB + 0.05×TSMOM + $2k VX): **Sharpe 2.84→3.02, MAR 22.07→23.27, 0 DLL breaches.**
- **Robust:** TSMOM improves 6/8 years; **both walk-forward halves improve** (H1 2.21→2.33, H2 3.38→3.61); PSR significant.
- **Additive / regime-complementary:** corr(TSMOM,VX)=0.19; 2022 split TSMOM +$936 vs VX −$1249 (opposite regimes). Combining beats either alone.
- Correlation measured vs ACTUAL ORB strategy PnL (−0.05/−0.16), not buy-and-hold proxy.

## 7. Drawdown expectations
- Combined maxDD ~−$2,344 (vs ORB-alone −$2,331) at the small allocation — essentially unchanged. Worst-day ~−$919 (vs −$850). [Per-year worst day/week/month to be tabulated in final dossier.]

## 8. "What if ORB AND both sleeves lose together" scenario
- **2020 COVID is the empirical answer: all three struggled** (ORB weak intraday chop, TSMOM −$616 whipsawed by the V-reversal, VX −$62). **This package is NOT a sharp-V-crash hedge.** It rescues weak *grind* years (2019, 2021), not a violent reversal. Position-sizing must assume a simultaneous-loss day is possible; the small allocation keeps it within DLL, but this is the known failure mode.

## 9. V-crash behavior + guard → GUARD_HELPS (mild, general, not overfit)
General VIX>35 flatten on TSMOM (active 3.5% of days, NOT COVID-tuned): 2020 package Sharpe 1.39→1.53, full package 3.02→3.04, TSMOM-only 2.97→2.99. **Other years unchanged or slightly better** (2025 2.76→2.80; 2022 3.19→3.17 negligible) → helps the crash window WITHOUT damaging normal-year contribution and is a broad threshold (not overfit to COVID). **Recommended for the package.** Still NOT a full V-crash hedge (improvement is mild) — the small-sizing + caveat in §8 remain the primary protection.

## 10. Monitoring rules [to finalize]
- Track each sleeve's realized vs expected per-year contribution; correlation drift to ORB; DLL-proximity on any day both sleeves + ORB align negative; regime tags (trend / vol-state).

## 11. Kill-switches / fail rules [to finalize]
- Sleeve disabled if: rolling-year contribution turns persistently negative; correlation-to-ORB rises above ~0.4 (loses diversification); any single day breaches DLL attributable to the sleeve; vol-carry ETP construction issue.

## 12. Paper-only rollout plan [to finalize]
- Stage 1: paper, smallest validated size (TSMOM 0.025×, VX $1k), report-only tracking vs ORB-alone for ≥1 quarter. Stage 2: review per-year + DLL behavior before any size increase. NO live/prop at any stage without separate explicit approval.

## 13. Gates
Deployment = operator-gated capital decision. NO live/prop exposure until separately, explicitly approved. This dossier informs that decision; it does not constitute or trigger it.

## 14. Open items (must close before dossier is deployment-decision-complete)
- [x] V-crash guard (24n) → GUARD_HELPS (general VIX>35 flatten, mild, not overfit) — recommended. §9.
- [x] Finer DSR proper trial-dispersion (24n) → DSR_PASS (deflated SR 1.0, 12 trials, disp 0.0035) — lift is NOT grid-luck.
- [x] True VIX-futures-curve vehicle vs SVXY ETP (24-vc2): RESOLVED — vehicle is NOT the limit. SVXY ≈ short-VXX (combined Sharpe 2.82 vs 2.79, corr −0.16 vs −0.15, both small decorrelated). Validated vol-carry leg is at its REACHABLE-DATA CEILING. True VX1/VX2 futures NOT reachable via Yahoo (404) → class-C feed need is the ONLY further upgrade path; until then vol-carry stays validated-small.
- [ ] MCL TSMOM leg (weakest, negative standalone) — keep for pool-diversification or drop.
- [ ] Per-year worst day/week/month table for the combined book.
- [ ] Monitoring/kill-switch/paper-rollout sections finalized (currently sketched §10-12).
**Status: 2 of 6 open items closed (both positive). Research evidence is strong enough to BUILD this dossier; 4 items remain before it is deployment-decision-complete. Deployment stays operator-gated.**
