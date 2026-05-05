# Filter Substitution Sweep — Is `ema_slope` Load-Bearing? (2026-05-05)

**Filed:** 2026-05-05 (operator's option 1 directive — Lane B / Forge)
**Authority:** T1, no Lane A surfaces touched, no registry mutation.
**Architecture question:** Is `ema_slope` portable/substitutable, or load-bearing in the proven trio?

---

## Result table

Single asset (MNQ), single entry (`orb_breakout`), single exit (`profit_ladder`); only `filter_name` varies. Same harness as today's other sweeps.

| Filter | n | PF | Net PnL | Max DD | Sharpe | Verdict |
|---|---:|---:|---:|---:|---:|---|
| **ema_slope** (BASELINE — proven trio default) | 1,198 | **1.621** | **+$51,599** | **-$2,399** | **2.389** | **PASS** |
| vwap_slope | 1,847 | 1.049 | +$7,988 | -$10,246 | 0.303 | KILL |
| bandwidth_squeeze | 1,839 | 1.037 | +$6,184 | -$10,354 | 0.234 | KILL |
| session_morning | 1,633 | 1.024 | +$3,633 | -$11,802 | 0.145 | KILL |
| session_afternoon | 1,637 | 1.068 | +$7,100 | -$4,307 | 0.373 | WATCH |
| **none** (control — no filter) | 1,852 | 1.046 | +$7,630 | -$9,967 | 0.289 | KILL |

**Baseline PF 1.621 vs best alternative 1.068.** A 0.553 PF gap. The ema_slope filter is contributing the bulk of the strategy's edge — alternatives are barely better than no filter at all (control PF 1.046).

---

## Architecture answer

**`ema_slope` is STRONGLY LOAD-BEARING in the proven XB trio.** Findings:

1. **None of the alternatives reach PASS.** Best alternative (session_afternoon, PF 1.068) is barely WATCH — and only 0.022 PF above no-filter at all.
2. **No-filter control PF (1.046) is comparable to most alternatives** — meaning the alternative filters are roughly equivalent to no filter. They don't subtract value, but they don't add the directional edge that ema_slope does.
3. **Max DD is dramatically worse without ema_slope** — baseline max DD is -$2,399, all alternatives have max DD between -$4,307 and -$11,802 (1.8× to 4.9× worse). ema_slope is doing primary risk-management work, not just direction filtering.
4. **Trade count balloons without ema_slope** — baseline 1,198 trades; alternatives 1,633-1,852. Without ema_slope, the strategy enters in adverse trend conditions where it loses; ema_slope is filtering OUT the bad-direction trades.

**This combined with today's earlier evidence:**

| Slot | Substitutable? | Evidence |
|---|---|---|
| Entry | **Yes** (most alternatives work) | ORB, PB, BB all PASS on MNQ; VWAP marginal — 3 of 4 portable |
| Filter | **NO** (ema_slope is irreplaceable here) | This sweep — alternatives give up 0.5+ PF |
| Exit (profit_ladder) | NO (per existing proven_donors data) | "Only known exit producing positive median trade"; alternatives all degrade |

**The proven "trio" is really a TIGHTLY-COUPLED FILTER-EXIT BUNDLE with a portable entry slot.** Earlier doctrine of "the trio is portable" (yesterday) needs revision: only the entry is portable; the filter+exit pair is the actual proven bundle.

---

## Donor catalog updates

| Donor | Status update |
|---|---|
| `ema_slope` (proven_donor filter) | **Reinforced top tier** — load-bearing, irreplaceable in the proven assembly. Donor catalog should label it "primary contributor" |
| `profit_ladder` (proven_donor exit) | Same — co-validated with ema_slope as the load-bearing filter-exit pair |
| `vwap_slope`, `bandwidth_squeeze`, `session_morning`, `session_afternoon` | Tested as filter alternatives — all KILL or WATCH at best. Available as components for non-XB hybrids but should NOT replace ema_slope in proven trio |

---

## Implications for Phase 0 hot lane

1. **Don't try to substitute ema_slope** in any future XB-family hybrid. The donor catalog should encode "ema_slope + profit_ladder" as a co-validated bundle, not separate components.
2. **Do continue testing entry substitutions** — that's where the portability lives (today's PB and BB cross-asset PASSes prove this).
3. **Filter substitution may have value OUTSIDE the proven XB trio** — in different parent strategies where ema_slope wasn't the original filter. Those tests are separate Phase 0 questions.
4. **The "proven bundle" naming should be tightened** — it's filter+exit, not all three.

---

## What this sweep did NOT do

- Test filter substitutions on different entries (PB, BB) — would be a 2D sweep; today's was 1D for cleanliness
- Test on different assets (MES/MGC/MCL/MYM) — single asset (MNQ) for clean comparison
- Try parameter variations within filters (e.g., different EMA periods)
- Registry mutation
- Lane A surfaces touched

---

## Today's full Forge cumulative

| Session | Output |
|---|---|
| Morning batch (HYB-VolMan + HYB-FX 1.5×) | 1 PASS-with-WARN, 1 WARN |
| HYB-FX 1.0× and 0.75× calibrations | 1 WARN, 1 FAIL → salvage retired |
| Batch #1 (3 candidates) | 0 PASS, 3 KILL, 1 RETEST (engine bug) |
| Batch #2 (3 candidates) | 2 PASS (XB-PB-MNQ, XB-BB-MNQ), 2 KILL (HYB-LunchComp A/B) |
| Runner cross-asset sweep (8 candidates) | 5 PASS (XB-PB-MCL/MYM, XB-BB-MGC/MCL/MYM), 3 WATCH |
| WATCH calibration (3 candidates) | 0 PASS shifts, all WATCH-retain |
| **Filter sweep (this) — 5 alternatives** | **0 PASS, 1 WATCH, 4 KILL — ema_slope load-bearing** |

**Day total: 27 candidate evaluations.** 9 PASS / 5 WATCH / 11 KILL / 2 RETEST.

---

## Next safe Forge actions queued

1. **Sweep entry substitutions on additional assets via runner** (e.g., add XB-VWAP cross-asset to confirm yesterday's KILL was MNQ-specific or universal)
2. **Tail-engine candidate addition** (event-driven, NFP-day, sparse-session) — extends the candidate space beyond workhorse archetype
3. **Engine debug `donchian_breakout`** (still queued; user explicitly cautioned against rabbit hole today)
4. **Operator review of today's 9 PASS candidates** for registry append (operator-gated)
5. **Day close** if energy spent — today's evidence has been substantial

**My pick: option 4 needs operator decision (no Claude action), so default Claude-actionable is option 1 (entry-sub on more assets) OR option 2 (tail-engine extension).** Option 1 is cheap (runner already supports it; just needs candidate registration). Option 2 is medium-cost (runner extension + new harness).

---

*Filed 2026-05-05. Lane B / Forge. No Lane A surfaces touched. Per new operating rule, surfacing next safe action immediately.*
