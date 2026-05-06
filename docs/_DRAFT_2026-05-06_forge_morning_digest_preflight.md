# Pre-Flight: FQL Forge Morning Digest (Phase A → Phase B activation)

**Filed:** 2026-05-06
**Authority:** T1 (verified-informational; report-only governance artifact)
**Lane:** B (Forge / governance)
**Operator decision required:** approve activation of `scripts/com.fql.forge-morning-digest.plist.disabled` to begin scheduled morning cadence

---

## What was built

| Artifact | Path | Status |
|---|---|---|
| CLI tool | `research/fql_forge_morning_digest.py` | Built, smoke-tested |
| Disabled plist | `scripts/com.fql.forge-morning-digest.plist.disabled` | Built, syntax-validated, NOT loaded |
| First smoke-test report | `docs/reports/fql_forge_morning_digest/2026-05-05_forge_morning_digest.md` | Generated (105 lines, 6 sections) |
| Output dir | `docs/reports/fql_forge_morning_digest/` | Created |

Phase model mirrors monthly system review and memory hygiene audit:
- **Phase A — manual CLI only (NOW):** operator runs `python3 research/fql_forge_morning_digest.py [--date YYYY-MM-DD] --save`. Auto-detects latest forge_daily_*.json if no date.
- **Phase B — scheduled launchd (this pre-flight requests):** plist fires weekdays at 08:00 PT, after the prior weekday's 19:00 Forge fire.

## Safety contract

- Report-only. No registry / Lane A / portfolio / runtime / scheduler / checkpoint / hold-state mutation.
- All file writes target `docs/reports/fql_forge_morning_digest/`.
- All other I/O is read-only against existing artifacts (forge_daily_*.json/md, forge_queue.md, _TRIPWIRE_*.md, forge logs, registry JSON).
- No subprocess invocations.
- Plist provided as `.disabled` so it cannot be loaded accidentally.

## Six sections produced

1. **Executive Summary** — last run status (COMPLETE/TRIPWIRE/FAILED), verdict counts, runtime, action needed
2. **Candidate Results** — table per candidate with verdict, PF, n, net PnL, repeat-from-prior-runs detection, **registered-in-registry marker** (closed-loop visibility)
3. **Queue Changes** — current `forge_queue.md` next-recommended candidates
4. **Evidence Absorption Status** — distinct PASSes (prior 7 days + today) vs registry membership; backlog GREEN/YELLOW/RED with thresholds (≤5/≤15/>15 unreviewed PASSes)
5. **Automation Health** — runtime, stderr, stdout freshness, tripwire status
6. **Recommended Next Action** — one operator action + one safe Forge action + mode (CONTINUE / PAUSE / FIX)

## Smoke test results (against last night's 2026-05-05 fire)

| Test | Result |
|---|---|
| `python3 ... --dry-run` | OK — 2,821 chars / 105 lines / 6 sections |
| `python3 ... --save` | OK — wrote `docs/reports/fql_forge_morning_digest/2026-05-05_forge_morning_digest.md` |
| Auto-date-detection | OK — finds latest `forge_daily_*.json` and uses its date |
| `plutil -lint` on plist | OK |
| `launchctl list \| grep forge-morning-digest` | (not loaded — correct) |

## What the smoke-test report surfaced

**Last Forge run (2026-05-05):** ✅ COMPLETE  |  PASS 2 / WATCH 3 / KILL 0 / RETEST 0  |  74.3s  |  no tripwires

**Closed-loop visible:** the 2 PASSes from yesterday's fire (XB-PB-EMA-Ladder-MCL, XB-PB-EMA-Ladder-MYM) are correctly marked as ✅ in registry — because we executed the surgical batch register this morning (commit `a5d75a1`). The digest sees the registration and confirms no review backlog.

**Backlog status:** 🟢 GREEN — IN BALANCE (0 PASSes awaiting review out of 2 distinct PASSes in window)

**Mode:** 🟢 CONTINUE — review PASSes when ready

## Honest v1 limitations (v1.1 candidates, not blockers)

1. **Queue aging** not yet implemented — needs a daily snapshot mechanism similar to monthly review. v1 surfaces current queue without delta tracking.
2. **Repeat detection window** is fixed at 7 days. Could be parameterized.
3. **Backlog thresholds** (5/15) are placeholders. Should be revisited after a few weeks of real data.
4. **No "queue changes since yesterday"** detection (would need queue snapshot).
5. **No commit-log integration** to detect "this PASS was registered in commit X" attribution.

None change the safety contract. None block activation.

## Activation steps (when operator approves)

```bash
cp scripts/com.fql.forge-morning-digest.plist.disabled \
   ~/Library/LaunchAgents/com.fql.forge-morning-digest.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.fql.forge-morning-digest.plist
launchctl list | grep forge-morning-digest
```

To deactivate later:

```bash
launchctl bootout gui/$(id -u)/com.fql.forge-morning-digest
rm ~/Library/LaunchAgents/com.fql.forge-morning-digest.plist
```

## Schedule when activated

- Plist fires **weekdays at 08:00 local** (5 entries, Mon-Fri).
- No first-Saturday self-guard needed; runs every weekday morning by design.
- Reads the most recent `forge_daily_*.json` (typically the prior weekday's 19:00 fire).
- Net effective cadence: **5 fires per week**, one per weekday morning.

## Activation recommendation

**Recommend activation NOW.** Reasoning:
- Smoke test produced real signal (closed-loop registration visible)
- Safety contract identical to other Lane B Phase B activations
- Plist syntax-validated, not loaded
- The digest pairs naturally with the evening Forge fire (19:00 produces, 08:00 next day digests)
- Without activation, this remains manual; defeats the "evidence absorption" purpose

**Counter (defer activation):** wait until v1.1 polishes (queue aging, snapshot mechanism). Cost: one extra session of manual `python3 research/fql_forge_morning_digest.py --save` invocations per weekday.

## Why this exists

Without a morning digest, Forge produces evidence faster than the operator can review it (the very pattern the doctrine `feedback_closed_loop_over_cadence.md` warns against). The digest:
- Surfaces what changed in last night's fire
- Detects new PASSes vs repeat candidates
- Tracks registry absorption (closed-loop)
- Flags backlog before it accumulates
- Recommends one operator action + one Forge action

This is the consumption side of the closed loop. Cadence increases (twice-daily, weekend fires) become safe only after this absorbs the evening fire.

## Operating stack after activation

| Cadence | Layer | Surface |
|---|---|---|
| Continuous | Infra | OpenClaw / watchdog / claw control loop |
| Daily AM | **Forge digest (NEW)** | **`com.fql.forge-morning-digest` weekdays 08:00 PT** |
| Daily/Weekday | Lane A live ops | forward-day, daily-research, operator-digest, treasury-rolldown |
| Twice/weekly | Research factory | twice-weekly-research |
| Weekly | Integrity/audit | weekly-research |
| Daily PM | Forge evidence | `com.fql.forge-daily-loop` weekdays 19:00 PT |
| Monthly | Strategic governance | `com.fql.monthly-system-review` first Sat 09:00 PT |
| Human-gated | Truth | registry append, promotion, portfolio/runtime/checkpoint |

13 launchd agents after activation (was 12).

---

*Filed 2026-05-06. Lane B / Forge. Phase A operative; Phase B activation pending operator approval. No Lane A surfaces touched. No registry mutation. Report-only.*
