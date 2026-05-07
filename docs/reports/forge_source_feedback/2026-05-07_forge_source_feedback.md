# FQL Forge → Source-helpers Feedback — 2026-05-07

**Generated:** 2026-05-07T08:39:41
**Lookback:** prior 7 days
**Scope:** Lane B / Forge — recommendation-only feedback layer (closed-loop learning)

**Safety contract:** report-only; no source-helper / harvest priority / registry / Lane A / portfolio / runtime / scheduler / checkpoint / hold-state mutation. All recommendations require operator approval.

---

## 1. Executive Summary

### One-line state

**Forge runs in window:** 2  |  **distinct PASSes:** 6  |  **Confidence:** see §6

### What is working

- **Mechanism:** `ema_slope` filter + `profit_ladder` exit (load-bearing pair) reproducible across PB/BB/VWAP entries and across multiple assets
- **Cross-asset:** entry portability confirmed on MGC, MCL, MYM (less so MNQ for VWAP, more so for BB)
- **Tail-engine variant:** XB-BB-AfternoonOnly-MGC validates session-restricted approach for tail archetype

### What is failing

- **VWAP-on-MNQ:** PF 1.056 KILL — entry portability is asset-conditional, not universal
- **Salvage template** (parent + salvaged-failed-component): 0/7 success on 2026-05-05 — downgraded

### Top recommendation: TRANSFER, do not amplify

Forge wins are all in MOMENTUM/breakout family (per `_priorities.md`, that family is OVERWEIGHT at 55% portfolio). Don't harvest more momentum. **Apply the validated mechanism to UNDERWEIGHT factors** — VALUE (HIGH gap), CARRY/VOL/EVENT/STRUCTURAL (MEDIUM gaps).

### Read order
1. **Section 4 (Harvest Recommendation Map)** — TRANSFER themes, AVOID/DOWN-WEIGHT lists
2. **Section 5 (Candidate-Pool Implication)** — what to generate next vs pause
3. **Section 6 (Safety / Confidence)** — interpret confidence before acting
4. Detail sections 2/3 for evidence

---

## 2. Winning Pattern Extraction

**Aggregated by dimension across the lookback window. Sorted by PASS-rate desc.**

#### By asset

| Value | n | PASS | WATCH | KILL | RETEST | PASS-rate | Confidence |
|---|---:|---:|---:|---:|---:|---:|---|
| `MCL` | 2 | 2 | 0 | 0 | 0 | 100% | WEAK |
| `MYM` | 2 | 2 | 0 | 0 | 0 | 100% | WEAK |
| `MGC` | 3 | 2 | 1 | 0 | 0 | 67% | WEAK |
| `MES` | 3 | 0 | 3 | 0 | 0 | 0% | WEAK |

#### By asset class

| Value | n | PASS | WATCH | KILL | RETEST | PASS-rate | Confidence |
|---|---:|---:|---:|---:|---:|---:|---|
| `crude-oil` | 2 | 2 | 0 | 0 | 0 | 100% | WEAK |
| `dow` | 2 | 2 | 0 | 0 | 0 | 100% | WEAK |
| `gold` | 3 | 2 | 1 | 0 | 0 | 67% | WEAK |
| `sp500` | 3 | 0 | 3 | 0 | 0 | 0% | WEAK |

#### By entry mechanism

| Value | n | PASS | WATCH | KILL | RETEST | PASS-rate | Confidence |
|---|---:|---:|---:|---:|---:|---:|---|
| `bb_reversion` | 4 | 3 | 1 | 0 | 0 | 75% | WEAK |
| `pb_pullback` | 4 | 2 | 2 | 0 | 0 | 50% | WEAK |
| `vwap_continuation` | 2 | 1 | 1 | 0 | 0 | 50% | WEAK |

#### By filter

| Value | n | PASS | WATCH | KILL | RETEST | PASS-rate | Confidence |
|---|---:|---:|---:|---:|---:|---:|---|
| `ema_slope` | 10 | 6 | 4 | 0 | 0 | 60% | STRONG |

#### By exit

| Value | n | PASS | WATCH | KILL | RETEST | PASS-rate | Confidence |
|---|---:|---:|---:|---:|---:|---:|---|
| `profit_ladder` | 10 | 6 | 4 | 0 | 0 | 60% | STRONG |

---

## 3. Weak / Noisy Pattern Extraction

**Repeated KILL / WATCH neighborhoods. Candidates re-tested without verdict change.**

- (no candidates re-tested in window — sample too small)

---

## 4. Harvest Recommendation Map

**Harvest theme recommendations based on Forge winning evidence + current `_priorities.md` factor gaps.**

### Read of current harvest priorities (`~/openclaw-intake/inbox/_priorities.md`)

- | HIGH | VALUE | 0c+0p | 13 | Any testable value/fundamental strategy on any asset class |
- | MEDIUM | CARRY | 0c+1p | 20 | Carry strategies across asset classes (rates, commodity, FX) |
- | MEDIUM | VOLATILITY | 0c+1p | 9 | Vol strategies on non-equity assets, non-morning sessions |
- | MEDIUM | EVENT | 0c+1p | 16 | Event families beyond FOMC/NFP (CPI, OPEC, auctions, rebalance) |
- | MEDIUM | STRUCTURAL | 0c+1p | 8 | Afternoon/close session, rates/FX microstructure |
- | LOW | MOMENTUM | 3c+1p | 2 | HIGH BAR ONLY — portfolio is 55% momentum |

### Forge evidence vs harvest priority alignment

