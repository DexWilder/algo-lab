# Tail-Engine Pool Expansion — 2026-05-05

**Filed:** 2026-05-05 (Lane B / Forge — operator's #2 directive after Phase B activation)
**Authority:** T1, no Lane A surfaces touched, no registry mutation.
**Purpose:** Expand candidate pool with tail-engine / sparse-session / asymmetric-payoff variants so the autonomous daily loop can produce diverse evidence rather than re-testing the same neighborhood.

---

## Summary

- **Pool grew 12 → 20 candidates** (added 8 tail-engine variants)
- **Selection rotated** from "first N" to date-cycle (each day picks a different N-window)
- **3 smoke-tested**, 2 produced surprise PASS results
- **All use existing crossbreeding-engine harness** — no new strategy code needed

---

## 8 candidates added

| Candidate | Asset | Gap targeted | Archetype | Harness | Smoke result |
|---|---|---|---|---|---|
| XB-ORB-EMA-MorningOnly-MNQ | MNQ | Sparse-session tail-engine — morning-only orb_breakout | tail | existing (session_morning filter swap) | 1633 trades, PF 1.024, **WATCH** |
| XB-ORB-EMA-AfternoonOnly-MNQ | MNQ | Sparse-session tail-engine — afternoon-only orb_breakout | tail | existing | not yet tested |
| XB-PB-EMA-MorningOnly-MNQ | MNQ | Sparse-session tail-engine — morning-only PB entry | tail | existing | not yet tested |
| XB-BB-EMA-MorningOnly-MGC | MGC | Sparse-session tail-engine — BB on already-PASS asset, morning-restricted | tail | existing | not yet tested |
| XB-BB-EMA-AfternoonOnly-MGC | MGC | Same, afternoon-restricted | tail | existing | not yet tested |
| **XB-ORB-EMA-Chandelier-MNQ** | MNQ | Asymmetric exit — chandelier trailing exit alt | workhorse | existing (chandelier exit swap) | **PASS — PF 1.571** ★ |
| **XB-ORB-EMA-TimeStop-MNQ** | MNQ | Asymmetric exit — fixed time-stop (true tail-engine) | tail | existing | **PASS — PF 1.486** ★ |
| XB-ORB-EMA-MidlineTarget-MNQ | MNQ | Asymmetric exit — midline target | workhorse | existing (midline_target exit swap) | not yet tested |

**No new harness code** — all 8 candidates use the existing `generate_crossbred_signals` engine with parameter swaps. Required only adding a generalized helper `_xb_general(asset, entry, filter, exit, label)` to the runner.

---

## Two surprise architecture findings from smoke tests

### 1. Exit slot is MORE substitutable than the filter slot

Yesterday's filter sweep concluded `ema_slope` is **strongly load-bearing** (alternatives barely better than no filter). Today's smoke tests on exit alternatives flip the picture:

| Exit | PF on MNQ |
|---|---:|
| profit_ladder (proven) | 1.62 |
| **chandelier** | **1.571** (97% of proven) |
| **time_stop** | **1.486** (92% of proven) |

The exit slot tolerates substitution well. Both chandelier and time_stop produce workhorse-archetype PASSes (n=1198, PF >1.4). This is a real correction to the implicit doctrine — only the filter (ema_slope) is truly load-bearing in the proven assembly. Entry and exit are both substitutable, just with narrow sets of high-quality alternatives.

**Revised slot-portability picture:**

| Slot | Substitutability | Best alts |
|---|---|---|
| Entry | YES (narrow) | ORB, PB, BB (3 of 4 tested PASS) |
| Filter | NO (load-bearing) | ema_slope only |
| Exit | YES (narrow) | profit_ladder, chandelier, time_stop (3 of 4 tested produce PASS) |

The proven trio's "load-bearing" component is the filter alone, not the filter+exit pair as I documented yesterday. Updating `project_proven_trio_architecture.md` after this commit.

### 2. Sparse-session restriction doesn't help the workhorse

The morning-only restriction on ORB+ema_slope produced WATCH (PF 1.024) — barely above no-filter control. This suggests the proven trio's edge is NOT concentrated in a particular session window; restricting to morning gives up more good trades than bad ones. **Consistent with yesterday's filter sweep finding** that session-based filters underperform ema_slope as a stand-alone filter.

Tail-engine archetype hypothesis: morning-only ORB might find its edge if paired with a different exit (e.g., time_stop) that doesn't depend on a long hold-period to capture asymmetric payoff. Worth a future test cycle.

---

## Selection rotation logic

The runner's `_select_top()` previously returned `items[:n]` (always the first N). Updated to date-cycle:

```python
days = (date.today() - date(2026, 5, 5)).days  # epoch = activation date
offset = (days * n) % len(items)
selected = items[offset:offset + n]  # wrap on overflow
```

**Practical effect (with current pool of 20 and `--top 5`):**

| Day | Selected window |
|---|---|
| Day 0 (today, 2026-05-05) | XB-PB cross-asset 4 + XB-BB-MES |
| Day 1 (2026-05-06) | XB-BB MGC/MCL/MYM + XB-VWAP MES/MGC |
| Day 2 (2026-05-07) | XB-VWAP MCL/MYM + first 3 sparse-session tail-engines |
| Day 3 (2026-05-08) | last 2 sparse-session + 3 asymmetric-exit |
| Day 4 (2026-05-09) | wraps to start (XB-PB cross-asset 4 + XB-BB-MES) |

**Cycle length: 4 weekdays.** The full pool gets evaluated once per 4-day cycle. Adding more candidates extends the cycle proportionally.

---

## Tonight's 19:00 autonomous fire — what will it run?

**Today is day 0** (epoch = activation date 2026-05-05). The 19:00 fire will select items 0-4 — same 5 candidates as today's manual smoke tests:

- XB-PB-EMA-Ladder-MES (PF 1.151 baseline → expected WATCH)
- XB-PB-EMA-Ladder-MGC (PF 1.194 → expected WATCH)
- XB-PB-EMA-Ladder-MCL (PF 1.311 → expected PASS)
- XB-PB-EMA-Ladder-MYM (PF 1.351 → expected PASS)
- XB-BB-EMA-Ladder-MES (PF 1.123 → expected WATCH)

**Tonight's fire WILL NOT include the new tail-engine candidates** — but tomorrow's (day 1) and especially day 2's will. By Friday end-of-week, all 20 candidates will have been autonomously evaluated at least once.

This is the right behavior — preserves operator's pre-flight verification (which used --top 5 and saw the same first 5 candidates). The new candidates enter the rotation tomorrow.

---

## What this expansion did NOT do

- No registry append
- No promotion of any candidate to `idea` status
- No new strategy code (only runner additions)
- No Lane A surfaces touched
- No change to launchd plist (still --top 5, still weekdays 19:00 local)
- No tripwire changes

---

## Updated runner state

- **Pool size:** 20 candidates (was 12)
- **Helper functions:** added `_xb_general()` for filter/exit configurability; `_xb_swap()` now wraps it for the proven-trio default case
- **Selection:** date-rotated cycle of N=top per day
- **Memory:** `project_proven_trio_architecture.md` needs update after this commit (exit slot is more substitutable than originally characterized)

---

## Next safe Forge actions

| # | Action | Status |
|---|---|---|
| 1 | **Tonight at 19:00 local** — first autonomous fire (selects items 0-4 per rotation) | Autonomous; no Claude action |
| 2 | **Operator review of 11 PASS candidates** for registry append | Pure operator decision; pending since 2026-05-05 morning |
| 3 | **Update memory** — `project_proven_trio_architecture.md` to reflect new exit-slot finding | Cheap; do now |
| 4 | **Smoke-test remaining 5 untested tail-engine candidates** before they hit autonomous rotation | Optional; rotation will catch them anyway |
| 5 | **Engine debug `donchian_breakout`** | Defer (rabbit hole risk) |

**My pick: #3** — update memory with the exit-substitutability finding so it's preserved across sessions. Cheap (~5 min). The rest are either autonomous (tonight) or pure operator decisions.

---

*Filed 2026-05-05. Lane B / Forge. No Lane A surfaces touched. Pool expansion + rotation logic active for tonight's first autonomous fire and forward.*
