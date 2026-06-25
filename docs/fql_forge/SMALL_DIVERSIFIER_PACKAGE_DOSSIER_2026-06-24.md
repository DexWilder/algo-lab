# Deployment-Decision Dossier — Small Diversifier Package (DRAFT, report-only)

> 🔴 **VOID (2026-06-25):** the PRIMARY engine of this package (ORB = `orb_breakout | ema_slope | profit_ladder`) carried a **same-day-close lookahead in its `ema_slope` filter**. Point-in-time revalidation at the deployed config (R4) shows ORB does **NOT survive** on any asset (clean Sharpe MNQ 0.27 / MES −0.19 / MGC 0.86 / MCL −0.84 / MYM −0.09 — see `TRIPWIRE_ORB_EMA_SLOPE_LOOKAHEAD_2026-06-25.md`). This package's entire rationale was "small decorrelated sleeves that improve the ORB book" — **with no real ORB edge, that rationale is void.** This dossier is **DEAD as written.** TSMOM and vol-carry may still have standalone merit, but they must be re-examined as potential *primaries* on their own point-in-time-clean evidence, not as ORB satellites. Do NOT act on any number in this dossier. Capital gate in force.

> **STATUS: research evidence is strong enough to BUILD this dossier — it is NOT "deployment-ready" / "turn it on."** This is a decision-support artifact. Building it is report-only research. NO promotion, wiring, scheduler, registry, sizing, paper, or live/prop mutation. Any deployment is a separate, explicitly operator-gated capital decision. Per [[feedback_validated_candidate_vs_deployment_dossier]].

## 1. Objective & portfolio role
Add small, decorrelated, **regime-complementary stabilizer sleeves** alongside the deployed ORB primary engine — to modestly improve combined risk-adjusted return (Sharpe/MAR) and rescue ORB's weak *grind* years, WITHOUT damaging prop-firm daily-loss constraints. **These are NOT new workhorses and NOT replacements for ORB.** Satellite stabilizers, sized small.

## 2. Instruments & exact construction
- **Primary (incumbent, unchanged):** ORB = `orb_breakout | ema_slope | profit_ladder`, MNQ, params stop_mult 0.5 / target 4.0 / trail 2.5. 1 contract baseline.
- **Sleeve A — TSMOM:** time-series momentum, 126-day (6mo) trailing-return SIGN, held, daily, pooled equal-contract across **MNQ/MES/MGC** (MCL leg DROPPED 2026-06-25 — see §14: standalone Sharpe −0.30/net −$5,891, negative even winsorized, AND the dirtiest series at 18 rollover-artifact days; dropping it marginally improved the package on every OOS axis). No flip. *Caveat: remaining pool is equity-heavy (MNQ/MES correlated) + gold; energy TSMOM could be revisited only via a clean roll-adjusted crude series, not raw MCL.*
- **Sleeve B — Vol-carry:** contango-only short-vol. Signal = VIX3M/VIX slope > 0 (prior close, no lookahead) → long short-vol. **Expression caveat:** tested via SVXY ETP (ETP decay/leverage-reset artifacts) — a true VIX-futures-curve vehicle is the class-C upgrade; do NOT deploy the raw ETP without the execution-realism section below.

## 3. Trade schedule / cadence
- ORB: intraday (existing). TSMOM: daily close evaluation, position held overnight, flips infrequent (~6mo signal). Vol-carry: daily close evaluation of slope, position held while contango. All signals computed at/after prior close, acted next session — no lookahead (verified).

## 4. Sizing — now PRINCIPLED (2026-06-25 CV1/CV2): vol-target, not hand-tuned — `PRINCIPLED_SIZING_CONFIRMS`
This is a **validated small-diversifier package with principled RESEARCH sizing — NOT a deployment-ready portfolio.** The hand-tuned 0.05×TSMOM / $2k vol-carry is REPRODUCED by principled risk-budgeting: **vol-target each decorrelated diversifier to a small fixed fraction k of ORB's daily $-risk.** Weights derived on H1 ONLY, evaluated OOS on H2; no optimizer, no H2-peeking → not overfit. Discovery became construction: the hand-tuned sizes were NOT magic numbers — they sit in the H1-derived principled neighborhood.