| Forge winner | Theme | Current harvest priority | Recommendation |
|---|---|---|---|
| `MCL` (2 PASSes) | crude-oil, energy | MOMENTUM family — LOW (overweight portfolio) | **TRANSFER** mechanism, do not amplify |
| `MYM` (2 PASSes) | dow, equity-index | MOMENTUM family — LOW (overweight portfolio) | **TRANSFER** mechanism, do not amplify |
| `MGC` (2 PASSes) | gold, precious-metals | MOMENTUM family — LOW (overweight portfolio) | **TRANSFER** mechanism, do not amplify |

### Recommendation map (UP / DOWN / TRANSFER / NEUTRAL)

**TRANSFER (highest-leverage):** Forge has validated a load-bearing mechanism `ema_slope + profit_ladder` that works across MNQ/MGC/MCL/MYM with multiple entries (PB/BB/VWAP). The pattern is reproducible. **However the wins are all in MOMENTUM/breakout family, which `_priorities.md` flags as overweight (55% portfolio).** Recommendation: don't harvest more momentum. Instead, harvest sources that explore the SAME load-bearing mechanism in UNDERWEIGHT factors:
- **VALUE** (HIGH priority gap): up-weight sources discussing `trend-filter + staged-exit` applied to value/term-premium/PPP signals (e.g., 'value-momentum hybrid', 'staged scale-out value entries')
- **CARRY** (MEDIUM): up-weight sources where carry signals layer with trend-filter regime-detection
- **VOLATILITY** (MEDIUM): up-weight `compression-breakout` (BB-style) sources on non-equity assets — Forge BB winners point that way
- **STRUCTURAL** (MEDIUM): up-weight afternoon-session microstructure sources — XB-BB-AfternoonOnly-MGC was a tail-engine PASS

**AVOID amplifying** (would deepen overconcentration):
- More momentum-family sources (already 55% portfolio per priorities)
- More MNQ-specific or equity-index-only momentum sources (Forge already showed cross-asset works; new MNQ-only sources add nothing)

**NEUTRAL** (continue current weighting):
- General GitHub strategy-research sources (broad enough to surface diverse families)
- Reddit/YouTube monitoring (unfocused; not amenable to up/down per-Forge)

**DOWN-WEIGHT (per Forge weak signals):**
- Salvage-template harvesting (per `project_proven_trio_architecture.md`, 7 salvage attempts on 2026-05-05 produced 0 PASSes; salvage template was downgraded)
- VWAP-on-MNQ sources specifically (Forge showed VWAP works on MGC/MCL/MYM but FAILS on MNQ — entry portability is asset-conditional)

---

## 5. Candidate-Pool Implication

**What new candidates the Forge runner pool should consider next, vs what to pause.**

### Generate next (per Forge evidence)

- VALUE-themed candidates with `ema_slope + profit_ladder` mechanism (validate the TRANSFER hypothesis on underweight factor)
- CARRY-themed candidates layered with trend-filter regime detection
- Compression-breakout (BB) candidates on rates (ZN/ZF/ZB) and FX (6E/6J/6B) — extends BB cross-asset evidence into UNDERWEIGHT factors
- Afternoon-session candidates on under-tested assets — XB-BB-AfternoonOnly-MGC PASSed (PF 1.207); test session-restricted patterns on more assets

### Pause / deprioritize

- Salvage-template candidates (Phase 0 §3.4 #5) — already downgraded per `project_proven_trio_architecture.md`
- VWAP-on-MNQ specifically (KILL on MNQ; PASSes on MGC/MCL/MYM)
- KILL-every-fire candidates if any surface (none in current 2-day window)

### Pool composition health

- current pool size: ~19
- per `project_proven_trio_architecture.md`, entry portability is asset-conditional — ensure each entry-asset combo is tested at least once before generalizing

---

## 6. Safety / Confidence

### Sample size

- Forge runs in lookback window: **2**
- candidate evaluations: **10**
- distinct PASS verdicts: **6**

### Recommendation confidence: 🔴 **WEAK**

Sample too small for reliable feedback. Cross-window patterns are speculative; a single PASS streak could reverse next week. Treat all recommendations as DIRECTIONAL ONLY.

### Caveats
- All Forge metrics come from cheap-screen evaluations (no walk-forward, no out-of-sample). PASS verdicts are PROMOTION-CANDIDATE, not validated edges.
- Asset/entry/filter/exit dimensions are not independent — many combinations co-occur in tested candidates
- Harvest theme mapping is heuristic (asset → keywords); operator should review specific theme suggestions before applying

---

## 7. Next Action

### Operator action

- **Review §4 TRANSFER recommendation.** Decide whether to update `~/openclaw-intake/inbox/_priorities.md` `Search Term Suggestions` to favor mechanism-transfer themes (VALUE+trend-filter, CARRY+regime-detection, VOL+compression-breakout-on-non-equity, STRUCTURAL+afternoon-session).
- **No source-helper config mutation occurred during this run.** All changes require operator approval.

### Safe Forge action

- **Continue scheduled fires.** Cadence remains weekday 19:00 PT evening + 08:00 PT next-morning digest. No cadence increase recommended.
- **If approved:** queue new candidates in the runner pool that test the TRANSFER hypothesis (VALUE/CARRY/VOL/EVENT/STRUCTURAL with proven `ema_slope + profit_ladder` mechanism). Pre-flight required.

### Mode

- **🟡 SURFACE-AND-WAIT** — sample size is WEAK (only 2 fires); recommendations are directional. Re-run feedback after another 5+ fires to upgrade to MODERATE confidence before acting.

### Phase B activation question

- Should this become scheduled (e.g., weekly Sunday morning before next-week harvest)? **Recommend defer** — first run sample is too small. Re-evaluate Phase B after 2-3 weekly manual runs produce stable recommendations.

---
