# Carry Candidate Displacement Check — 2026-03-18

*Standing rule: every candidate at TESTED or VALIDATION_PASS gets a
displacement analysis. Both carry candidates are at TESTED stage.*

---

## Candidate 1: Commodity-TermStructure-Carry-EnergyMetals

### Rubric Score (Estimated at TESTED Stage)

| Q | Score | Reasoning |
|---|-------|-----------|
| Q1. Mechanism | 3 STRONG | Academic basis (Erb & Harvey, Koijen et al.), but signal is PROXY (60-day return conflates carry with momentum). Real mechanism, noisy signal. |
| Q2. Durability | 2 MARGINAL | MGC dominates PnL. 2025 gold rally is ~70% of returns. MCL is marginal (PF 1.15). MGC-only edge, not a broad commodity carry effect. |
| Q3. Best in family | 3 STRONG | Only commodity carry strategy with code and data. Best representative by default. |
| Q4. Portfolio fit | 4 ELITE | Fills CARRY factor gap (0 active). Fills commodity asset diversity. Different horizon (monthly). Correlation near zero with equity/FX strategies. |
| Q5. Evidence | 2 MARGINAL | batch_first_pass = SALVAGE (not ADVANCE). MGC PF 3.23 but asset-concentrated. MCL fails. Proxy conflation unresolved. |
| Q6. Worth attention | 3 STRONG | Fills the single biggest factor gap. Even marginal carry is more valuable than another momentum strategy. Carry lookup v2 (front/back data) could transform this. |
| **Total** | **17/24 MARGINAL+** | |

### Displacement Check

**Check 1: Core — PB-MGC-Short (16/24)**
- Candidate scores 17 vs incumbent 16. Marginal advantage.
- BUT: candidate is SALVAGE classification (not ADVANCE). PB-MGC is
  proven core with 6+ years of backtest. Candidate has no forward evidence.
- **Verdict: Does not displace core yet.** Needs ADVANCE classification
  or forward evidence to justify replacing a sitting core strategy.

**Check 2: Watch — MomIgn-M2K-Short (14/24)**
- Candidate scores 17 vs MomIgn 14. Clear advantage (+3 points).
- Candidate fills CARRY gap (MomIgn is MOMENTUM, overcrowded factor).
- With +2 gap bonus: effective 19 vs 14.
- **Verdict: WOULD displace MomIgn for a watch slot** if watch has room
  or MomIgn expires. Currently watch is 5/3 (over cap), so this becomes
  actionable at MomIgn's 2026-06-01 deadline if MomIgn fails its promote
  condition.

**Check 3: Gap Value**
- Fills CARRY factor gap: YES (0 active, 0 conviction, 0 watch)
- Fills MCL asset gap: Partially (MCL result is weak, MGC is strong)
- Fills session gap: No (daily close, already covered by DailyTrend-MGC)
- Gaps filled: 1 (CARRY)
- Gap bonus: +2

### Current Assessment

**Not ready for displacement yet.** SALVAGE classification and proxy
conflation mean the signal quality hasn't been proven. But the CARRY
gap-fill value is so high that this candidate should be tracked closely.
The next decision point is:
- If salvage attempt (true carry signal via v2 data) produces ADVANCE → enters conviction directly (rubric would jump to ~20 with real signal)
- If proxy version produces forward PF > 1.2 on MGC → enters watch, displaces MomIgn

---

## Candidate 2: Treasury-Rolldown-Carry-Spread

### Rubric Score (Estimated at TESTED Stage)

| Q | Score | Reasoning |
|---|-------|-----------|
| Q1. Mechanism | 3 STRONG | Academic basis (Butler & Butler, Koijen et al.). Carry lookup provides real directional signal. Spread construction is sound (corr 0.027 with rates direction — genuinely neutral). |
| Q2. Durability | 2 MARGINAL | Equal variant: positive in 4/7 years, but 2025-2026 strongly negative (-$15K). Not durable across full sample. ZF/ZB pair drives all profit (52% of trades). |
| Q3. Best in family | 4 ELITE | Only rates carry strategy in the entire catalog. No competition. |
| Q4. Portfolio fit | 4 ELITE | Fills CARRY factor gap (0 active). Fills RATES asset gap (0 active). Different horizon (monthly). Spread = near-zero beta to equities/FX/commodities. Two gaps filled simultaneously. |
| Q5. Evidence | 2 MARGINAL | PF 1.11 (equal) / 1.10 (DV01) on 79 trades. Marginal by elite standard. Not ADVANCE-level. 2025-2026 weakness is concerning. |
| Q6. Worth attention | 3 STRONG | Fills two gaps simultaneously (CARRY + rates). Even weak carry on rates is more diversifying than strong momentum on equities. Validates the carry lookup unlock. |
| **Total** | **18/24 STRONG** | Gap bonus (+2 for 2 gaps) → effective **20** in displacement |

