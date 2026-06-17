# Daily Workhorse #2 — Ranked Board — 2026-06-16

> Report-only. Result of the targeted WH2 campaign (`forge_cycle_2026-06-16n/o`): cross-asset the winning `prior_day_break` mechanism + two new MGC mechanisms, every candidate through the same board incl. correlation to BOTH MNQ workhorses + cadence tiering + registry dedup. No vanity grids, no MNQ-cousin promotion, no mutation/activation.

## Headline findings
1. **`prior_day_break` is GOLD-SPECIFIC — it does not generalize.** Cross-asset on the proven recipe KILLs everywhere except MGC (MYM 1.32, MES 1.15, M2K 1.17, 6E 1.07, MCL 0.94, ZN 0.94, ZF 0.81 — all fail quality gates). The diversifier is the *(gold × prior_day_break)* pairing, not a portable mechanism.
2. **The strongest board line, MGC `orb_breakout`, is NOT a new find — it already exists** as `XB-ORB-EMA-Ladder-MGC` (probation, wired 2026-05-28; registry PF 1.601, n=652). My campaign re-derived its backtest. It's the gold member of the ORB-Ladder family already on the books, awaiting its 30-forward-trade gate.
3. **MGC `prior_day_break` is the one genuinely NEW engine** — and it's **additive** over the existing MGC-ORB book (mutual daily-PnL corr **+0.244**, < 0.3). Mechanism-distinct (prior-day level, not opening range), decorrelated from both MNQ workhorses (+0.06 / −0.04).
4. **No true-daily WH2 found; no non-gold, non-MNQ diversifier found.** Every survivor is weekly-frequent gold.

## Ranked board

### TRUE-DAILY candidates (≥120 trades/yr & n≥500)
- **None.** The hunt has not yet produced a true daily second engine.

### WEEKLY-FREQUENT diversifiers (decorrelated from MNQ; gold)
| Candidate | New? | n | trades/yr | PF | H1/H2 | top3/5/10 | max-DD dur | corr→MNQ | verdict |
|---|---|---:|---:|---:|---|---|---:|---:|---|
| **MGC `prior_day_break`** | **NEW, additive (+0.24 vs MGC-ORB)** | 405 | 50.6 | 1.34 | 1.32/1.35 | 14.4/18.8/28.6 | 128 | +0.06/−0.04 | **FORWARD_CLOCK_CREDIBLE** |
| MGC `orb_breakout` | EXISTING book (XB-ORB-EMA-Ladder-MGC, probation) | 656 | 82.0 | 1.50 | 1.42/1.54 | 8.4/11.3/17.5 | 142 | +0.10/+0.07 | already wired; re-confirmed |

### SPARSE event engines (separate track, mapped earlier)
- ZN/ZF-FOMC rates sleeve (regime-gated), FOMC-MNQ-1h. Not workhorses.

### KILL / archive (this batch)
- `prior_day_break` on MYM, MES, M2K, MCL, ZN, ZF, 6E — mechanism gold-specific.
- MGC `abnormal_range_followup` — PF 0.59, dead on gold.

## The honest caveat: gold crowding
The WH2 hunt keeps surfacing **gold** because `prior_day_break` is gold-specific and ORB-gold already exists. MGC now carries 4 books (ORB-MGC-Long core, PB-MGC-Short core, DailyTrend-MGC-Long probation, XB-ORB-EMA-Ladder-MGC probation) — the registry already flags an "MGC strategy soft cap." Adding `prior_day_break` would be a **5th gold book**. Even though it decorrelates from the others, this risks solving "diversify away from MNQ" by **over-concentrating in MGC**. A second daily engine on a genuinely different *driver* (rates, FX, crude, vol) — not just a different mechanism on gold — remains the real unmet mission goal.

## Recommendation
- **Bank MGC `prior_day_break`** as a forward-clock-credible, additive gold diversifier (Track 2 EXPERIMENTAL) — but weigh it against the MGC soft cap before it earns a forward-clock slot. It is not the true daily WH2.
- **The non-gold daily-engine gap is now empirically confirmed**: current-data mechanisms (ORB, prior-day, abnormal-range, mean-reversion, vol, gap, afternoon, FX-session) do not yield a non-MNQ, non-gold daily workhorse. Like the FOMC vein, the next real expansion likely needs a **new input** (Lever-B: carry/curve/COT for a structural daily engine), not more current-data grids.

## Boundaries
Report-only. No activation, no wiring, no registry/scheduler/portfolio mutation. No retune.