| variant | sleeve weights | H2 Sharpe | risk note |
|---|---|---|---|
| ORB alone | — | 3.38 | benchmark |
| hand-tuned (0.05× / $2k) | 0.05 / $2000 | 3.61 | discovery |
| **vol-target k=0.10** | 0.031 / $933 | 3.54 | **conservative canonical** — best risk (maxDD −2283, MAR 15.51) |
| **vol-target k=0.15** | 0.047 / $1400 | 3.59 | **upper research** — closest to hand-tuned perf |
| inverse-corr capped | 0.056 / $698 | 3.58 | corroborating |

All variants: **0 DLL breaches.**

**Canonical sizing rule (report-only):**
- **k=0.10 = conservative/default research sizing** (risk-cleanest).
- **k=0.15 = upper research sizing** (closest to hand-tuned performance).
- The final deployment-decision dossier presents BOTH, k=0.10 as default. Both remain report-only — NO sizing change, NO portfolio mutation, NO paper/live until separately operator-approved.

## 4b. (prior hand-tuned reference)
- TSMOM ≈ **0.05–0.10×** the pooled-1-contract notional (MAR-optimal ~0.025–0.05×, Sharpe-optimal ~0.10×).
- Vol-carry ≈ **$1–3k** notional.
- **Hard finding: oversizing destroys it** — TSMOM ≥0.25× and vol-carry ≥$5k introduce DLL breaches and Sharpe degradation. Sizing discipline is load-bearing.

## 5. Execution & financing / ETP realism
- ORB/TSMOM: micro/standard futures — no borrow; overnight = margin only (negligible financing); flip costs (commission + slippage) ARE included in the backtests.
- Vol-carry via SVXY: long-only (no borrow needed), ETP expense + roll-decay are embedded in the ETP's own return series (already captured). **OPEN FOR DEPLOYMENT (research-sufficient, NOT deployment-sufficient — see §14):** before any paper decision the vol-carry leg MUST state explicitly: (a) the actual tradable vehicle (SVXY vs short-VXX vs VX1/VX2 futures); (b) borrow / shorting / ETP decay + leverage-reset assumptions; (c) roll / term-structure proxy limitations (VIX3M/VIX slope is a proxy for the true VX1/VX2 curve); (d) vehicle-specific fail / monitoring rules + bid/ask + capacity at small size. The research signal is at its reachable-data ceiling; the *deployment vehicle realism* is a separate, still-open requirement.
- TSMOM overnight gap risk across 4 markets: covered in drawdown expectations.

## 6. Validation evidence (CONFIRMED, report-only)
- Combined book (ORB + 0.05×TSMOM + $2k VX): **Sharpe 2.84→3.02, MAR 22.07→23.27, 0 DLL breaches.**
- **Robust:** TSMOM improves 6/8 years; **both walk-forward halves improve** (H1 2.21→2.33, H2 3.38→3.61); PSR significant.
- **Additive / regime-complementary:** corr(TSMOM,VX)=0.19; 2022 split TSMOM +$936 vs VX −$1249 (opposite regimes). Combining beats either alone.
- Correlation measured vs ACTUAL ORB strategy PnL (−0.05/−0.16), not buy-and-hold proxy.

## 7. Drawdown expectations
- Combined maxDD ~−$2,344 (vs ORB-alone −$2,331) at the small allocation — essentially unchanged. Worst-day ~−$919 (vs −$850).
- **Per-year worst day / week (5d) / month (21d)** — combined book, full pool, k=0.10 vol-target (CV13, 2026-06-25). Every year stays within the $1,100 DLL on a single-day basis; every year net-positive:

