# Pre-Flight: Source-Priority Patch (Forge → Source-Helpers Closed Loop)

**Filed:** 2026-05-07
**Authority:** T2 (operator-gated). Pre-flight is T1 diagnostic.
**Lane:** B (Forge / harvest)
**Operator decision required:** approve / partial / defer / reject the proposed harvest-priority changes below

---

## Why this pre-flight exists

The Forge → source-helpers feedback layer (commit `d0438b1`, `research/forge_source_feedback.py`) ran on 2026-05-07 and surfaced an actionable insight:

> Forge wins are all in MOMENTUM/breakout family. Per `~/openclaw-intake/inbox/_priorities.md`, that family is OVERWEIGHT (55% portfolio). **Don't harvest more momentum. Transfer the validated mechanism (`ema_slope + profit_ladder`) to UNDERWEIGHT factors.**

This pre-flight converts that recommendation into a concrete operator-reviewable patch. Per safety contract: **no source-helper config / harvest priority mutation occurs in this pre-flight.** Operator decides whether to apply.

---

## Section 1 — Current Forge evidence summary

**Lookback window:** 2 fires (2026-05-05 + 2026-05-06)
**Confidence:** WEAK on entry/asset; STRONG on filter+exit (load-bearing pair)

### Aggregated by dimension

| Dimension | Top finding | N | PASS-rate |
|---|---|---:|---:|
| Filter | `ema_slope` | 10 | 60% (STRONG) |
| Exit | `profit_ladder` | 10 | 60% (STRONG) |
| Entry | `bb_reversion` | 4 | 75% |
| Entry | `pb_pullback` | 4 | 50% |
| Entry | `vwap_continuation` | 2 | 50% |
| Asset | `MCL` (energy) | 2 | 100% |
| Asset | `MYM` (Dow equity) | 2 | 100% |
| Asset | `MGC` (gold) | 3 | 67% |
| Asset | `MES` (S&P equity) | 3 | 0% |

### Key architecture findings (from `project_proven_trio_architecture.md`)

- **`ema_slope` is uniquely load-bearing.** Filter sweep showed PF 1.621 (ema_slope) vs 1.068 (best alternative). Don't substitute.
- **Entry portability is asset-conditional.** VWAP works on MGC/MCL/MYM, fails on MNQ. BB strongest on MYM (PF 1.785), MGC (1.522). PB is most universal.
- **Exit slot has 3 viable alternatives.** profit_ladder PF 1.62 ≈ chandelier 1.571 ≈ time_stop 1.486. midline_target is weak (1.085).
- **Salvage template downgraded.** 7 attempts on 2026-05-05, 0 PASSes.

### Failure signals

- **VWAP-on-MNQ:** PF 1.056 (KILL). Entry-asset combo, not entry alone, fails.
- **Salvage harvesting:** 0% success rate (downgraded to deprioritize).
- **MES (S&P):** 0% PASS rate across 3 fires — equity-index momentum saturation likely.

---

## Section 2 — Current source/priority state

### `~/openclaw-intake/inbox/_priorities.md` Priority Factor Gaps

| Priority | Factor | Active | Ideas | Target |
|---|---|---|---:|---|
| **HIGH** | **VALUE** | 0c+0p | 13 | Any testable value/fundamental strategy on any asset class |
| MEDIUM | CARRY | 0c+1p | 20 | Carry strategies across asset classes (rates, commodity, FX) |
| MEDIUM | VOLATILITY | 0c+1p | 9 | Vol strategies on non-equity assets, non-morning sessions |
| MEDIUM | EVENT | 0c+1p | 16 | Event families beyond FOMC/NFP (CPI, OPEC, auctions, rebalance) |
| MEDIUM | STRUCTURAL | 0c+1p | 8 | Afternoon/close session, rates/FX microstructure |
| LOW | MOMENTUM | 3c+1p | 2 | HIGH BAR ONLY — portfolio is 55% momentum |

**Generator:** `scripts/claw_control_loop.py` (auto-rewrites `_priorities.md` every 30 min). Direct edits to `_priorities.md` get overwritten.

### Current `Search Term Suggestions` section (auto-generated)

```
### For intraday breakout/trend (HIGH):
- intraday trend following futures, price action breakout system
- ATR channel breakout futures, range expansion continuation
- EMA crossover intraday futures, momentum burst detection
- opening range expansion, first N minutes breakout

### For session patterns (MEDIUM):
- afternoon session futures strategy, closing auction momentum
- overnight session edge futures, pre-market range strategy
- London-NY session transition futures

### For component fragments (HIGH):
- profit target exit research, trailing stop optimization futures
- trend filter comparison, EMA slope vs VWAP slope futures
- breakout confirmation candle pattern, volume confirmation entry
```

**Observation:** "intraday breakout/trend" is marked HIGH priority in suggestions, but the factor table marks MOMENTUM as LOW priority (overweight). Internal contradiction — the suggestions generator may be lagging behind the factor-priority logic.

