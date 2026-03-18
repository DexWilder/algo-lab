# Claude↔Claw Control Loop — 24-Hour Shakedown Audit
## 2026-03-17 (Day 0 — System Wiring Day)

*This audit covers the period from loop activation through first evening.*

---

## 1. Claw Phases Completed

| Metric | Value |
|--------|-------|
| Primary tasks completed | **1** (academic_scan) |
| Secondary tasks completed | **0** |
| Total phases | **1** |
| Expected phases (fully operational) | 2-4 per day |

**Assessment: PARTIAL — expected.** The system was wired during this session.
Claw's primary task (Tuesday academic scan) was completed manually before
the cron job was created. The 30-minute heartbeat cron was created at 20:57 ET
with first fire at ~21:27 ET. No cron-triggered phases have fired yet.

This audit is baseline, not steady-state. The first full autonomous day will
be Wednesday 2026-03-18.

---

## 2. Notes and Reports Produced

| Output Type | Count | Location |
|-------------|-------|----------|
| Harvest notes | **3** | `inbox/harvest/2026-03-17_*.md` |
| Refinement notes | **0** | `inbox/refinement/` (empty) |
| Cluster reports | **0** | `inbox/clustering/` (empty) |
| Assessment reports | **0** | `inbox/assessment/` (empty) |
| **Total notes** | **3** | |
| **Daily budget used** | **3 / 15** (20%) | |

**Notes produced:**
1. `Treasury Auction Cycle Long-Short Arbitrage` — EVENT, rates-native, new family
2. `Volatility-Managed Commodity Futures Portfolio` — VOLATILITY, commodity-focused
3. `Optimized Cross-Asset Carry Portfolio` — CARRY, cross-asset, blocked

**Assessment: LOW VOLUME but expected for Day 0.** Only primary task ran.
Secondary tasks were not available because the multi-phase directive system
was wired after the primary task completed. Budget underutilized at 20%.

---

## 3. Idle Gaps

| Period | Duration | Reason |
|--------|----------|--------|
| Claw primary completion → session end | ~30 min | No cron job yet, no secondary assigned |
| Overnight (projected) | ~9 hours | Claw heartbeat will fire every 30 min starting ~21:27 |

**Assessment: EXPECTED gap on Day 0.** The cron was wired late in the day.
Starting tomorrow, the expected max idle gap is **30 minutes** (heartbeat
interval). Claude refreshes directives every 4 hours, so the longest Claw
could be working on stale directives is 4 hours — but the directives don't
change drastically within a day, so this is acceptable.

---

## 4. Claude Refresh Schedule

| Scheduled Run | Fired? | Notes |
|---------------|--------|-------|
| 02:00 ET (launchd) | **NOT YET** | First fire will be overnight |
| 06:00 ET (launchd) | **NOT YET** | Tomorrow morning |
| 10:00 ET (launchd) | **NOT YET** | Tomorrow |
| 14:00 ET (launchd) | **NOT YET** | Tomorrow |
| 17:30 ET (daily research) | **YES** | Standard daily pipeline ran successfully |
| 18:00 ET (launchd claw loop) | **NOT YET** | Plist updated after 18:00 today |
| 22:00 ET (launchd) | **PENDING** | Will be first claw-loop launchd fire |

**Manual control loop runs:** 2 (during session, to seed handoff files)

**Assessment: CANNOT VERIFY YET.** The 4-hour launchd schedule was installed
at ~20:50 ET. The first automated fire will be at 22:00 ET tonight. Full
verification requires checking tomorrow's logs.

**Verification command for tomorrow:**
```bash
ls -la research/logs/claw_loop_20260318*.log
```

---

## 5. Budget and Stop Conditions

| Check | Status |
|-------|--------|
| Daily note cap (15) | **NOT TESTED** — only 3 notes produced |
| Daily report cap (2) | **NOT TESTED** — 0 reports produced |
| Phase cap (4 phases) | **NOT TESTED** — only 1 phase ran |
| Budget tracking in directives | **WORKING** — shows "12 remaining" correctly |
| Stop condition in HEARTBEAT.md | **WRITTEN** — not yet exercised |

**Assessment: STRUCTURAL OK, NOT STRESS-TESTED.** The budget arithmetic is
correct in the directive file (15 - 3 = 12 remaining). But no phase has hit
the cap yet. First real test will be when Claw runs 3-4 phases in a day.

---

## 6. Lane Stalls

| Component | Status | Evidence |
|-----------|--------|----------|
| OpenClaw Gateway | **RUNNING** | pid 36187, RPC probe OK |
| OpenClaw Cron Scheduler | **ENABLED** | 1 job, nextWakeAtMs set |
| Claw heartbeat job | **SCHEDULED** | Next fire in ~26 min |
| Claude launchd (claw loop) | **LOADED** | com.fql.claw-control-loop in launchctl list |
| Claude launchd (daily) | **FIRED TODAY** | daily_run_20260317_1730.log exists |
| Handoff files | **SEEDED** | All 6 files exist with correct content |

