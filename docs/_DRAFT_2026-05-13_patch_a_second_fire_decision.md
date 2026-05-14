# DECISION RENDERED 2026-05-14 — Patch A Second-Fire Review

**Status:** ✅ DECISION RENDERED 2026-05-14 morning. Operator-approved SHIFT SURFACE. Executed 2026-05-14 in commit chain.

(File retains `_DRAFT_` prefix pending HYG-2 lifecycle convention from `docs/_BACKLOG_post_patch_a_and_phase_1_exit.md` §3 — file will be renamed to `_DECISION_` per Phase 1 exit cleanup work.)

---

# Pre-Flight Template: Patch A Second-Fire Decision (2026-05-13 evening)

**Original status:** TEMPLATE — to be filled in by operator after Wed 2026-05-13 20:00 PT source-helpers fire #2 data lands.
**Authority:** T2 (operator-gated decision).
**Lane:** B (Forge / harvest).
**Scope of decision:** stays / trims / reverts the source-priority Patch A applied 2026-05-07 (commit `77e1e5f`).

**Important:** No recommendation pre-filled. No conclusion pre-drawn. This document codifies the elite challenge-layer doctrine ("every pre-flight includes counter-argument + reversal criteria") so tonight's decision is structurally rigorous, not retrofitted.

---

## §1 Context (frozen at template time)

- **Patch A application:** commit `77e1e5f` (2026-05-07). +10 / -1 to `scripts/fetch_github_leads.py` QUERIES.
- **Pre-flight that authorized Patch A:** `docs/_DRAFT_2026-05-07_source_priority_patch_preflight.md`.
- **Patch A review checklist:** `docs/_DRAFT_2026-05-07_patch_a_review_checklist.md`.
- **First-fire data (2026-05-10):** 14 GH leads; 10 of 12 TRANSFER theme keywords had 0 matches; junk rate ~4 mentions (acceptable); operator decision was WAIT FOR WEDNESDAY (one data point insufficient).
- **Second-fire timing:** Wed 2026-05-13 20:00 PT (pending at template time).
- **This decision:** the substantive Patch A outcome call.

---

## §2 Data inputs to collect BEFORE filling in this template

These should be inspected after the 20:00 PT source-helpers fire completes (~21:00 PT review window):

| Data point | Where to look |
|---|---|
| Did source-helpers fire cleanly? | `research/logs/source_helpers_20260513_*.log` exists with non-zero size; LastExitStatus 0 |
| Total GitHub leads count | `head -5 ~/openclaw-intake/inbox/source_leads/github_leads.md` (line "Total leads:") |
| Patch A theme keyword matches | `grep -c -i "<theme>" ~/openclaw-intake/inbox/source_leads/github_leads.md` for each of 12 TRANSFER themes (value, term premium, earnings yield, PPP, carry, regime detection, trend filter, compression, Bollinger, afternoon session, close auction, microstructure) |
| Junk count | `grep -c -i "crypto\|bitcoin\|ethereum\|defi\|nft\|web3" ~/openclaw-intake/inbox/source_leads/github_leads.md` |
| Cross-fire comparison | Compare `github_leads.md` vs `github_leads_prev.md` — count unique-new-leads vs duplicates from Sun's fire |
| Triage outcomes (if any) | Did any Sun 5/10 leads get classified ACCEPT / ACCEPT-COMPONENT / REJECT? Check `harvest_triage/` notes |
| Existing first-fire data | Reference §1 above + Sun 5/10 16-line summary in operator chat |

Fill in below ONLY after collecting these.

---

## §3 Second-fire data (FILLED IN 2026-05-14 morning)

- Total GitHub leads: **14 / 15 cap**
- Junk count: **4** (1 each: crypto, bitcoin, ethereum, defi — same as Sun)
- Theme keyword matches (across full file):
  - value: **2** (same as Sun)
  - term premium: **0**
  - earnings yield: **0**
  - PPP: **0**
  - carry: **0**
  - regime detection: **0**
  - trend filter: **0**
  - compression: **0**
  - Bollinger: **1** (same as Sun)
  - afternoon session: **0**
  - close auction: **0**
  - microstructure: **0**