| year | worst day | worst week | worst month | net | Sharpe |
|---|---|---|---|---|---|
| 2019 | −61 | −52 | (partial) | +142 | 4.70 |
| 2020 | −551 | −1606 | −1421 | +2787 | 1.41 |
| 2021 | −545 | −1240 | −1410 | +4226 | 2.06 |
| 2022 | −582 | −988 | −579 | +9151 | 3.03 |
| 2023 | −396 | −534 | −450 | +9060 | 4.55 |
| 2024 | −529 | −847 | −839 | +8369 | 3.07 |
| 2025 | −893 | −1195 | −2107 | +10607 | 2.76 |
| 2026 | −820 | −607 | +668 | +8961 | 5.59 |
| **ALL** | **−893** | **−1606** | **−2107** | **+53304** | **2.97** |

Worst single day across the whole sample −$893 (2025, within DLL); worst week −$1,606 (2020 COVID); worst month −$2,107 (2025). **2020 is the weakest year (Sharpe 1.41)** — consistent with §8 (the all-lose regime is a violent-V, not a grind). No DLL breaches in any year.

## 8. "What if ORB AND both sleeves lose together" scenario
- **2020 COVID is the empirical answer: all three struggled** (ORB weak intraday chop, TSMOM −$616 whipsawed by the V-reversal, VX −$62). **This package is NOT a sharp-V-crash hedge.** It rescues weak *grind* years (2019, 2021), not a violent reversal. Position-sizing must assume a simultaneous-loss day is possible; the small allocation keeps it within DLL, but this is the known failure mode.

## 9. V-crash behavior + guard → GUARD_HELPS (mild, general, not overfit)
General VIX>35 flatten on TSMOM (active 3.5% of days, NOT COVID-tuned): 2020 package Sharpe 1.39→1.53, full package 3.02→3.04, TSMOM-only 2.97→2.99. **Other years unchanged or slightly better** (2025 2.76→2.80; 2022 3.19→3.17 negligible) → helps the crash window WITHOUT damaging normal-year contribution and is a broad threshold (not overfit to COVID). **Recommended for the package.** Still NOT a full V-crash hedge (improvement is mild) — the small-sizing + caveat in §8 remain the primary protection.

## 10. Monitoring rules (FINALIZED 2026-06-25, report-only)
Tracked daily once (if) on paper; all are observe-and-alert, none auto-mutate:
1. **Per-sleeve realized vs expected contribution** — rolling-252d net per sleeve vs the per-year table (§7). Alert if a sleeve's rolling-year net falls below the worst historical year for that sleeve.
2. **Correlation drift to ORB** — rolling-126d |corr(sleeve, ORB daily PnL)|. Baseline TSMOM 0.09, VC 0.15 (H1). Alert at >0.30, kill-review at >0.40 (diversification lost — see §11).
3. **Vol-target drift** — recompute each sleeve's trailing-63d σ vs ORB's; alert if the implied k drifts outside [0.07, 0.18] (canonical band 0.10–0.15), i.e. the sleeve has silently grown/shrunk relative to ORB risk.
4. **DLL-proximity / co-loss days** — flag any day all-three (ORB + both sleeves) align negative; track distance to the $1,100 DLL. Per §7 the historical worst single day is −$893 (within DLL), so a breach would be out-of-distribution and is itself an alert.
5. **Regime tags** — trend / vol-state (VIX level, VIX3M/VIX slope) attached to each day for post-hoc attribution.

## 11. Kill-switches / fail rules (FINALIZED 2026-06-25, report-only — disable = revert to ORB-alone, operator-confirmed)
A sleeve is flagged for DISABLE (operator-confirmed, not auto) if ANY:
1. Rolling-252d contribution turns net-negative for **2 consecutive quarters** (persistent, not one bad quarter).
2. Rolling-126d |corr-to-ORB| **> 0.40** (diversification — the entire rationale — is gone).
3. Any single day breaches the **$1,100 DLL attributable to the sleeve** (out-of-distribution per §7).
4. Vol-carry vehicle integrity issue (ETP decay/leverage-reset/roll anomaly, or the §5 deployment-vehicle assumptions are violated in practice).
5. Implied k drifts outside **[0.07, 0.18]** for >21 trading days and is not corrected.
Whole-package kill = revert to ORB-alone (the incumbent), which is always the safe fallback.

