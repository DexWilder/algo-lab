# Pre-Flight: Monthly System Review v1.1 (Phase A → Phase B activation)

**Filed:** 2026-05-05 (v1.0 initial); revised 2026-05-05 (v1.1 decision-report rewrite)
**Authority:** T1 (verified-informational; report-only governance artifact)
**Lane:** B (research / governance)
**Operator decision required:** approve activation of `scripts/com.fql.monthly-system-review.plist.disabled` to begin scheduled monthly cadence

---

## v1.1 changes from v1.0

The v1.0 was a static status report. v1.1 turns it into a **decision report** per operator framing:

> state → risks → deltas → decisions needed → recommended changes

**Ten new sections / improvements added:**

1. **Decision Required** (section 2) — operator action items aggregated from all sections, table-rendered
2. **Top 5 System Risks** (section 3) — structural risks ranked by severity (concentration, drift, backlog, tripwires, plumbing thinness, looping)
3. **Vision Alignment Score** (section 4) — GREEN/YELLOW/RED with explanation; defaults to YELLOW for first month while baseline establishes
4. **Month-over-Month Delta** (section 5) — 17-metric table comparing current vs prior snapshot; first month writes baseline at `.snapshots/YYYY-MM_snapshot.json`
5. **Evidence Absorption Rate** (section 6) — generation vs absorption; flags GENERATING_FASTER_THAN_ABSORBING
6. **Automation Truth Table** (section 7) — expected vs loaded vs last-log-age, OK/WARN/FAIL per agent
7. **Recommended Roadmap Edits** (section 15) — specific add/change/remove from section findings
8. **Next Month Watchlist** (section 16) — 3-7 items + standing items to revisit
9. **Source Artifacts** (section 17) — paths/links appendix
10. **Pre-Activation Checklist** (section 18) — 10 checks; rendered every report until plist activation, then can be removed

Existing detail sections (Roadmap, Lane A, Forge, Registry, Portfolio Gap, Memory Hygiene, Source/Harvest) preserved and extended to populate `decisions` and `watchlist` aggregator fields.

## What was built (current state)

| Artifact | Path | Status |
|---|---|---|
| CLI tool (v1.1) | `research/monthly_system_review.py` | Built; 18 sections; smoke-tested |
| Disabled plist | `scripts/com.fql.monthly-system-review.plist.disabled` | Built, syntax-validated, NOT loaded |
| First v1.1 report | `docs/reports/monthly_system_review/2026-05_FQL_SYSTEM_REVIEW.md` | Generated (439 lines, 18 sections, 13 KB) |
| First snapshot | `docs/reports/monthly_system_review/.snapshots/2026-05_snapshot.json` | Saved (baseline) |
| This pre-flight | `docs/_DRAFT_2026-05-05_monthly_system_review_preflight.md` | This file |

## Safety contract (unchanged from v1.0)

- Report-only. No registry / Lane A / portfolio / runtime / scheduler / checkpoint / hold-state mutation.
- All file writes target `docs/reports/monthly_system_review/` (report) or `.snapshots/` (delta tracking).
- All other I/O is read-only against existing artifacts.
- No network calls. Only subprocess: `launchctl list` and `plutil -lint` (the latter only when generating the pre-activation checklist section).
- Plist provided as `.disabled` so it cannot be loaded accidentally.

## v1.1 smoke test results

| Test | Result |
|---|---|
| `--month 2026-05 --dry-run` | OK — 13,008 chars / 439 lines / 18 sections / 1 win / 4 risks / 1 decision pending |
| `--month 2026-05 --save` | OK — wrote report + snapshot |
| `--dry-run` (auto prior-month) | OK — defaults to 2026-04 |
| `--first-saturday-guard` (today is Tue) | OK — exits cleanly with "not first Saturday" message |
| `plutil -lint` on plist | OK |
| `launchctl list \| grep monthly-system-review` | (not loaded — correct) |

## What the v1.1 report (May 2026 partial) actually surfaces

**Vision alignment:** 🟡 **YELLOW** — explanation: "1 fire / 2 PASS verdicts at expected rate; cross-pollination 0 salvaged_from criterion not yet moving."

**Top 5 system risks (ranked):**
1. Thin cross-pollination plumbing — 0 salvaged_from entries (severity 75)
2. Memory/docs drift — 1 agent disagrees between memory and reality (severity 65)