- Cross-fire: **0 unique new leads / 14 duplicates** of Sun (top 8 repo names IDENTICAL)
- Triage outcomes for Sun 5/10 leads: not yet classified at decision time (Mon harvest cycle didn't pull from Sun's leads materially)
- New observations vs first-fire: **Wed leads are LITERALLY IDENTICAL to Sun's set** — same top-8 repos by stars, identical keyword counts, identical junk count. Confirmation that GitHub-search ranking returns the same top-15 broad-query results regardless of the 10 added TRANSFER queries.

---

## §4 Decision options (operator selects one)

**Reframe (locked 2026-05-13 morning via Lane 1 14-day forge_source_feedback dry-run):** The TRANSFER thesis is REINFORCED, not weakened, by 6 fires of evidence at MODERATE confidence. So tonight's question is NOT "Was TRANSFER wrong?" It IS:

> *"Did GitHub surface TRANSFER-aligned leads under Patch A — or is TRANSFER better routed through another surface (Reddit, academic, source-yield memory)?"*

That framing makes each option below trigger-precise:

- ☐ **CONTINUE** — Wed fire produces clear on-theme VALUE / CARRY / VOL / STRUCTURAL leads without junk-rate deterioration. Keep all 10 new queries. Promote DEFERRED ledger entries to VERIFIED_CLEAN.
- ☐ **PARTIAL TRIM** — A subset of Patch A queries produces junk/zero signal but others produce on-theme leads. Drop the specific underperforming queries; preserve the rest. Mark trimmed queries in commit message.
- ☑ **SHIFT SURFACE** — Wed repeats Sunday's pattern: TRANSFER thesis remains strong (per 14-day feedback evidence), but GitHub produces broad/momentum/business-as-usual leads. Revert GitHub-side Patch A and queue equivalent work on Reddit (Patch B) or source-yield / academic harvest lanes. The thesis travels with the operator's intent; the channel does not. **← OPERATOR-SELECTED 2026-05-14**
- ☐ **FULL REVERT** — Only if Patch A materially worsens GitHub intake quality (junk rate ≥50%, or triage rejection on new-query leads). Revert `77e1e5f` entirely.
- ☐ **WAIT** — Evidence is genuinely mixed but not harmful. Defer decision again to 2026-05-17 yield-shift assessment per checklist §3. Update ledger DEFERRED_UNTIL.

**Key distinction:** SHIFT SURFACE preserves the TRANSFER thesis (which is now MODERATE-confidence reinforced). FULL REVERT discards the thesis with the channel. Don't conflate the two.

---

## §5 Recommendation (FILLED IN 2026-05-14)

**Selected decision:** **SHIFT SURFACE**

**Reasoning:** The TRANSFER thesis remains valid and is reinforced by the 14-day Forge feedback evidence (MODERATE confidence; `ema_slope + profit_ladder` load-bearing pair confirmed across PB/BB/VWAP entries on multiple assets). However, GitHub search did not surface TRANSFER-aligned leads under Patch A. Two source-helper fires (Sun 5/10 + Wed 5/13) produced essentially identical results: 14 leads each, identical top-15 repos by stars, 10 of 12 TRANSFER theme keywords with 0 matches both fires, junk count unchanged at 4. The diagnosis is **channel/surface fit failure, not thesis failure**. The 10 new TRANSFER queries either return zero results (terms too academic for GitHub repo descriptions) or return repos that don't beat the broader queries' top-15 by stars under the MAX_LEADS=15 cap.

The thesis-vs-channel distinction (locked in `feedback_channel_vs_thesis.md` 2026-05-13 morning) directly enabled this decision. Without it, the data could have been misread as "TRANSFER is wrong" — leading to a FULL REVERT that discarded both channel and thesis. SHIFT SURFACE preserves the validated thesis for redeployment to channels better suited to academic/niche concept harvesting.

---

## §6 Strongest counter-argument (REQUIRED — challenge layer)

