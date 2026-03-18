# Integrated Quality-Pressure Review — 2026-03-18

*First combined review using all three elite robustness tools:
Replacement Scoreboard + Forward Counterfactual + Edge Vitality Monitor.*

---

## Most Vulnerable Strategies Right Now

### 1. TV-NFP-High-Low-Levels — FADING VITALITY, CONVICTION SLOT AT RISK

| Tool | Signal | Detail |
|------|--------|--------|
| Vitality | **FADING (0.260)** | Half-life ARCHIVE_CANDIDATE. Lowest vitality in entire portfolio. |
| Scoreboard | Conviction slot, rubric 18 | At the minimum threshold. One point lower and it drops to watch. |
| Counterfactual | Not in forward data | Zero forward trades — no live evidence to evaluate. |

**Assessment:** This is the most concerning strategy in the portfolio.
It holds a conviction slot (rubric 18) but the half-life monitor has
flagged it ARCHIVE_CANDIDATE, and vitality is 0.260 — deep into FADING
territory. The watch items from the original validation (T3 weakening
PF 1.09, Bootstrap CI 0.93 below 1.0) were known risks. The system is
now confirming those risks are materializing.

The strategy fills the EVENT factor gap alongside PreFOMC-Drift, and
NFP coverage is genuinely unique. But elite standard says: a FADING
strategy in a conviction slot is a contradiction. The edge must be
alive to justify the attention.

**Pressure level: HIGH.** If vitality doesn't improve to STABLE (0.4+)
within 2 months, this should move to watch with an expiry deadline.
The EVENT gap value justifies patience but not indefinite tolerance.

---

### 2. PB-MGC-Short — WEAKEST CORE, NEGATIVE FORWARD PnL

| Tool | Signal | Detail |
|------|--------|--------|
| Vitality | VITAL (0.800) | Backtest half-life healthy. No drift alerts. |
| Scoreboard | **VULNERABLE (rubric 16)** | Weakest core by 2 points. Only core below 18. |
| Counterfactual | **REVIEW** | Forward: increases portfolio DD by $122. Not earning its slot in live. |

**Assessment:** PB-MGC-Short is a paradox. The vitality monitor shows
VITAL (healthy backtest, no drift) but the scoreboard shows VULNERABLE
(rubric 16, weakest core) and the forward counterfactual shows REVIEW
(negative contribution to live portfolio). The explanation: the strategy
trades so rarely (9 trades in 6 years) that the forward sample (3 trades,
-$316) is noise, but the rubric score reflects the structural problem —
unreliable metrics on tiny samples plus 4th MGC strategy at the soft cap.

This strategy is surviving on past merit (PF 2.36 backtest) rather than
current contribution (3 trades, -$316 forward). The vitality score is
artificially high because HEALTHY half-life on 9 trades is meaningless —
there's not enough data for the half-life to detect decay.

**Pressure level: MODERATE.** Not an immediate downgrade candidate (the
backtest is genuinely strong) but confirmed as the first core slot to
challenge. Any promoted conviction strategy scoring 17+ that fills a
non-MGC gap would displace it.

---

### 3. CloseVWAP-M2K-Short — NEAR FADING, DECAYING HALF-LIFE

| Tool | Signal | Detail |
|------|--------|--------|
| Vitality | **STABLE (0.410)** — barely above FADING (0.4 threshold) | Half-life DECAYING. |
| Scoreboard | Watch slot, rubric 16, 74 days to deadline | Promote condition: decay stabilizes + fwd PF > 1.2. |
| Counterfactual | Not in forward data | Zero forward trades. |

**Assessment:** Second-lowest vitality (0.410), one tick above FADING.
The DECAYING half-life is the driver. Close session coverage is unique
and valuable, but the strategy must show its edge is still alive. With
zero forward trades and no drift data, we're relying entirely on the
backtest trajectory — and it's declining.

**Pressure level: MODERATE.** The watch deadline (2026-06-01) is the
natural decision point. If vitality drops to FADING before then,
escalate the review.

---

### 4. MomIgn-M2K-Short — FIRST EXPIRY, NO FORWARD EVIDENCE

| Tool | Signal | Detail |
|------|--------|--------|
| Vitality | VITAL (0.800) | Backtest half-life healthy (paradoxically). |
| Scoreboard | **FIRST EXPIRY (rubric 14)** | 74 days to deadline. Lowest rubric in any active bucket. |
| Counterfactual | Not in forward data | Zero forward trades. |

**Assessment:** The vitality score is misleading. VITAL at 0.800
because the half-life is HEALTHY and there's no drift data — but the
rubric score (14) reflects the real problem: validation collapsed from
9.0 to 6.0, PF 1.24 is marginal, and it's in the overcrowded MOMENTUM
factor. The vitality monitor can't detect "the edge was always marginal"
— it can only detect decay from a previously strong edge.

This is the clearest case of a strategy surviving on default rather than
merit. It has the lowest score in any active bucket, no forward evidence,
and its primary value (midday M2K session) is niche.

**Pressure level: HIGH.** The 2026-06-01 deadline should be enforced
strictly. If no forward evidence by then, archive without extension.

---

## Closest Challengers to Displacing Incumbents

### Treasury-Rolldown-Carry-Spread (effective 20)

