# Calibration Follow-up — WATCH candidates @ stop_mult=1.0× (2026-05-05)

**Filed:** 2026-05-05 (one bounded calibration test per operator's #2 directive)
**Authority:** T1 Lane B / Forge — no Lane A surfaces touched, no registry mutation.

Tested whether the 3 WATCH candidates from today's runner sweep convert to PASS under a tighter stop (stop_mult=1.0× vs default 2.0×).

---

## Result

| Candidate | Asset | Baseline (stop_mult=2.0) | stop_mult=1.0 | Verdict shift |
|---|---|---|---|---|
| XB-PB-EMA-Ladder-MES | MES | PF 1.151, n=1473, +$6.6k, **WATCH** | PF 0.826, n=1473, -$4.5k, KILL | Tighter stops WORSE → WATCH-retain at baseline |
| XB-PB-EMA-Ladder-MGC | MGC | PF 1.194, n=854, +$5.3k, **WATCH** | PF 1.066, n=854, +$1.4k, WATCH (worse) | Tighter stops WORSE → WATCH-retain at baseline |
| XB-BB-EMA-Ladder-MES | MES | PF 1.123, n=682, +$2.5k, **WATCH** | PF 0.930, n=682, -$0.8k, KILL | Tighter stops WORSE → WATCH-retain at baseline |

---

## What this answers

**None of the 3 WATCH candidates converted to PASS via the single bounded test.** All 3 degrade with tighter stops. This is consistent with the existing `xb_orb_stop_sweep_results.json` evidence — stop_mult=2.0× is the validated default for this strategy family.

**Per operator's rule "one bounded calibration each, no broad optimization":** stop here. Don't iterate to stop_mult=3.0 or other params.

**Net classification (final for these 3 today):**
- XB-PB-MES → **WATCH-retain** (baseline PF 1.151 is the right setting; not a PASS, not a KILL)
- XB-PB-MGC → **WATCH-retain** (baseline PF 1.194 is best; closest to PASS line of the three)
- XB-BB-MES → **WATCH-retain** (baseline PF 1.123)

---

## Honest read on these candidates

All three are genuinely borderline, not under-tuned. The strategy bundle (proven trio + entry) produces marginal-positive edges on MES (S&P) and MGC (gold) — the assets where the proven trio has historically been weaker than on MNQ (Nasdaq). MES/MGC may simply be assets where this template has lower prior than MNQ/MCL/MYM.

This is informative about cross-asset extension: the proven trio works, but expected PF varies meaningfully by asset. Asset selection matters as much as component selection.

**Operator decision for these 3:**
- Keep on WATCH list (defer to next checkpoint or future calibration with different params)
- OR retire as borderline (free up donor catalog attention)
- OR test on a different parent component combination (e.g., what if `ema_slope` is replaced — a filter substitution sweep)

---

## What this batch did NOT do

- Stop_mult=3.0 (wider) test — would violate "one bounded calibration each"
- Other parameter changes
- Registry mutation
- Lane A surfaces touched

---

## Next safe Forge actions (queued, operator picks)

1. **Filter substitution sweep** — try alternatives to `ema_slope` in proven trio (vwap_slope, bandwidth_squeeze, session_morning, session_afternoon — all already in crossbreeding engine). Tests whether the proven filter is load-bearing or replaceable. ~30s per candidate via runner. **Same harness; no engine debug needed.**
2. **Tail-engine candidate addition to runner** — current runner only has workhorse archetypes. Adding event-driven / sparse session candidates (e.g., NFP-day variants, cash-close variants) extends the test surface. ~15 min runner extension.
3. **Engine debug `donchian_breakout`** — currently 0 trades on any asset. Would unlock another entry. **CAUTION: per operator, debug work can balloon.** Defer unless obvious quick fix.
4. **Operator review of the 7 morning PASS candidates for registry append** — T2, operator-gated decision, no Claude action needed; pure operator review.

**My pick: option 1** — most leverage today, runner ready, single CLI invocations. Tests architecture question Q1's flip side ("is `ema_slope` filter substitutable like the entries are?"). High information per second.

**Counter-argument for option 4 instead:** the 7 morning PASS candidates are eligible NOW; appending them captures real PASS evidence into the registry, which feeds Item 2's plumbing test. But this is operator decision, not Claude execution.

---

*Filed 2026-05-05. Lane B / Forge. No Lane A surfaces touched.*