### `scripts/fetch_github_leads.py` QUERIES (durable lever, 30 entries)

Current GitHub query mix is balanced but skews intraday-momentum-heavy. Reddit equivalent in `fetch_reddit_leads.py`.

---

## Section 3 — Proposed UP-WEIGHT themes (TRANSFER recommendation)

Apply `ema_slope + profit_ladder` mechanism to underweight factors. Specific themes:

### 3a. VALUE (HIGH gap, 0c+0p)
**Rationale:** Biggest factor gap; zero coverage. Forge mechanism could transfer if Value signals can be filtered by trend regime and exited via staged profit-taking.

**Specific themes to harvest:**
- "value momentum hybrid systematic"
- "trend-filtered value strategy futures"
- "term premium trading with regime filter"
- "PPP value FX with trend confirmation"
- "earnings yield futures systematic with momentum filter"

### 3b. CARRY (MEDIUM gap, 0c+1p, 20 ideas blocked)
**Rationale:** Many ideas already in queue but blocked. Layering trend-filter regime detection might unblock subset.

**Specific themes:**
- "carry strategy regime detection futures"
- "FX carry trend filter systematic"
- "treasury carry with EMA regime"
- "commodity curve carry trend-confirmed"

### 3c. VOLATILITY (MEDIUM gap, 0c+1p)
**Rationale:** Forge BB winners on MGC/MCL/MYM suggest compression-breakout pattern works cross-asset. Apply to non-equity, non-morning sessions per priority spec.

**Specific themes:**
- "volatility compression breakout treasury futures"
- "Bollinger compression FX systematic"
- "ATR squeeze breakout commodity futures"
- "VIX-conditional volatility regime futures"

### 3d. STRUCTURAL (MEDIUM gap, 0c+1p)
**Rationale:** XB-BB-AfternoonOnly-MGC was a tail-engine PASS (PF 1.207, n=376). Session-restricted patterns work; extend to under-tested asset/session combinations.

**Specific themes:**
- "afternoon session microstructure futures"
- "treasury close auction strategy systematic"
- "session-transition rates strategy"
- "FX close-session volatility systematic"

---

## Section 4 — Proposed DOWN-WEIGHT themes

### 4a. Salvage-template harvesting
**Evidence:** 7 attempts on 2026-05-05, 0 PASSes (per `project_proven_trio_architecture.md`).
**Action:** deprioritize sources discussing "rescue failed strategies" / "modified parent strategies" / parameter-resurrection of dead candidates.

### 4b. Generic momentum pile-ons
**Evidence:** Portfolio is 55% momentum; `_priorities.md` flags as overweight; Forge wins amplify already-saturated family.
**Action:** trim generic momentum-themed queries; preserve specific high-bar gates (afternoon, close-driven, uncovered asset).

### 4c. VWAP-on-MNQ specifically (asset-conditional weakness)
**Evidence:** XB-VWAP-EMA-Ladder-MNQ PF 1.056 KILL. Entry portable on MGC/MCL/MYM but not MNQ.
**Action:** if any source-helper queries target VWAP+nasdaq specifically, deprioritize. (Inspection of current QUERIES list shows none explicitly — this is preventive.)

---

## Section 5 — Exact proposed edits / patch blocks

Two surfaces, two levers. Operator chooses scope.

### Patch A — `scripts/fetch_github_leads.py` QUERIES list (DURABLE; recommended primary lever)

**Remove (or comment-out) — generic momentum pile-on:**
```python
# Line 56 — DELETE (generic momentum already overweight)
"momentum trading systematic python",
```

**Add — VALUE mechanism-transfer queries (4 new):**
```python
# After line 80 (end of QUERIES) add:
    # VALUE mechanism-transfer (per Forge feedback 2026-05-07)
    "value momentum hybrid systematic",
    "trend-filtered value strategy futures",
    "term premium trading with regime filter",
    "earnings yield futures systematic with momentum filter",
```

**Add — CARRY + trend-filter (2 new):**
```python
    # CARRY + trend-filter (per Forge feedback 2026-05-07)
    "carry strategy regime detection futures",
    "treasury carry with EMA regime filter",
```

**Add — VOLATILITY compression-breakout on non-equity (2 new):**
```python
    # VOLATILITY non-equity compression-breakout (per Forge feedback 2026-05-07)
    "volatility compression breakout treasury futures",
    "Bollinger squeeze breakout commodity futures",
```

**Add — STRUCTURAL afternoon/session (2 new):**
```python
    # STRUCTURAL afternoon/close session (per Forge feedback 2026-05-07)
    "afternoon session microstructure futures",
    "treasury close auction strategy systematic",
```

**Net:** +10 / -1 = 30 → 39 queries. The `MAX_LEADS = 15` cap remains, so total intake doesn't increase — but the *mix* of leads shifts toward underweight factors.