**Best case AGAINST SHIFT SURFACE:** Two source-helper fires (3-day gap) is a small sample; the pattern of "identical top-15" might be coincidence rather than structural channel-fit failure. A third fire on Sunday 5/17 might surface something different. Reverting now removes the 10 queries before we've seen them get a fair chance under different conditions (e.g., what if a hot new repo on a TRANSFER theme gets indexed next week?).

**Why we proceed anyway:** The "different conditions" scenario is ~5% likely versus ~95% likely the structural cap-crowd-out continues. Even if we waited, the SHIFT SURFACE decision would be the same eventually; running 3 more fires only confirms the pattern. The cost of waiting (1 more week of noise) exceeds the cost of acting now (revert is single-line, trivially reversible if Sun 5/17 shows new pattern).

---

## §7 What would prove this decision wrong

Specific observable evidence over the next 1-4 weeks:

- Reddit Patch B (when implemented) ALSO produces zero TRANSFER-themed leads → suggests the THESIS, not the channel, is wrong; need to re-evaluate the 14-day feedback that reinforced the thesis
- Academic source channel ALSO fails to surface TRANSFER concepts → same as above, but with a third channel datapoint
- Forge feedback over the next 30 days SHIFTS away from TRANSFER recommendation → thesis may be losing strength as more PASS evidence accumulates in different patterns
- Triage of the 14 GitHub leads (when it happens) shows several were actually on-theme but I missed them in keyword search → keyword analysis was too narrow

---

## §8 Reversal criteria

Under what conditions would we reverse SHIFT SURFACE and re-add the GitHub queries?

- A different channel (Reddit B / academic / source-yield memory) demonstrates that the TRANSFER thesis IS productive when given the right surface — at which point we'd reconsider whether GitHub deserves a more carefully-tuned query set, not a blanket re-add
- GitHub search algorithm changes materially (e.g., repo ranking changes; new TRANSFER-themed repos achieve top-15 stars) → could revisit
- We add `MAX_LEADS=30` or higher as a separate decision → at higher cap the new queries' results might surface beneath the broad-query top-15. NOT recommended without separate pre-flight.

---

## §9 Application sequence (executed 2026-05-14)

```bash
# 1. Edit scripts/fetch_github_leads.py — remove the 10 added queries; restore "momentum trading systematic python"
# 2. Verify: python3 -c "import importlib.util; ..." → 30 queries restored
# 3. Update _acknowledgments.json:
#    - a95ac91: DEFERRED_UNTIL → SUPERSEDED, note SHIFT SURFACE decision
#    - 77e1e5f: DEFERRED_UNTIL → SUPERSEDED, note GitHub-side revert
# 4. Single bundled commit: revert + ledger + decision template fill-in
# 5. No other surfaces touched
```

---

## §10 Safety contract

- Operator approval required before any code change applied.
- Patch B (Reddit) and Patch C (priorities generator) remain deferred independent of this decision unless explicitly authorized.
- No Lane A / registry / scheduler / portfolio / runtime / checkpoint / hold-state changes regardless of outcome.
- No promotion of any candidate to probation regardless of outcome.

---

## §11 Post-decision actions

After filling in §5-§8 and applying any code changes:
- Update `docs/reports/governance/_acknowledgments.json` for `a95ac91` and `77e1e5f`:
  - If CONTINUE: → VERIFIED_CLEAN
  - If PARTIAL TRIM: → VERIFIED_CLEAN (with note about which queries trimmed)
  - If FULL REVERT or SHIFT SURFACE: → SUPERSEDED (with note about reverting/replacement commit)
  - If WAIT: → DEFERRED_UNTIL 2026-05-17
- Update `_DRAFT_2026-05-07_patch_a_review_checklist.md` §2 (Wednesday) decision selection.
- Re-run governance audit to confirm effective load reflects resolution.

---

*Template filed 2026-05-13. Lane B / Forge. Phase 1 exit Thursday/Friday hinges on this decision completing cleanly. No content pre-filled.*