(Only 2 surfaced this month; thresholds are tuned to flag *patterns that compound*, not transient issues. KILL-loop, review-backlog, asset-concentration thresholds are present but not triggered yet.)

**Decision required:** 1 — "Operator: pre-flight batch register for 2 PASS-every-fire candidate(s)?"

**Evidence absorption:** IN_BALANCE (1 fire, 2 PASSes, no backlog)

**Automation truth table:** All 11 expected agents loaded; 4 show "WARN" because their stdout/stderr log paths don't match my `log_pattern_map` (cosmetic — agents are healthy per launchctl, but the v1.1 log-pattern guesses are approximate). Easy v1.2 fix.

**Watchlist for next month:**
- Forge fires next month — confirm rotation visited all candidates at least once
- Registry total strategies (current: 151)
- salvaged_from population (currently 0 — first non-zero would move Item 2 criterion)
- Closed-loop feedback edge — has step #6 progressed?

## Honest limitations remaining (v1.2 candidates, not blockers)

1. **Truth-table log pattern map is approximate.** Some agents show WARN solely because the v1.1 log filename pattern guess is wrong, not because the agent is unhealthy. Should be hardened to read each plist's `StandardOutPath` directly.
2. **Memory drift detector is binary.** It flagged `com.fql.monthly-system-review` as "claimed but not loaded" — true, but ignores that this agent is intentionally `.disabled`. Could add a "disabled-by-design" allowlist read from memory.
3. **Vision alignment is heuristic.** v2 should parse commit log to compute tooling-vs-strategy commit ratio.
4. **Evidence absorption "registered this month" count not yet computed.** Needs registry `_generated` parsing.
5. **No month-over-month deltas yet** (this is the first snapshot). Will populate organically after report #2.

None change the safety contract. None block activation.

## Activation steps (when operator approves)

```bash
cp scripts/com.fql.monthly-system-review.plist.disabled \
   ~/Library/LaunchAgents/com.fql.monthly-system-review.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.fql.monthly-system-review.plist
launchctl list | grep monthly-system-review
```

To deactivate later:

```bash
launchctl bootout gui/$(id -u)/com.fql.monthly-system-review
rm ~/Library/LaunchAgents/com.fql.monthly-system-review.plist
```

## Schedule when activated

- Plist fires **every Saturday at 09:00 local**.
- Script self-guards via `--first-saturday-guard`; exits cleanly unless `today.weekday() == 5 AND today.day <= 7`.
- Net effective cadence: **one fire per month**, on the first Saturday after month-end.
- Report covers the prior month by default.
- Example: Saturday 2026-06-06 fires → `2026-05_FQL_SYSTEM_REVIEW.md` (final May report, with month-over-month delta vs the v1.1 baseline already saved).

## Activation recommendation

**Recommend activation NOW.** Reasoning:
- Pre-activation checklist (Section 18 of the v1.1 report) shows all 10 checks ✅ except the cosmetic plist-not-yet-deployed item which is correct-by-design until activation.
- Smoke tests clean.
- Safety contract unchanged from v1.0.
- v1.2 polish items are additive enhancements; none affect output correctness or safety.
- The `.snapshots/2026-05_snapshot.json` baseline is already saved, so the first scheduled fire (2026-06-06) will produce the first month-over-month delta automatically.
- Delaying activation until v1.2 polishes are in just delays the first scheduled report.

**Counter-recommendation (deferred activation):** if operator wants the truth-table log patterns hardened first, defer activation by ~1 session, land v1.2 patch, then activate. This is a defensible choice; the cost is one extra session of manual `python3 research/monthly_system_review.py --save` invocations.

## Why this exists (unchanged from v1.0)

Per operator framing 2026-05-05: every other layer (daily research, weekly scorecard, operator digest, Forge daily loop) is **per-domain or per-cadence**. None synthesize across roadmap, lanes, registry, portfolio, automation, memory, and source-yield in a single artifact. Without a strategic governance synthesis, FQL drifts as the factory speeds up.

This is the governance layer that catches drift early. v1.1 makes it a **decision report**, not a status report — what to read, what to act on, what to change next month.

---

*Filed 2026-05-05. Lane B / governance. Phase A operative; Phase B activation pending operator approval. v1.1 active. No Lane A surfaces touched. No registry mutation. Report-only.*