### Displacement Check

**Check 1: Core — PB-MGC-Short (16/24)**
- Candidate scores 18 (effective 20 with gap bonus) vs incumbent 16.
- Candidate fills 2 gaps (CARRY + rates) that PB-MGC doesn't fill.
- BUT: PF 1.11 is marginal. PB-MGC has PF 2.36 (though on 9 trades).
- **Verdict: Arguable.** Raw rubric favors the candidate. But PF 1.11
  doesn't inspire confidence for core deployment. This is a "promote
  to conviction first, then challenge core" path — not a direct jump.

**Check 2: Watch — MomIgn-M2K-Short (14/24)**
- Candidate scores 18 (effective 20) vs MomIgn 14. Decisive advantage.
- **Verdict: WOULD displace MomIgn immediately** for a watch slot. But
  at rubric 18, this actually qualifies for conviction probation, not
  just watch.

**Check 3: Gap Value**
- Fills CARRY factor gap: YES (0 active)
- Fills Rates asset gap: YES (0 active)
- Fills session gap: No
- Gaps filled: **2** (CARRY + Rates) — the two biggest portfolio gaps
- Gap bonus: +2

### Current Assessment

**Closest candidate to earning a slot.** Rubric 18 meets the conviction
threshold. With gap bonus, effective 20. Fills the two biggest gaps in
the portfolio simultaneously. The concern is PF 1.11 — marginal by
elite standard.

The honest framing: this strategy is valuable for WHAT IT IS (first
carry + first rates) more than for HOW MUCH IT EARNS (PF 1.11). Under
the portfolio construction policy, a strategy that fills 2 factor/asset
gaps at PF 1.1 is more portfolio-valuable than a strategy that adds to
morning momentum at PF 1.5.

**Next decision point:** If the equal-notional variant shows stable
forward PnL over 3+ months, it qualifies for conviction entry. The
2025-2026 weakness must be monitored — if it's a regime artifact that
resolves, the strategy is genuinely strong. If it's a secular decline,
the APPROXIMATE signal may not be good enough.

---

## Roster-Upgrade Summary

### Closest to Displacing an Incumbent

**Treasury-Rolldown-Carry-Spread** is closest. Rubric 18 (meets conviction
threshold), fills 2 gaps (CARRY + Rates), effective score 20 with gap
bonus. The bottleneck is PF 1.11 and the 2025-2026 weakness — forward
evidence would resolve this.

### Incumbent Under Most Pressure

**MomIgn-M2K-Short (watch, 14/24)** is under the most pressure. It's the
weakest active strategy by rubric score, in the most overcrowded factor
(MOMENTUM), on an asset that already has 3 active strategies (M2K), and
its validation collapsed from 9.0 to 6.0 on extended data. Both carry
candidates would displace it. Its 2026-06-01 deadline is the natural
expiry point.

**PB-MGC-Short (core, 16/24)** is under secondary pressure. It's the
weakest core strategy, but displacement requires a candidate that's both
stronger AND has forward evidence — neither carry strategy has forward
evidence yet. PB-MGC is safe until a conviction strategy earns promotion.

### Next Highest-Leverage Replacement Battle

**Treasury-Rolldown-Carry-Spread vs MomIgn-M2K-Short** for a watch slot
at the 2026-06-01 deadline. If Treasury-Rolldown accumulates even modest
forward evidence (any positive PnL on the spread), it replaces a decaying
MOMENTUM strategy with a new CARRY + Rates strategy. This single swap:
- Opens the first CARRY factor position in the portfolio
- Opens the first Rates asset position in the portfolio
- Removes one MOMENTUM strategy from the overcrowded factor
- Reduces M2K concentration by 1

This is the highest-leverage roster move available. The background engine
should continue accumulating evidence on both carry candidates while the
watch deadline approaches.
