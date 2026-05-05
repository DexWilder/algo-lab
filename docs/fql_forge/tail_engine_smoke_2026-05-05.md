# Tail-Engine Smoke Test — Remaining 5 Candidates (2026-05-05)

**Filed:** 2026-05-05 (Lane B / Forge — operator's #3 directive)
**Authority:** T1, no Lane A surfaces touched, no registry mutation.

---

## Result table

| Candidate | Trades | PF | Net PnL | Verdict | Harness | Keep in rotation? |
|---|---:|---:|---:|---|---|---|
| XB-ORB-EMA-AfternoonOnly-MNQ | 1,637 | 1.068 | +$7,100 | **WATCH** | OK | yes |
| XB-PB-EMA-MorningOnly-MNQ | 2,058 | 1.074 | +$8,755 | **WATCH** | OK | yes |
| XB-BB-EMA-MorningOnly-MGC | 486 | 0.989 | -$208 | **KILL** | OK | **REMOVE** (consistent KILL; wastes future cycles) |
| **XB-BB-EMA-AfternoonOnly-MGC** | **376** | **1.207** | **+$1,783** | **PASS** ★ tail-engine | OK | yes |
| XB-ORB-EMA-MidlineTarget-MNQ | 1,198 | 1.085 | +$2,413 | **WATCH** | OK | yes |

**No harness issues** — all 5 ran cleanly via existing crossbreeding engine, no errors, no NaN metrics.

---

## Findings

### 1. New PASS: XB-BB-EMA-AfternoonOnly-MGC (PF 1.207)

The BB-MGC-afternoon-restricted variant produces a tail-engine PASS — adds a 14th candidate to today's PASS list. Notably, the **morning-restricted version (XB-BB-EMA-MorningOnly-MGC) was a clean KILL** (PF 0.989). This means BB-MGC's edge is **afternoon-concentrated**, not all-day or morning.

Architecture micro-finding: session matters for BB+MGC specifically. May not generalize — different entry/asset combinations may have different optimal sessions.

### 2. Midline target is the weak exit alternative

| Exit alt | MNQ PF |
|---|---:|
| profit_ladder (proven) | 1.62 |
| chandelier | 1.571 |
| time_stop | 1.486 |
| **midline_target** | **1.085** ← clear weak |

The midline_target exit underperforms by ~0.4 PF compared to the other three. Not a clean KILL but clearly the weak-of-class. Aligns with the entry-substitution finding that VWAP was the entry-alt outlier — each slot tolerates a few good alternatives, not all alternatives.

### 3. Sparse-session restrictions on the proven trio underperform

XB-ORB and XB-PB with morning-only or afternoon-only filters all produced WATCH (PF 1.068-1.074). Consistent with yesterday's filter sweep finding: ema_slope is the load-bearing filter; layering session restrictions on top of (or replacing) ema_slope reduces edge without filtering the right trades.

---

## Recommendation: prune one candidate

**XB-BB-EMA-MorningOnly-MGC** is a structural KILL (PF 0.989, near-break-even, would just reproduce KILL on every rotation visit). Recommend removing from runner pool to avoid wasting future autonomous cycles. Evidence is preserved in this memo and git history.

The other 4 (3 WATCH + 1 PASS) stay in rotation — WATCH evidence is informative for the autonomous loop's longer-term pattern detection.

---

## Updated PASS roster for today

Adding the 2 new PASSes from the smoke tests this afternoon to the morning's 11:

**14 PASS candidates today:**
- 11 from morning batches (XB-PB / XB-BB cross-asset + HYB-VolMan)
- 1 from earlier smoke test (XB-ORB-EMA-Chandelier-MNQ, PF 1.571)
- 1 from earlier smoke test (XB-ORB-EMA-TimeStop-MNQ, PF 1.486)
- 1 from this batch (XB-BB-EMA-AfternoonOnly-MGC, PF 1.207)

The 14 PASS candidates span:
- 3 entry types (ORB, PB, BB) — entry portability confirmed
- 5 assets (MNQ, MES, MGC, MCL, MYM) — cross-asset coverage broad
- 3 exit types (profit_ladder, chandelier, time_stop) — exit alternatives confirmed
- 2 session profiles (all-day workhorse, afternoon-restricted tail-engine)

---

## Next safe Forge actions

| # | Action | Cost | My pick |
|---|---|---|---|
| 1 | **Prune XB-BB-EMA-MorningOnly-MGC from runner** | ~1 min code change | quick housekeeping; do now |
| 2 | **Prepare batch register pre-flight for today's PASS roster (14 candidates now, not 11)** | 30-60 min | High value — the value-capture move operator queued earlier |
| 3 | **Add more asymmetric-exit variants** — chandelier+PB+MES, time_stop+BB+MGC, etc. | ~10 min runner extension + ~3 smoke runs | Confirmed-strong family worth extending; cheap |
| 4 | **Engine debug `donchian_breakout`** | unknown | Defer (rabbit hole) |

**My pick: do #1 immediately (housekeeping), then #2 (register pre-flight).** #2 has been pending all day, today's evidence has compounded substantially (12 morning PASSes → 14 PASSes), and the register pre-flight per operator's earlier spec converts the evidence into durable registry structure.

#3 is a strong follow-up but has lower marginal value than capturing the existing winners.

---

*Filed 2026-05-05. Lane B / Forge. No Lane A surfaces touched. Surfacing next action immediately per operating rule.*
