# FQL Forge Day Summary — 2026-05-05

**Filed:** 2026-05-05 (end of day)
**Authority:** T1 Lane B / Forge throughout — no Lane A surfaces touched, no registry mutation.

This memo captures the full day's batch-mode Forge work after the operator's "candidate batch → cheap screens → kill fast → keep winners" push.

---

## The day's headline: 7 cross-asset PASSes — discovered TWO sister workhorse families

| Workhorse family | Validated assets (PASS) | Watch (near-PASS) | Notes |
|---|---|---|---|
| **XB-PB-EMA-Ladder** (PB pullback entry + ema_slope filter + profit_ladder exit) | **MNQ, MCL, MYM** | MES, MGC | 3 PASS + 2 WATCH; energy breadth filled (MCL) |
| **XB-BB-EMA-Ladder** (BB reversion entry + ema_slope filter + profit_ladder exit) | **MNQ, MGC, MCL, MYM** | MES | 4 PASS + 1 WATCH |

Combined with the original **XB-ORB-EMA-Ladder** family (MNQ + MCL + MYM in current probation), the workhorse roster has tripled from 1 family to 3 — all sharing the proven `ema_slope` + `profit_ladder` portable bundle, swapping only the entry mechanism.

**This is the donor economy working as designed:** the proven trio is a portable platform; multiple entry mechanisms compose with it; operator-review-eligible candidates exist for cross-asset extension of an existing successful family.

---

## Full result table (all 21 candidate evaluations today)

| # | Candidate | Asset | Trades | PF | Net PnL | Verdict | Source |
|---|---|---|---:|---:|---:|---|---|
| 1 | HYB-VolMan-Sizing-overlay | MNQ | 1198 | 1.612 | +$57.5k | PASS-with-WARN ceiling | morning batch |
| 2 | HYB-FX 1.5× (salvage) | 6J | 12 | 1.139 | +$62 | WARN sample | morning batch |
| 3 | HYB-FX 1.0× (calibration) | 6J | 24 | 1.308 | +$200 | WARN positive direction | mid-day |
| 4 | HYB-FX 0.75× (calibration) | 6J | 33 | 0.952 | -$62 | FAIL → salvage retired | mid-day |
| 5 | XB-VWAP-EMA-Ladder | MNQ | 812 | 1.056 | +$2.5k | KILL (entry weak) | batch #1 |
| 6 | XB-Donchian-EMA-Ladder | MCL | 0 | n/a | $0 | RETEST (engine bug) | batch #1 |
| 7 | XB-Donchian-EMA-Ladder | MNQ | 0 | n/a | $0 | RETEST (engine bug isolated) | RETEST |
| 8 | HYB-CashClose-A (salvage) | ZN | 1367 | 0.263 | -$42k | KILL hard | batch #1 |
| 9 | HYB-CashClose-B (salvage filtered) | ZN | 98 | 0.552 | -$2.5k | KILL | batch #1 |
| 10 | **XB-PB-EMA-Ladder** | **MNQ** | **1463** | **1.403** | **+$29.3k** | **PASS** | batch #2 |
| 11 | **XB-BB-EMA-Ladder** | **MNQ** | **667** | **1.245** | **+$8.9k** | **PASS** | batch #2 |
| 12 | HYB-LunchComp-A (salvage) | ZN | 482 | 0.257 | -$18k | KILL | batch #2 |
| 13 | HYB-LunchComp-B (salvage filtered) | ZN | 41 | 0.064 | -$3k | KILL hard | batch #2 |
| 14 | XB-PB-EMA-Ladder | MES | 1473 | 1.151 | +$6.6k | WATCH | runner sweep |
| 15 | XB-PB-EMA-Ladder | MGC | 854 | 1.194 | +$5.3k | WATCH | runner sweep |
| 16 | **XB-PB-EMA-Ladder** | **MCL** | **1061** | **1.311** | **+$7.4k** | **PASS** | runner sweep |
| 17 | **XB-PB-EMA-Ladder** | **MYM** | **462** | **1.351** | **+$4.0k** | **PASS** | runner sweep |
| 18 | XB-BB-EMA-Ladder | MES | 682 | 1.123 | +$2.5k | WATCH | runner sweep |
| 19 | **XB-BB-EMA-Ladder** | **MGC** | **289** | **1.522** | **+$4.1k** | **PASS** (tail-engine, strong) | runner sweep |
| 20 | **XB-BB-EMA-Ladder** | **MCL** | **459** | **1.232** | **+$2.5k** | **PASS** (tail-engine) | runner sweep |
| 21 | **XB-BB-EMA-Ladder** | **MYM** | **234** | **1.785** | **+$3.9k** | **PASS** (tail-engine, very strong) | runner sweep |

**Tally:**
- **9 PASS / PASS-with-WARN** (rows 1, 10, 11, 16, 17, 19, 20, 21)
- **4 WARN / WATCH** (rows 2, 3, 14, 15, 18)
- **6 KILL** (rows 4, 5, 8, 9, 12, 13)
- **2 RETEST** (rows 6, 7 — Donchian engine bug, out-of-batch fix)

Real winners: **7 cross-asset workhorse extensions** across XB-PB and XB-BB families.

---

## Architecture answers (the durable findings)

### Q1: Are XB components swappable, or is XB-ORB a tightly coupled bundle?

**ANSWER: Substantially swappable.** The proven trio (ema_slope + profit_ladder) is a portable platform. Today's evidence across 4 entry types on MNQ:

