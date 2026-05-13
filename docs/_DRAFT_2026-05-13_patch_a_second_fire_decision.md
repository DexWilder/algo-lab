# Pre-Flight Template: Patch A Second-Fire Decision (2026-05-13 evening)

**Status:** TEMPLATE — to be filled in by operator after Wed 2026-05-13 20:00 PT source-helpers fire #2 data lands.
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

## §3 Second-fire data (TO BE FILLED IN)

- Total GitHub leads: ___ / 15 cap
- Junk count: ___
- Theme keyword matches:
  - value: ___
  - term premium: ___
  - earnings yield: ___
  - PPP: ___
  - carry: ___
  - regime detection: ___
  - trend filter: ___
  - compression: ___
  - Bollinger: ___
  - afternoon session: ___
  - close auction: ___
  - microstructure: ___
- Cross-fire: ___ unique new leads / ___ duplicates of Sun
- Triage outcomes for Sun 5/10 leads: ___ ACCEPT / ___ COMPONENT / ___ REJECT
- New observations vs first-fire: ___

---

## §4 Decision options (operator selects one)

- ☐ **CONTINUE** — Patch A is producing diverse, on-theme leads in target factors. Keep all 10 new queries. Promote DEFERRED ledger entries to VERIFIED_CLEAN.
- ☐ **PARTIAL TRIM** — Specific queries are returning all junk or zero useful leads. Drop those specific queries; preserve the rest. Mark trimmed queries in commit message.
- ☐ **FULL REVERT** — Patch A's 10 new queries are not producing yield, OR junk rate spiked, OR triage rejected the new-query leads. Revert `77e1e5f` entirely.
- ☐ **SHIFT SURFACE** — Patch A's themes are right but GitHub is the wrong channel for VALUE / CARRY (too academic; not coded). Revert GitHub-side Patch A and queue equivalent work on Reddit (Patch B) or source-yield memory / academic harvest lanes instead.
- ☐ **WAIT** — Two fires still insufficient signal. Defer decision again to 2026-05-17 yield-shift assessment per checklist §3. Update ledger DEFERRED_UNTIL.

---

## §5 Recommendation (TO BE FILLED IN AFTER DATA REVIEW)

**Selected decision:** ___

**Reasoning:**
___

---

## §6 Strongest counter-argument (REQUIRED — challenge layer)

What is the best case AGAINST the selected decision? Be honest. If you can't construct a real counter, the decision may be overconfident.

___

---

## §7 What would prove this decision wrong

Specific observable evidence over the next 1-4 weeks that would indicate the decision was incorrect:

- ___
- ___
- ___

---

## §8 Reversal criteria

Under what conditions would we reverse this decision? Be specific (data thresholds, time horizons, evidence types):

- ___
- ___

---

## §9 Application sequence (only if decision requires code change)

For decisions other than WAIT, document the exact commands or edits needed:

```
# (fill in if applicable)
```

If WAIT: update ledger DEFERRED_UNTIL date to 2026-05-17, no other changes.

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