| Metric | Value |
|--------|-------|
| Rubric | 18 raw + 2 gap bonus = **20 effective** |
| Gaps filled | CARRY factor (0 active) + Rates asset (0 active) |
| Target 1 | MomIgn-M2K-Short (watch 14) — decisive advantage |
| Target 2 | PB-MGC-Short (core 16) — advantage but needs forward evidence |
| Status | Testing (first-pass complete, PF 1.11 equal / 1.10 DV01) |
| Blocker | Needs forward evidence. PF 1.11 is marginal by elite standard. |

### Commodity-TermStructure-Carry (effective 19)

| Metric | Value |
|--------|-------|
| Rubric | 17 raw + 2 gap bonus = **19 effective** |
| Gaps filled | CARRY factor (0 active) |
| Target | MomIgn-M2K-Short (watch 14) — clear advantage |
| Status | Testing (SALVAGE classification, MGC-only edge) |
| Blocker | SALVAGE, not ADVANCE. Needs v2 data or forward evidence. |

---

## Strategies Surviving on Past Merit

Three strategies show the pattern of "strong backtest, weak or absent
forward evidence":

| Strategy | Backtest | Forward | Diagnosis |
|----------|----------|---------|-----------|
| **PB-MGC-Short** | PF 2.36 (9 trades) | 3 trades, -$316 | Too rare to evaluate. Backtest PF is unreliable on 9 trades. |
| **TV-NFP-High-Low-Levels** | PF 1.66, Sharpe 3.25 | 0 trades | FADING vitality despite strong backtest. Half-life flagged ARCHIVE_CANDIDATE. |
| **MomIgn-M2K-Short** | PF 1.24 (90 trades) | 0 trades | Validation collapsed 9.0→6.0. Rubric 14. Surviving by default. |

None of these three have demonstrated any forward value. Under the elite
standard, past merit is necessary but not sufficient — forward evidence
is what earns a slot.

---

## FADING Strategy: Immediate Action Needed?

**TV-NFP-High-Low-Levels (vitality 0.260 FADING)**

This is the only FADING strategy. The question: does FADING require
immediate downgrade, or does the EVENT factor gap value justify a
monitoring period?

**Recommendation: Monitor with escalation deadline, not immediate downgrade.**

Rationale:
- NFP occurs ~12 times per year. The strategy has had zero opportunities
  to generate forward evidence since entering probation. Flagging it as
  FADING based on backtest half-life alone — without any forward trades
  to confirm or deny — is the monitor doing its job, but the evidence is
  one-dimensional.
- The EVENT factor gap is the second-most-valuable gap in the portfolio
  (after CARRY). Dropping NFP coverage removes half the EVENT factor
  presence.
- PreFOMC-Drift (the other EVENT strategy) is VITAL at 0.800. If NFP
  were also VITAL, the EVENT factor would be strongly represented. Losing
  NFP weakens the factor.

**Action:** Keep in conviction but set a vitality gate:
- If vitality improves to STABLE (0.4+) after 2 NFP events with forward
  trades → stays in conviction
- If vitality remains FADING after 2 NFP events → move to watch with
  expiry deadline
- If vitality drops to DEAD → immediate downgrade regardless of EVENT value

---

## Single Highest-Leverage Roster Move

**Treasury-Rolldown-Carry-Spread replaces MomIgn-M2K-Short at the
June 1 deadline.**

This swap:
- Opens CARRY factor (0 → 1 active) — biggest factor gap
- Opens Rates asset class (0 → 1 active) — biggest asset gap
- Removes MOMENTUM (55% → ~50%) — toward the hard cap
- Removes M2K concentration (3 → 2 in watch)
- Replaces rubric 14 with effective 20 (+6 points)
- Replaces a strategy surviving by default with one filling two gaps

**What needs to happen for this to be earned:**
1. Treasury-Rolldown accumulates any forward evidence (even 2-3 months
   of spread returns, positive or negative, to confirm the signal works)
2. MomIgn fails to meet its promote condition (fwd PF > 1.3 / 20 trades)
   by June 1 — which is very likely given it has 0 forward trades now
3. You approve the displacement at the June 1 checkpoint

**If current trends continue:** MomIgn expires with zero evidence.
Treasury-Rolldown enters the watch slot with CARRY + Rates gap value.
The portfolio's two biggest structural weaknesses (no CARRY, no Rates)
begin to be addressed. This is the single highest-leverage move available.

---

## System Health Summary

| Metric | Status |
|--------|--------|
| FADING strategies | 1 (TV-NFP) — monitoring with escalation |
| DEAD strategies | 0 |
| Core vulnerability | PB-MGC-Short (16) — no immediate threat |
| Watch pressure | MomIgn (14) expires June 1 |
| Challenger readiness | Treasury-Rolldown at effective 20, needs forward evidence |
| Forward data depth | 5 days, 4 strategies — thin, growing |
| Factor gaps | CARRY (0), STRUCTURAL (0) — unchanged |
| Next checkpoint | June 1 watch expiry decisions |

The three tools together show a portfolio that is structurally sound but
under real evolutionary pressure. The CARRY challengers are almost ready.
The weakest incumbents are identified. The system is working as designed:
discovery feeds challengers, the scoreboard makes pressure visible,
counterfactual checks live contribution, and vitality catches decay.
The portfolio will get stronger at the June 1 checkpoint.
