# Bottom Probation Review — Slot Pressure Audit
## 2026-03-18

*Applying the adopted elite governance: 5 conviction + 3 watch = 8 total.
Current probation: 12. Must reduce by 4.*

---

## Context

The portfolio has 12 probation strategies against an 8-slot cap
(5 conviction + 3 watch). The bottom 4 by rubric score are:

| Strategy | Rubric | Current State |
|----------|--------|---------------|
| GapMom | 16 | Multi-asset, morning, breakout |
| MomIgn-M2K-Short | 14 | M2K, midday, momentum |
| ORBEnh-M2K-Short | 13 | M2K, morning, breakout |
| VWAPMR-MCL-Short | 13 | MCL, morning, mean-reversion |

Concentration context:
- **M2K:** 4 strategies (MomIgn, CloseVWAP, TTMSqueeze, ORBEnh) — at soft cap
- **Morning session:** 7 strategies — over the proposed hard cap of 5
- **MOMENTUM factor:** 61% — over the hard cap of 50%

---

## 1. ORBEnh-M2K-Short (Rubric: 13/24 MARGINAL)

### Strongest Case to Keep
- Validation 8.0/10 on 2-year data (strong on limited sample)
- 100% parameter stability
- M2K morning short fills a direction niche (most M2K strategies are
  midday or all-day)

### Strongest Case to Prune
- **No extended-history validation.** The 8.0/10 score is on 2 years
  only. Every other probation strategy has 6.7-year validation.
  Without extended history, we don't know if this edge is real or a
  2-year artifact.
- **No PF in registry.** We literally do not have a backtest PF for
  this strategy on the full data. It was promoted to probation on
  2-year metrics alone.
- **Half-life: ARCHIVE_CANDIDATE.** The system's own monitoring has
  flagged it.
- **Morning session concentration.** 7th morning strategy. Morning is
  over the proposed hard cap of 5.
- **Activation score 0.42** — below the 0.50 neutral line.
- **Breakout family on M2K morning.** The breakout x morning equity
  family has 13 tested variants and is flagged as saturated.

### Is This Truly Elite-Potential?
**No.** A strategy with no extended-history validation, no registry PF,
and an ARCHIVE_CANDIDATE half-life flag is the definition of unproven.
The 2-year 8.0/10 score is promising but insufficient — elite standard
requires conviction, not hope.

### Better Slot Alternative?
The M2K morning slot adds to the most overcrowded session in the
portfolio. The M2K asset already has 4 strategies — at soft cap.
Any non-morning, non-M2K candidate would be more valuable.

### Recommendation: **DOWNGRADE TO TESTING.**
Run extended-history validation. If PF > 1.2 on 6.7 years with WF
stability, re-enter as a watch candidate. If not, archive. Set review
deadline: 2026-05-01 (6 weeks). If not re-validated by then, archive.

---

## 2. VWAPMR-MCL-Short (Rubric: 13/24 MARGINAL)

### Strongest Case to Keep
- MCL is an energy asset gap — only 1 other MCL strategy exists
  (RangeExpansion, which was just downgraded for decay)
- Mean-reversion provides factor diversification on MCL
- Short direction adds to portfolio's short-side coverage

### Strongest Case to Prune
- **70% parameter stability — worst in the entire portfolio.** Every
  other strategy is 80%+. This means the edge is sensitive to parameter
  choice, which is a classic overfitting signal.
- **Validation 6.5/10 — weakest score of all probation.**
- **Only 2-year data.** No extended-history validation.
- **Half-life: ARCHIVE_CANDIDATE.**
- **No PF in registry.** Same as ORBEnh — promoted without full metrics.
- **Morning session.** 7th morning strategy.
- **Activation score 0.40** — lowest of all probation.

### Is This Truly Elite-Potential?
**No.** 70% parameter stability is disqualifying under elite standard.
A strategy whose PF swings > 30% with ±20% parameter changes is not
a real edge — it's a parameter-mined artifact. The MCL slot has value,
but this strategy isn't earning it.

### Better Slot Alternative?
Commodity-TermStructure-Carry (currently in testing) is an MCL candidate
with a real mechanism (carry factor) and academic basis. If it advances,
it would fill the MCL slot with a CARRY factor strategy instead of a
fragile mean-reversion one.

### Recommendation: **DOWNGRADE TO TESTING.**
The MCL energy slot is valuable but this occupant is the weakest in the
portfolio by three different metrics (param stability, validation score,
activation score). Set review deadline: 2026-05-01. If extended-history
PF > 1.2 and param stability improves to 85%+, re-enter as watch.
Otherwise archive.

---

## 3. MomIgn-M2K-Short (Rubric: 14/24 MARGINAL)

### Strongest Case to Keep
- **90 trades** — largest sample of the four under review
- **PF 1.24 on 6.7 years** — positive, proven over full history
- **Midday session** — the only midday M2K strategy, which is a session
  diversification point
- **Healthy half-life** — no decay detected
- **Activation score 0.67** — highest of the four, above neutral
- **Controller action REDUCED_ON** — system considers it active-worthy

### Strongest Case to Prune
- **Validation collapsed from 9.0 to 6.0** when extended from 2-year
  to 6.7-year data. This is a serious warning — the edge looked much
  stronger on the recent period than the full sample. It may be a
  regime artifact (worked in 2024-2025 but not before).