## 12. Paper-only rollout plan (FINALIZED 2026-06-25, report-only — every stage operator-gated)
- **Stage 0 (now):** report-only, NO capital. This dossier + CV-series evidence. No paper wiring yet.
- **Stage 1 (on explicit approval only):** paper, **smallest validated size — vol-target k=0.10 conservative default** (TSMOM≈0.031× / VC≈$933), TSMOM pool MNQ/MES/MGC (MCL dropped), V-crash guard ON (§9). Track all §10 monitors vs ORB-alone for **≥1 quarter**. Success = sleeves behave within the §7 envelope, no §11 trigger, realized corr-to-ORB stays low.
- **Stage 2 (separate approval):** review per-year + DLL behavior; only then consider k=0.15 upper sizing. Resolve §5 deployment-vehicle realism for vol-carry BEFORE any size increase.
- **Live/prop:** NOT in scope at any stage of this dossier. Separate explicit capital decision, separate DSCL/vehicle-realism gate. Per [[feedback_data_audit_green_scope]] research-clean ≠ capital-clean.

## 13. Gates
Deployment = operator-gated capital decision. NO live/prop exposure until separately, explicitly approved. This dossier informs that decision; it does not constitute or trigger it.

## 14. Open items (must close before dossier is deployment-decision-complete)
- [x] V-crash guard (24n) → GUARD_HELPS (general VIX>35 flatten, mild, not overfit) — recommended. §9.
- [x] Finer DSR proper trial-dispersion (24n) → DSR_PASS (deflated SR 1.0, 12 trials, disp 0.0035) — lift is NOT grid-luck.
- [~] True VIX-futures-curve vehicle vs SVXY ETP (24-vc2): RESOLVED FOR RESEARCH CLASSIFICATION ONLY — vehicle is not the limit for the *research* signal (SVXY ≈ short-VXX, combined Sharpe 2.82 vs 2.79; validated leg at reachable-data ceiling; true VX1/VX2 not on Yahoo → class-C). **NOT resolved for DEPLOYMENT** — vehicle/execution realism (actual tradable vehicle, ETP decay/leverage-reset/borrow assumptions, roll/term-structure proxy limitations, vehicle-specific fail/monitoring rules) MUST be stated explicitly before any paper decision. See §5 (still OPEN for deployment). Do not read "resolved" as "deployment-ready."
- [x] MCL TSMOM leg (weakest, negative standalone) → **DROP** (CV13, 2026-06-25). Standalone Sharpe −0.30 / net −$5,891 (winsorized −0.36 / −$6,052 → not artifact-inflated, just a drag); 18 rollover-artifact days (dirtiest series). Pool minus MCL is marginally BETTER OOS on every axis (Sharpe 3.54→3.56, MAR 15.51→15.84, maxDD −2283→−2249, net +$207) with no hedge benefit lost. TSMOM pool is now MNQ/MES/MGC. Caveat: equity-heavy remaining pool; energy TSMOM only via clean roll-adjusted crude.
- [x] Per-year worst day/week/month table for the combined book → §7 (CV13). All years within DLL, all net-positive; 2020 weakest (Sharpe 1.41).
- [x] Monitoring/kill-switch/paper-rollout sections finalized (§10-12, 2026-06-25) — concrete thresholds tied to §7 evidence; all observe-and-alert, operator-confirmed, none auto-mutate.
**Status: 5 of 6 fully closed (V-crash guard, DSR, MCL-leg DROP, per-year table, monitoring/kill/rollout). The ONLY remaining open item is §5 true-VIX DEPLOYMENT-vehicle realism — and that is deployment-gated by design, NOT a research item (it cannot/should not close until a real paper decision). Research-side, this dossier is COMPLETE. Sizing is PRINCIPLED (CV1/CV2 → `PRINCIPLED_SIZING_CONFIRMS`). This is a validated small-diversifier package with principled RESEARCH sizing — NOT a deployment-ready portfolio. Deployment stays operator-gated.**