### Patch B — `scripts/fetch_reddit_leads.py` QUERIES list (parallel changes)

Same set of additions; same single removal. Operator can choose A-only, B-only, or both.

### Patch C — `_priorities.md` Search Term Suggestions section

**Issue:** auto-generated by `scripts/claw_control_loop.py`. Direct edits to `_priorities.md` get overwritten on the next 30-min loop.

**Two options:**

**C.1** — modify `claw_control_loop.py` generator logic to incorporate Forge feedback. Larger change; risky to existing automation.

**C.2** — leave `_priorities.md` generator alone for now. The Patch A/B query changes are enough to shift harvest yield. If shift proves successful (next monthly review confirms underweight factor coverage growing), then revisit C.1 to align generator with feedback.

**Recommendation:** defer Patch C to a later session. Rely on A+B for now. Surface this design choice to operator: do we want feedback to influence `_priorities.md` generator, or stay at the query-list level?

---

## Section 6 — Risk analysis

| Risk | Severity | Mitigation |
|---|---|---|
| Overfitting to 2 Forge fires | **HIGH** | All recommendations are flagged WEAK confidence. Patch is small (+10/-1 queries) and easily reversible. |
| Deepening momentum overconcentration if patch is misapplied | LOW | Patch removes 1 generic momentum query; adds none in momentum theme. Direction is correct. |
| New queries return zero results / low quality | LOW-MEDIUM | First post-patch source-helper run (next Sun/Wed 20:00 PT) will surface this; no harm if it does. |
| `_priorities.md` generator divergence | LOW | Documented; operator decides whether to address in C.1 later. |
| Automatic application — UNAUTHORIZED | N/A | This pre-flight does NOT apply any patch. Operator must explicitly approve. |
| Source-helper Lane A surface compromise | N/A | Source-helpers is Lane B; no Lane A surface touched by patch A or B. |

**Net risk: LOW.** The patch is small, reversible, and operator-gated. Worst case: 10 new queries return junk for a week and are reverted.

---

## Section 7 — Operator decision

Choose one:

### ☐ APPROVE FULL
Apply Patch A + Patch B as written. Defer Patch C. Next source-helper fire (Sun 2026-05-10 20:00 PT) tests the new query mix. Re-fire feedback after 7 days to assess yield shift.

### ☐ APPROVE PARTIAL
Pick subset of patches (e.g., A only; or VALUE+CARRY only; or one query at a time). Apply chosen subset; defer rest.

### ☐ DEFER
Wait for more Forge fires before acting. Re-evaluate after another week of organic data accumulates. Today's 2-fire sample may be too thin.

### ☐ REJECT
Do not apply any patch. Reasoning: e.g., concern about the WEAK confidence; want to see source-yield memory (#4 in upgrade plan) built first; want monthly review to corroborate.

### Optional clarifier — `_priorities.md` generator design choice
- ☐ Keep generator passive (current state — Patch A/B is enough)
- ☐ Plan future C.1 to wire Forge feedback into the generator

---

## Section 8 — Recommendation

**My recommendation: APPROVE PARTIAL — apply Patch A only, defer Patch B and C.**

Reasoning:
1. GitHub leads (Patch A) are the largest source channel and the most directly query-driven. Smallest blast radius for first feedback-loop application.
2. Reddit (Patch B) is more conversational; the QUERIES change has lower marginal effect since posts surface organically. Apply only after Patch A proves out.
3. `_priorities.md` generator (Patch C) is the deepest change; defer until we have multi-week feedback evidence to justify generator modification.
4. The single removal (`"momentum trading systematic python"`) is the cleanest first action — directly addresses overconcentration.
5. The +9 additions cover all four underweight factors (VALUE/CARRY/VOL/STRUCTURAL); each gets at least one direct query.

If Patch A proves out (next monthly review shows underweight factor coverage growing), expand to Patch B in 2-4 weeks. Patch C only after multi-month evidence justifies a deeper architectural touch.

---

## Section 9 — If approved: application sequence

(Operator approval required before any of this happens)

```bash
# 1. Edit scripts/fetch_github_leads.py per Patch A above
# 2. Verify file syntax: python3 -c "exec(open('scripts/fetch_github_leads.py').read().split('def ')[0])"
# 3. Spot-check QUERIES count: 30 → 39 expected
# 4. Single bundled commit: "Lane B / Forge: apply source-priority patch (forge feedback 2026-05-07)"
# 5. No other surfaces touched
# 6. Wait for next source-helper fire (Sun 2026-05-10 20:00 PT)
# 7. Verify next forge_source_feedback.py run reflects shifted yields
```

No registry / Lane A / portfolio / runtime / scheduler / checkpoint / hold-state mutation throughout.

---

*Filed 2026-05-07. Lane B / Forge. T1 diagnostic; T2 application requires operator approval. Recommendation-only at filing time. Closed-loop tier 2 (the system now learns AND can recommend what to look for next).*
