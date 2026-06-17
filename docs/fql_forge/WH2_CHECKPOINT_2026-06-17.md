# Daily-WH2 Search — Checkpoint — 2026-06-17

> Report-only milestone. The operator pre-declared this checkpoint: "If #T7 and #T12 both die, the conclusion is not 'Forge failed' — the in-house feed universe is probably exhausted for generic daily WH2, and the next unlock is likely Lever-B feeds." That condition is now met. This records the evidence honestly.

## This turn's resolutions
- **#T7 ZN afternoon range-compression release → KILL** (robust): PF 0.05–0.08 across all of ZN/ZF/ZB and 0/6 parameter islands. The afternoon rates break *fails* — rates afternoon is mean-reverting, not expansionary (consistent with the existing ZN-Afternoon-Reversion book). Not a single-island artifact; genuinely dead.
- **#T12 CPI gold↔rates rotation → FEED-BLOCKED** (not testable-now): the in-house CPI calendar carries dates only, no CPI MoM/acceleration values. The inflation-driver mechanism cannot be built without BLS point-in-time CPI values → Lever-B (CPI detail feed).
- **MGC/rates conditioning leads → both fail under scrutiny:**
  - MGC-ORB × rates-up: WEAK_OR_NOISE (single-lookback artifact, killed).
  - MGC-prior_day_break × rates-down: looked robust across lookbacks (91%), but **OOS date-split FALSIFIES it** — the gate INVERTS between halves (2019-22 gated PF 0.98 vs rates-up 1.58; 2023-26 gated PF 2.88 vs 0.65). Full-sample PF 1.94 was recency-driven. **KILLED — not OOS-robust.** The unconditioned MGC-prior_day_break (PF 1.23 train / 1.35 test) is the reliable object; the gate added false confidence.

## Cumulative evidence (in-house feed universe)
| Surface | Result |
|---|---|
| Single-series daily mechanisms (Cycles 1–2, 112 candidates) | only gold-breakout survives (already captured) |
| Breakout family off-MNQ/gold (ORB, donchian, dual-thrust) | all KILL |
| Cross-asset standalone (index dispersion) | sub-gate on long history (PF 1.148) |
| Cross-asset confirmation (gold × rates state) | OOS-falsified / noise |
| Claw lead #T7 (rates afternoon compression) | KILL |
| Claw lead #T12 (CPI rotation) | feed-blocked |

## Honest conclusion (NOT "Forge failed")
The **in-house feed universe is exhausted for a generic daily, non-MNQ, driver-diverse WH2.** This is a strong, evidenced negative — the loop falsified many tempting leads (including two PF artifacts and one OOS inversion) rather than promoting a fake. That is a process win.

## What still stands (durable)
- MNQ daily workhorse (incumbent); gold sleeve (MGC-ORB wired + MGC-prior_day_break unconditioned, additive, prop-OK at 1 micro); FOMC rates + FOMC-MNQ event sleeves; no-lookahead cross-asset harness (reusable).
- True daily WH2 remains **OPEN**.

## Next unlock = Lever-B feeds (operator-supplied)
Ranked (per `LEVER_B_QUEUE_2026-06-16.md`), now reinforced by the backlog triage:
1. **Rates curve/carry/rolldown** (multi-contract/F2) — top daily-WH2 unlock; 35 backlog notes.
2. **Treasury auction calendar** (public Fiscal Data API) — 47 backlog notes, 5 mechanism families.
3. **CPI detail (BLS MoM values)** — unblocks #T12 and inflation-regime rotation.
4. EIA/OPEC inventory; COT positioning; DXY/real-rate.

Continuing report-only: Claw widened harvest (packet upgraded), no-lookahead harness ready for feeds. The high-EV move is now an operator-supplied Lever-B feed. All activation/wiring/registry/portfolio gates remain locked.