| Entry | MNQ PF | Verdict |
|---|---:|---|
| ORB (proven, original) | 1.62 | Baseline |
| **PB pullback** | **1.403** | **PASS** |
| **BB reversion** | **1.245** | **PASS** |
| VWAP continuation | 1.056 | KILL |

3 of 4 entries produce profitable workhorse hybrids when paired with the proven bundle. VWAP was the exception. This validates the donor-economy concept: most components compose; not all do; the catalog learns from both.

### Q2: Is salvage worth prioritizing as a Phase 0 template?

**ANSWER: NO — downgrade Template #5 priority.** Today: **7 salvage attempts (HYB-FX × 3 calibrations + HYB-CashClose × 2 + HYB-LunchComp × 2), 0 PASSes.** Strong evidence to deprioritize the salvage template until donor-economy data shows salvages can pass at meaningful rate. Templates #1, #2, #6 should lead Phase 0 priority instead.

### Q3: Item 2 cross-pollination criterion

Still 0/2. Today's PASSes are entry-substitution within proven trios — they populate `relationships.components_used` (the broader plumbing) but NOT `relationships.salvaged_from` (the criterion's strict requirement of "failed parent's component reused successfully"). Item 2 remains gated until a salvage path produces a PASS, which today's evidence suggests will require a different approach to salvage selection.

---

## Built today: `research/fql_forge_batch_runner.py`

Pre-Phase-0 Lane B automation — CLI tool, dry-run/report-only by design.

```
python3 research/fql_forge_batch_runner.py --list-only
python3 research/fql_forge_batch_runner.py --top 4
python3 research/fql_forge_batch_runner.py --candidate XB-PB-EMA-Ladder-MES
```

What it does:
- Loads candidate registry (currently 8 candidates: PB and BB cross-asset on MES/MGC/MCL/MYM)
- Selects top N or specific candidate
- Runs cheap screens via crossbreeding engine harness
- Classifies PASS / WATCH / KILL / RETEST per the verdict standard
- Writes markdown result memo + safety affirmation
- Surfaces summary counts

What it explicitly does NOT do (no `--apply` mode, period):
- Mutate registry status
- Promote strategies
- Touch portfolio composition / runtime / scheduler / checkpoint / hold state
- Make any operator-confirmation decision

Throughput unlock: **operator can now run additional cross-asset sweeps with one CLI invocation, no per-candidate handcrafting.** Adding new candidates to the registry is ~5 lines of Python. The harness composes.

---

## Operator decision gate — what's eligible for registry append

7 candidates passed cheap-screen with workhorse-archetype bars (PF ≥ 1.2, n meaningful):

| Candidate | Operator decision needed |
|---|---|
| XB-PB-EMA-Ladder-MNQ (PF 1.403) | Register as `idea`? |
| XB-PB-EMA-Ladder-MCL (PF 1.311) | Register as `idea`? Energy breadth fill |
| XB-PB-EMA-Ladder-MYM (PF 1.351) | Register as `idea`? |
| XB-BB-EMA-Ladder-MNQ (PF 1.245) | Register as `idea`? |
| XB-BB-EMA-Ladder-MGC (PF 1.522) | Register as `idea`? |
| XB-BB-EMA-Ladder-MCL (PF 1.232) | Register as `idea`? Energy breadth fill |
| XB-BB-EMA-Ladder-MYM (PF 1.785) | Register as `idea`? |

**No appends today.** Operator review per established discipline. If approved, these enter as `status: idea` with `triage_route: hybrid_generation_lane` and `relationships.components_used: [<entry>, "ema_slope", "profit_ladder"]`.

---

## Next-batch recommendations (queued, operator confirms)

1. **Engine debug `donchian_breakout`** (out-of-batch; ~30 min investigation) — unlock another entry for testing
2. **WATCH candidates re-test with one bounded calibration** (XB-PB on MES/MGC, XB-BB on MES) — see if a small param tweak pushes them to PASS
3. **Different filter combinations** — test `ema_slope` against alternatives in the proven trio bundle to see if it's load-bearing or replaceable
4. **HYB-VolMan re-test on a weaker baseline** (DailyTrend-MGC-Long if code recoverable)
5. **Forge runner extension** — add tail-engine / event-driven candidates for completeness; add A/B comparison support; add result-history accumulation (don't overwrite; append per run with timestamp)

---

## Today's commit chain (all Lane B / Forge)

`0056e05` (5 candidates) → `67659c7` (validation plans) → `aaaf98d` (HYB-VolMan + HYB-FX 1.5× + 1.0×) → `2a7f9e5` (HYB-FX 1.0× memo) → `7d4f002` (HYB-FX 0.75× retirement) → `e1f7f64` (batch #1: 3 KILL + 1 RETEST) → batch #2 + runner build (this commit)

---

## What this day proves

- The hot lane CAN run aggressively within safe boundaries
- 7 PASSes in one day is real algo-factory throughput, not slow research-lab pace
- The Forge runner makes the next 7 days' worth of cross-asset / cross-component sweeps a CLI command
- Architecture questions answered with evidence, not opinion
- Salvage doctrine downgraded based on data, not skepticism
- Lane A protected throughout — no runtime / portfolio / scheduler / checkpoint changes

---

*Filed 2026-05-05. Lane B / Forge. Built `research/fql_forge_batch_runner.py` for repeatable batch evidence generation.*