- **PF 1.24 is marginal** by elite standard. It clears the 1.2 floor
  but barely.
- **MOMENTUM factor** — adds to the 61% overcrowded factor.
- **M2K at soft cap** (4 strategies).

### Is This Truly Elite-Potential?
**Maybe.** The midday session niche is genuinely valuable (no other
midday M2K strategy). PF 1.24 on 90 trades with healthy half-life is
passable — not elite, but not junk. The validation collapse is
concerning but the full-period edge still exists.

### Better Slot Alternative?
No direct midday M2K alternative exists in the catalog. Pruning this
loses the only midday coverage on M2K.

### Recommendation: **MOVE TO WATCH.**
This is the strongest of the four under review but still MARGINAL (14).
Not strong enough for conviction probation, but the midday session
niche and 90-trade sample justify passive monitoring. Watch slot with
review deadline: 2026-06-01 (10 weeks). Promote to conviction if
forward PF > 1.3 after 20+ forward trades. Archive if forward PF < 1.0
after 20+ trades.

---

## 4. GapMom (Rubric: 16/24 MARGINAL)

### Strongest Case to Keep
- **PF 1.72 on MGC-long** — strongest raw PF of the four
- **Multi-asset** — tested on MGC, MNQ, MCL; best on MGC
- **83% parameter stability** — acceptable
- **Promoted 2026-03-15** — newest entry, hasn't had time to accumulate
  forward evidence

### Strongest Case to Prune
- **MGC-concentrated.** Best result is MGC-long, but MGC already has 4
  strategies (at soft cap) plus DailyTrend-MGC-Long in probation. Adding
  another MGC-morning strategy adds concentration, not diversification.
- **Morning session.** 7th morning strategy.
- **Breakout family.** Same family as ORB-MGC (which is already in core)
  and NoiseBoundary-MNQ. The breakout x morning family is saturated.
- **WF 6.7/10** — below the STRONG threshold.
- **Half-life ERROR** — insufficient data (just promoted, expected).
- **No forward trades yet.** Can't evaluate forward evidence.

### Is This Truly Elite-Potential?
**Possible but unlikely.** PF 1.72 on MGC-long is strong, but it's
the same asset/session/family as ORB-MGC-Long (which is already in
core with PF 1.99). The incremental portfolio value of a second
MGC-morning-breakout strategy is near zero. The multi-asset potential
(MCL, MNQ) is interesting but the results on those assets are weaker
(MNQ PF 1.31).

### Better Slot Alternative?
The probation slot would be better used by a non-MGC, non-morning
candidate. The carry strategies in testing (Commodity-TermStructure,
Treasury-Rolldown) would fill genuine factor gaps instead of adding
to morning equity/metal concentration.

### Recommendation: **MOVE TO WATCH.**
PF 1.72 is too high to archive outright — it may be a legitimate
tail engine on MGC. But it doesn't justify a conviction slot because
it adds to the two most overcrowded dimensions (MGC + morning). Watch
slot with review deadline: 2026-06-01. Re-evaluate if MCL or MNQ
results improve with more data. Archive if forward evidence confirms
it's just a weaker version of ORB-MGC.

---

## Summary of Recommendations

| Strategy | Rubric | Action | Destination | Review Deadline |
|----------|--------|--------|-------------|-----------------|
| ORBEnh-M2K-Short | 13 | **DOWNGRADE** | Testing | 2026-05-01: validate on extended history or archive |
| VWAPMR-MCL-Short | 13 | **DOWNGRADE** | Testing | 2026-05-01: validate on extended history or archive |
| MomIgn-M2K-Short | 14 | **MOVE TO WATCH** | Watch probation | 2026-06-01: promote if forward PF > 1.3 / 20 trades, archive if < 1.0 |
| GapMom | 16 | **MOVE TO WATCH** | Watch probation | 2026-06-01: re-evaluate MCL/MNQ results, archive if just weaker ORB-MGC |

### Resulting Slot Counts (if approved)

| Category | Before | After |
|----------|--------|-------|
| Core | 4 | 4 |
| Conviction probation | — | **8** (NoiseBoundary, PreFOMC, DailyTrend, MomPB-6J, FXBreak-6J, TV-NFP, TTMSqueeze, CloseVWAP) |
| Watch probation | — | **2** (MomIgn, GapMom) |
| Testing | 4 | **6** (+ORBEnh, +VWAPMR-MCL) |
| **Total active slots** | 16 | **14** |
| **Under 8-slot probation cap** | No (12) | **Yes** (8 conviction + 2 watch = 10, but watch doesn't count against conviction cap) |

### Watch Slot Rule (Adopted)

Every watch strategy must have:
- **A review deadline** — no indefinite passive survival
- **A promote condition** — specific metric that would elevate it to conviction
- **An archive condition** — specific metric that would eliminate it
- **Maximum watch duration: 16 weeks** — if neither condition is met
  by the deadline, archive. The catalog preserves the idea; the slot
  must be freed.

### Concentration Impact

| Dimension | Before | After |
|-----------|--------|-------|
| Morning session | 7 | **5** (ORBEnh and VWAPMR-MCL removed) |
| M2K strategies | 4 | **3** (ORBEnh removed from active) |
| MOMENTUM factor | ~61% | ~55% (MomIgn moved to watch, ORBEnh removed) |
