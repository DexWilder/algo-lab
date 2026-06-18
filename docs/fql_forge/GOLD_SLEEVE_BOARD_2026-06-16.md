# Gold Sleeve Board — 2026-06-16

> Kept separate from the WH2 mission. The gold sleeve is useful and real; **gold crowding is now a governance issue** and must not consume the daily-WH2 hunt. Report-only; no activation/wiring/registry mutation. Evidence: `forge_cycle_2026-06-16n/o` + combined-sleeve computation 2026-06-16.

## Members
| Member | Status | n | PF | net | mechanism |
|---|---|---:|---:|---:|---|
| **MGC-ORB** (XB-ORB-EMA-Ladder-MGC) | probation, **wired 2026-05-28** | 656 | 1.495 | $9,835 | opening-range breakout |
| **MGC-prior_day_break** | NEW candidate (Track 2, forward-clock-credible) | 405 | 1.341 | $5,820 | prior-day structural break |
| (also in MGC: ORB-MGC-Long core, PB-MGC-Short core, DailyTrend-MGC-Long probation) | | | | | |

## Combined sleeve (MGC-ORB + MGC-prior_day_break, 1 micro each)
- **Overlap:** fire same-day only **226 days = 27% of the union** → mostly independent timing.
- **Mutual daily-PnL correlation: +0.244** → additive (confirmed, < 0.3).
- **Combined:** net **$15,654**, PF **1.464**.
- **Max-DD / DD-duration:** ORB −$1,022 / 142d · PDB −$2,314 / 127d · **COMBINED −$2,277 / 236d**. Combining slightly *reduces* peak DD (vs PDB alone) but **lengthens** the underwater stretch (236 days) — the diversification offsets depth, not duration.
- **Worst single day:** ORB −$526 · PDB −$1,363 · **COMBINED −$1,363** vs sum-of-individual-worst −$1,889 → diversification helps (worst days don't coincide).
- **Prop (1 micro each):** combined worst day −$1,363 vs ~$2,000 Tradeify daily-DD guard → **OK** at 1-micro sizing.

## Verdict
A genuinely **additive, prop-compatible gold sleeve** at 1-micro sizing. MGC-prior_day_break is worth a forward-clock slot as the additive member — **subject to MGC soft-cap treatment**.

## MGC soft-cap treatment (governance)
MGC already carries ORB-MGC-Long (core), PB-MGC-Short (core), DailyTrend-MGC-Long (probation), XB-ORB-EMA-Ladder-MGC (probation). The registry flags an **MGC strategy soft cap**. Adding prior_day_break = a **5th gold book**. Rules:
- Even though members decorrelate from each other, they share **gold-driver beta** — total MGC exposure is a single-asset concentration risk at the portfolio level ([[feedback_concentration_is_load_bearing]], [[feedback_asset_family_saturation_rule]]).
- **Do not let the gold sleeve substitute for the WH2 mission.** A frequent gold engine ≠ a true daily second engine on a new driver. The WH2 hunt stays open.
- Before any gold addition: size the *combined* gold-sleeve exposure as one concentration unit; prefer to cap total gold books rather than add freely.

## Caveat
The repeated surfacing of gold in the WH2 hunt is a *symptom*: off-MNQ daily-elite edge in current single-series data is concentrated in gold-breakout. The cure is a new *driver* (Lever-B rates-curve/carry, dollar/real-rate), not more gold mechanisms.

## DEEP-REVIEW UPDATE (2026-06-17, cycle 17n) — MGC-prior_day_break addition, same rigor as the fip kill
Applied the per-year-stability + bad-day-offset + distinctness rigor (that downgraded MNQ first_impulse_pullback) to MGC-prior_day_break as a gold-sleeve addition vs incumbent MGC-ORB. **It comes out genuinely different from fip — it survives, but as a RETURN addition, not a risk-reducer:**
- **Distinctness PASSES** (fip failed this): same-day overlap **34.5%** (fip 87%), overall corr **0.244** (fip 0.43), different entry-hour spread, different mechanism (prior-day level vs opening range). A real separate gold edge.
- **Adds return:** sleeve net $9,835 → $15,654 (+$5,819); combined PF 1.464.
- **NOT a risk-reducer:** combined DD deepens −$1,022 → −$2,277 (worse in **7/8 years**); pdb does NOT offset ORB's worst days (10–12% positive). Expected — it's added exposure, not a hedge.
- **Prop-acceptable combined:** worst day −$1,363 (< $2k); pdb cost-robust (PF 1.34→1.24 @3x slip).

**Verdict: `ADDITION_CANDIDATE` (distinct return-adding gold mechanism) — NOT a risk-reducer, NOT WH2.** Stronger than fip (which was REDUNDANT + a 2025 artifact → dead); pdb is genuinely additive in return + diversity. **The binding gate is GOLD CONCENTRATION** — pdb would be a 5th MGC book; a sleeve-additive return book still deepens portfolio-level gold exposure (MGC soft-cap). So: real candidate, gated on the gold-concentration / soft-cap decision (operator), not promotable until resolved. Honest framing: this expands the gold sleeve's return via a distinct mechanism; it does not solve diversification or reduce risk.

## Boundaries
Report-only. No activation, wiring, registry/portfolio mutation, or retune.
