# Pre-Flight: Monthly System Review (Phase A → Phase B activation)

**Filed:** 2026-05-05
**Authority:** T1 (verified-informational; report-only governance artifact)
**Lane:** B (research / governance)
**Operator decision required:** approve activation of `scripts/com.fql.monthly-system-review.plist.disabled` to begin scheduled monthly cadence

---

## What was built

| Artifact | Path | Status |
|---|---|---|
| CLI tool | `research/monthly_system_review.py` | Built, smoke-tested |
| Disabled plist | `scripts/com.fql.monthly-system-review.plist.disabled` | Built, syntax-validated, NOT loaded |
| First report | `docs/reports/monthly_system_review/2026-05_FQL_SYSTEM_REVIEW.md` | Generated as smoke test (305 lines) |
| Output dir | `docs/reports/monthly_system_review/` | Created |

Phase model mirrors the Forge automation ladder:
- **Phase A — manual CLI only (NOW):** operator runs `python3 research/monthly_system_review.py --month YYYY-MM --save`.
- **Phase B — scheduled launchd (this pre-flight requests):** plist fires every Saturday at 09:00 local; script self-guards via `--first-saturday-guard` and exits 0 on Saturdays 8-31. Net: one fire per month, on the first Saturday after month-end.

## Safety contract

- Report-only. No registry / Lane A / portfolio / runtime / scheduler / checkpoint / hold-state mutation.
- All file writes target `docs/reports/monthly_system_review/`.
- All other I/O is read-only against existing artifacts (registry JSON, watchdog state, Forge reports, launchctl, plist files, memory dir, inbox).
- No network calls. No subprocess invocations beyond `launchctl list`.
- Plist provided as `.disabled` so it cannot be loaded accidentally.

## Smoke test results

Two test runs (May 2026 partial, April 2026 prior-month auto-default):

| Test | Result |
|---|---|
| `--month 2026-05 --dry-run` | OK — 7,850 chars / 306 lines / 10 sections / 2 wins / 3 risks / 6 recs |
| `--month 2026-05 --save` | OK — wrote `docs/reports/monthly_system_review/2026-05_FQL_SYSTEM_REVIEW.md` |
| `--dry-run` (auto prior-month) | OK — defaulted to 2026-04 / 7,006 chars / 303 lines / 1 win / 4 risks |
| `--first-saturday-guard` (today is Tue) | OK — exited cleanly with "not first Saturday" message |
| `plutil -lint` on plist | OK |
| `launchctl list \| grep monthly-system-review` | (not loaded — correct) |

## What the first report surfaced (May 2026 partial)

**Wins (2):** 2 PASS-every-fire candidates this month; all 11 expected launchd agents loaded.

**Risks (3):**
1. 1 watchdog check not OK on last run
2. Item 2 cross-pollination criterion: still 0 `salvaged_from` entries
3. Closed-loop Forge → source-helpers feedback not yet wired (roadmap step #6)

**Top recommendations (5 of 6):**
1. v2: parse commit log over the month and cross-check against claimed roadmap completions
2. Consider batch register pre-flight for PASS-every-fire candidates not yet in registry
3. Cross-pollination plumbing thin — prioritize batch registers that populate `components_used`
4. Run `python3 scripts/portfolio_gap_dashboard.py --save` to seed gap data
5. Build dedicated memory hygiene job (already on roadmap step #2)

These are real, actionable, and align with the existing roadmap. The report does what it claims to do.

## Known v1 limitations (v2 roadmap)

These were intentionally left thin to ship a working v1 — they are the obvious next deepenings:

1. **Section 2 (Roadmap):** parses memory + `roadmap_queue.md` for headers; doesn't yet diff against commit log to detect actual completed work vs claimed.
2. **Section 6 (Portfolio gap):** counts assets/families/sessions from registry; doesn't yet read latest `portfolio_gap_dashboard.py` saved output for richer gap surfacing.
3. **Section 8 (Memory hygiene):** does a thin sample (launchctl-vs-memory + registry count drift). The dedicated memory-hygiene job (roadmap step #2) is the deeper version.
4. **Section 9 (Source/harvest):** counts inbox items + checks source-helper log freshness; doesn't yet aggregate accept/reject yields per source over the month.
5. **Per-month trend deltas** (vs prior month) not yet wired — first report has no comparator. Will populate organically once 2+ reports exist.

None of these are blockers; all are additive enhancements that don't change the safety contract.

## Activation steps (when operator approves)

```bash
# Copy disabled plist into LaunchAgents
cp scripts/com.fql.monthly-system-review.plist.disabled \
   ~/Library/LaunchAgents/com.fql.monthly-system-review.plist

# Bootstrap (load) the plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.fql.monthly-system-review.plist

# Verify loaded
launchctl list | grep monthly-system-review
```

To deactivate later:

```bash
launchctl bootout gui/$(id -u)/com.fql.monthly-system-review
rm ~/Library/LaunchAgents/com.fql.monthly-system-review.plist
```

## Schedule

- Plist fires **every Saturday at 09:00 local**.
- Script self-guards: exits cleanly unless `today.weekday() == 5 and today.day <= 7` (i.e., the first Saturday of the month).
- Net effective cadence: **one fire per month**, on the first Saturday after month-end.
- Report covers the prior month by default (auto-detected from today's date).

Example: Saturday 2026-06-06 fires → produces `2026-05_FQL_SYSTEM_REVIEW.md`.

## Recommended next actions

1. **Operator reviews this pre-flight + the smoke-test report** at `docs/reports/monthly_system_review/2026-05_FQL_SYSTEM_REVIEW.md`.
2. If approved: run the activation steps above. First scheduled fire = Saturday 2026-06-06 09:00 PT for May 2026 final report.
3. If deferred: keep Phase A (manual CLI). Operator runs the script ad hoc when desired.
4. Add this as a **standing governance cadence** in project memory (regardless of activation choice).

## Why this exists

Per operator framing 2026-05-05: every other layer (daily research, weekly scorecard, operator digest, Forge daily loop) is **per-domain or per-cadence**. None synthesize across roadmap, lanes, registry, portfolio, automation, memory, and source-yield in a single artifact. Without a strategic governance synthesis, FQL drifts as the factory speeds up.

This is the governance layer that catches drift early.

---

*Filed 2026-05-05. Lane B / governance. Phase A operative; Phase B activation pending operator approval. No Lane A surfaces touched. No registry mutation. Report-only.*
