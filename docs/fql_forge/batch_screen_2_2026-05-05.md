# Batch Cheap-Screen #2 — 2026-05-05

**Filed:** 2026-05-05 (second batch this session — Lane B / Forge)
**Authority:** T1, no Lane A surfaces touched, no registry mutation.
**Scope:** 3 candidates (4 result rows with HYB-LunchComp A/B). Cheap-screens via `research/scratch/batch_screen_2_2026-05-05.py`.

---

## Result table

| Candidate | Asset | Gap / family | Trades | PF | Net PnL | Max DD | Comparison baseline | Verdict | Architecture learning | Next action |
|---|---|---|---:|---:|---:|---:|---|---|---|---|
| **XB-PB-EMA-Ladder-MNQ** | MNQ | Workhorse / entry-substitution | 1,463 | **1.403** | **+$29,297** | -$1,732 | XB-ORB-MNQ baseline PF 1.62, n=1183 | **PASS** | Proven trio is largely swappable — PB entry works | Cross-asset extension test (MES/MGC/MCL/MYM) |
| **XB-BB-EMA-Ladder-MNQ** | MNQ | Workhorse / entry-substitution | 667 | **1.245** | **+$8,877** | -$2,505 | Same | **PASS** | Reinforces: BB entry also works | Cross-asset extension test |
| **HYB-LunchComp-A impulse-only** | ZN | STRUCTURAL session-transition (rates) — salvage attempt #3 | 482 | 0.257 | -$18,142 | -$18,322 | n/a | **KILL** | Cash-close mini-recreation fails; window-specific edge does not generalize | Retire |
| **HYB-LunchComp-B impulse+lunch-comp** | ZN | Same | 41 | 0.064 | -$3,040 | -$3,001 | A above | **KILL hard** | Lunch-compression filter doesn't rescue the broken mechanism | Retire salvage thread |

---

## Architecture answers (the durable findings)

### Q1: Are the proven XB components swappable, or is XB-ORB a tightly coupled bundle?

**ANSWER: Substantially swappable.** Today's combined entry-substitution evidence:

| Entry | PF | Median trade | Net PnL | Verdict |
|---|---:|---:|---:|---|
| ORB (proven, original) | 1.62 | (registry) | (registry) | Baseline |
| PB pullback | **1.403** | +$7.26 | +$29,297 | **PASS** |
| BB reversion | **1.245** | +$3.26 | +$8,877 | **PASS** |
| VWAP continuation | 1.056 | -$4.49 | +$2,511 | KILL (yesterday) |

**3 of 4 entries produce profitable workhorse hybrids** when combined with `ema_slope` filter + `profit_ladder` exit on MNQ. The proven trio (ema_slope + profit_ladder) IS a portable platform; VWAP was the exception, not the rule.

**Implications for Phase 0:**
- Donor catalog should mark `ema_slope` + `profit_ladder` as **co-validated portable bundle**, not just individual donors
- Entry slot on this bundle accepts multiple entries; not all entries work but most do
- Cross-asset extension is the next logical step — XB-PB-EMA-Ladder and XB-BB-EMA-Ladder on MES/MGC/MCL/MYM should be tested before Phase 0 activation
- The "tightly coupled bundle" concern from earlier batch is REJECTED by this evidence

### Q2: Is salvage worth prioritizing as a Phase 0 template?

**ANSWER: NO. Downgrade Template #5 priority.** Today's salvage attempts (in order):

| Attempt | Hybrid | Result |
|---|---|---|
| 1 | HYB-FX 1.5× (FXBreak salvage + impulse 1.5×) | WARN (sample <30) |
| 2 | HYB-FX 1.0× (same, threshold lowered) | WARN with positive direction |
| 3 | HYB-FX 0.75× (same, threshold lowered again) | FAIL (PF 0.952) |
| 4 | HYB-CashClose-A (Treasury-Cash-Close salvage, no filter) | KILL hard (-$42k) |
| 5 | HYB-CashClose-B (same with impulse filter) | KILL (-$2.5k) |
| 6 | HYB-LunchComp-A (SPX lunch-comp salvage, no filter) | KILL (-$18k) |
| 7 | HYB-LunchComp-B (same with lunch filter) | KILL hard (PF 0.06) |

**7 salvage-template attempts, 0 PASSES.** The pattern is now strong enough to act on: salvage from rejected parents is a low-yield template at this stage. The reasons may include:
- Rejected parents were rejected for substantive reasons; recombining the components doesn't necessarily restore viability
- Salvaged components were likely the "best parts" of broken strategies; pairing with other validated components doesn't compose into a working assembly
- Context-dependence: a component that worked in one parent's context may not work outside that context

**Phase 0 template priority shift (recommended):**
- HIGH PRIORITY: Templates #1 (entry + regime filter), #2 (entry + exit), #6 (sizing overlay + workhorse parent) — today produced 2 PASSes via Template #2/#6 family
- LOWER PRIORITY: Template #5 (parent + salvaged failed-parent component) — until donor-economy evidence shows salvage paths can pass at meaningful rate
- The donors themselves stay catalogued (salvages aren't permanently retired) but the template's expected-value drops based on this evidence

### Q3: Item 2 cross-pollination criterion

Still 0/2. Today's entry-substitution PASSes use proven_donor pairings (the trio), NOT salvaged-from-failed-parent components — so they don't count toward Item 2's specific criterion (which requires a failed parent's component reused successfully). Item 2 remains gated on the salvage path producing a PASS, which today's evidence suggests is unlikely without a different approach.

---

## Updated donor catalog state (post-batch-2)

| Donor | Status update |
|---|---|
| `ema_slope` (proven_donor filter) | Confirmed: portable across multiple entry mechanisms (ORB, PB, BB) |
| `profit_ladder` (proven_donor exit) | Same — portable |
| `pb_pullback` (engine entry) | **NEW PASS** — joins ORB as proven-trio-compatible entry |
| `bb_reversion` (engine entry) | **NEW PASS** — joins ORB as proven-trio-compatible entry |
| `vwap_continuation` (engine entry) | KILL — incompatible with proven trio (single data point but clear) |
| `lunch_compression_regime_filter` (salvaged) | KILL — does not transplant to ZN context |

---

## What this batch did NOT do

- No registry append for the 2 PASSes (operator review required)
- No cross-asset extension yet (MES/MGC/MCL/MYM tests are the obvious next batch)
- No Lane A surfaces touched
- No optimization beyond the entry swap

---

## Files

- Scratch: `research/scratch/batch_screen_2_2026-05-05.py`
- This memo: `docs/fql_forge/batch_screen_2_2026-05-05.md`

---

*Filed 2026-05-05. Lane B / Forge. Building Forge batch runner next per operator direction.*