**Assessment: ALL LANES OPERATIONAL.** No stalls detected. The only gap is
that neither the Claw cron nor the Claude 4-hour launchd have fired their
first automated cycle yet. Both are correctly scheduled.

---

## 7. Output Quality Assessment

### Note 1: Treasury Auction Cycle Long-Short Arbitrage
- **Factor:** EVENT — fills a stated gap
- **Quality:** HIGH — specific source (Lou, Yan, Zhang), mechanical rules,
  clear entry/exit, honest about blockers (needs auction calendar)
- **Distinct?** YES — new family (treasury_auction_event), rates-native
- **Actionable?** BLOCKED (needs_auction_calendar_and_duration_mapping)
- **Verdict:** Useful catalog addition

### Note 2: Volatility-Managed Commodity Futures Portfolio
- **Factor:** VOLATILITY — fills a stated gap
- **Quality:** HIGH — academic source (Kang & Kwon 2021), specific mechanism
  (inverse-vol scaling with leverage cap), honest about need for basket definition
- **Distinct?** YES — extends vol management beyond equity index
- **Actionable?** NEAR-TESTABLE (needs_basket_definition, but MCL+MGC basket exists)
- **Verdict:** Strong candidate, potentially testable soon

### Note 3: Optimized Cross-Asset Carry Portfolio
- **Factor:** CARRY — fills a stated gap
- **Quality:** MEDIUM-HIGH — academic source (Baltas via Return Stacked),
  but overlaps conceptually with existing ManagedFutures-Carry-Diversified
  (idea #41). The optimization/covariance twist is different but the family
  is the same.
- **Distinct?** PARTIAL — same carry family, different weighting approach
- **Actionable?** BLOCKED (needs_carry_lookup_table)
- **Verdict:** Useful as a family variant, but should be clustered with #41

### Overall Quality Assessment

**3 for 3 useful.** All three notes followed the template, had real sources,
mechanical rules, honest blockers, and targeted stated gaps. Zero low-value
churn. Zero closed-family violations. Zero momentum variants.

This is a strong signal that Claw's targeting is well-calibrated by the
priority files.

---

## 8. Recommended Adjustments

### No changes needed yet — but watch these on Day 1 (Wednesday):

1. **Verify first cron-triggered phase.** Check `openclaw cron runs --limit 5`
   tomorrow morning. If the 30-min heartbeat has been firing but Claw is not
   producing output, the HEARTBEAT.md may need tuning (message payload,
   thinking level, timeout).

2. **Verify Claude 4-hour launchd fires.** Check for
   `research/logs/claw_loop_20260318_*.log` files. Should see entries at
   02:00, 06:00, 10:00, 14:00, 18:00, 22:00.

3. **Watch secondary task uptake.** After Claw's primary Wednesday task
   (family_refinement) completes, does the next heartbeat pick up
   `gap_harvest_supplemental` from the directive? If not, the directive
   re-read loop in HEARTBEAT.md may need strengthening.

4. **Watch budget exhaustion behavior.** If Claw generates 15 notes by
   mid-afternoon, does it correctly stop? Check the directive file shows
   "budget_exhausted" and Claw logs HEARTBEAT_OK for remaining heartbeats.

5. **Potential tuning after Day 1:**
   - If Claw completes tasks too fast (all budget used by noon): increase
     daily cap to 20, or add a "quality over quantity" directive
   - If Claw is too slow (only 1 phase per day): increase timeout from
     300s to 600s, or increase thinking level
   - If note quality drops: tighten the template requirements or add
     explicit quality gates to the directive
   - If duplicate notes appear: the Friday cluster review should catch
     this, but may need an intra-week dedupe pass

### Day 1 verification checklist:

```bash
# Run these Wednesday evening:

# 1. How many heartbeats fired?
openclaw cron runs --id 85c3eb78-b228-4106-a71e-ff6011e5ac1d --limit 50

# 2. How many Claw phases completed?
ls ~/openclaw-intake/logs/2026-03-18*.log

# 3. How many notes produced?
ls ~/openclaw-intake/inbox/harvest/2026-03-18*.md | wc -l
ls ~/openclaw-intake/inbox/refinement/2026-03-18*.md | wc -l

# 4. How many Claude refreshes?
ls research/logs/claw_loop_20260318*.log | wc -l

# 5. Budget state
head -12 ~/openclaw-intake/inbox/_directives_today.md

# 6. Any errors?
cat research/logs/launchd_claw_loop_stderr.log
```
